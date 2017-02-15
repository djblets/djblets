from __future__ import unicode_literals

import os
import shutil
import stat
import sys
import tempfile

import nose
from django.core.management import execute_from_command_line
from django.test.runner import DiscoverRunner

try:
    # Make sure to pre-load all the image handlers. If we do this later during
    # unit tests, we don't seem to always get our list, causing tests to fail.
    from PIL import Image
    Image.init()
except ImportError:
    try:
        import Image
        Image.init()
    except ImportError:
        pass

from django.conf import settings
from djblets.cache.serials import generate_media_serial


class TestRunner(DiscoverRunner):
    """Test runner for standard Djblets-based projects.

    This class provides all the common setup for settings, databases, and
    directories that are generally needed by Django projects using Djblets.
    Much of the behavior can be overridden by subclasses.

    `nose <http://nose.readthedocs.io/en/latest/>`_ is used to run the test
    suites. The options can be configured through :py:attr:`nose_options`.

    This can be subclassed in order to set the settings for the test run, or
    it can be instantiated with those settings passed in as keyword arguments.
    """

    #: The options used for nose.
    #:
    #: This is a list of command line arguments that would be passed to
    #: :command:`nosetests`.
    nose_options = [
        '-v',
        '--match=^test',
        '--with-id',
        '--with-doctest',
        '--doctest-extension=.txt',
    ]

    #: A list of Python package/module names to test.
    test_packages = []

    #: Whether or not ``collectstatic`` needs to be run before tests.
    needs_collect_static = True

    def __init__(self, *args, **kwargs):
        """Initialize the test runner.

        The caller can override any of the options otherwise defined on the
        class.

        Args:
            nose_options (list, optional):
                A list of options used for nose. See :py:attr:`nose_options`.

            test_packages (list, optional):
                A list of Python package/module names to test. See
                :py:attr:`test_packages`.

            needs_collect_static (bool, optional):
                Whether or not ``collectstatic`` needs to be run before
                tests. See :py:attr:`needs_collect_static`.
        """
        super(TestRunner, self).__init__(*args, **kwargs)

        # Override any values that the caller wants to override. This allows
        # the runner to be instantiated with the desired arguments instead
        # of subclassed.
        try:
            self.nose_options = kwargs['nose_options']
        except KeyError:
            pass

        try:
            self.test_packages = kwargs['test_packages']
        except KeyError:
            pass

        try:
            self.needs_collect_static = kwargs['needs_collect_static']
        except KeyError:
            pass

    def setup_test_environment(self, *args, **kwargs):
        """Set up an environment for the unit tests.

        This will handle setting all the default settings for a Djblets-based
        project and will create the directory structure needed for the tests
        in a temp directory.

        Subclasses can override this to provide additional setup logic.

        This must be called before :py:meth:`run_tests`.

        Args:
            *args (tuple):
                Additional positional arguments to pass to Django's version
                of this method.

            **kwargs (dict):
                Additional keyword arguments to pass to Django's version
                of this method.
        """
        super(TestRunner, self).setup_test_environment(*args, **kwargs)

        # Default to testing in a non-subdir install.
        settings.SITE_ROOT = '/'

        # Set some defaults for cache serials, in case the tests need them.
        settings.AJAX_SERIAL = 123
        settings.TEMPLATE_SERIAL = 123

        # Set a faster password hasher, for performance.
        settings.PASSWORD_HASHERS = (
            'django.contrib.auth.hashers.SHA1PasswordHasher',
        )

        # Make sure we're using standard static files storage, and not
        # something like Pipeline or S3 (since we don't want to trigger any
        # special behavior). Subclasses are free to override this setting.
        settings.STATICFILES_STORAGE = \
            'django.contrib.staticfiles.storage.StaticFilesStorage'

        # Create a temp directory that tests can rely upon.
        self.tempdir = tempfile.mkdtemp(prefix='rb-tests-')

        # Configure file paths for static media. This will handle the main
        # static and uploaded media directories, along with extension
        # directories (for projects that need to use them).
        settings.STATIC_URL = settings.SITE_ROOT + 'static/'
        settings.MEDIA_URL = settings.SITE_ROOT + 'media/'
        settings.STATIC_ROOT = os.path.join(self.tempdir, 'static')
        settings.MEDIA_ROOT = os.path.join(self.tempdir, 'media')

        required_dirs = self.setup_dirs() + [
            settings.STATIC_ROOT,
            settings.MEDIA_ROOT,
            os.path.join(settings.MEDIA_ROOT, 'ext'),
            os.path.join(settings.STATIC_ROOT, 'ext'),
        ]

        for dirname in required_dirs:
            if not os.path.exists(dirname):
                os.makedirs(dirname)

        if self.needs_collect_static:
            # Collect all static media needed for tests.
            execute_from_command_line([
                __file__, 'collectstatic', '--noinput', '-v', '0',
            ])

        generate_media_serial()

    def teardown_test_environment(self, *args, **kwargs):
        """Tear down the environment for the unit tests.

        This will clean up the temp directory structure.It must be called after
        :py:meth:`run_tests`.

        Args:
            *args (tuple):
                Additional positional arguments to pass to Django's version
                of this method.

            **kwargs (dict):
                Additional keyword arguments to pass to Django's version
                of this method.
        """
        shutil.rmtree(self.tempdir)

        super(TestRunner, self).teardown_test_environment(*args, **kwargs)

    def run_tests(self, test_labels=[], argv=None, *args, **kwargs):
        """Run the test suite.

        Args:
            test_labels (list of unicode, optional):
                Specific tests to run.

            argv (list of unicode, optional):
                Additional arguments for nose. If not specified, sys.argv is
                used.

            *args (tuple, unused):
                Unused additional positional arguments.

            **kwargs (dict, unused):
                Unused additional keyword arguments.

        Returns:
            int:
            The exit code. 0 means all tests passed, while 1 means there were
            failures.
        """
        if argv is None:
            argv = sys.argv

        self.setup_test_environment()
        old_config = self.setup_databases()

        self.nose_argv = [argv[0]] + self.nose_options

        if '--with-coverage' in argv:
            self.nose_argv += ['--with-coverage'] + [
                '--cover-package=%s' % package_name
                for package_name in self.test_packages
            ]
            argv.remove('--with-coverage')

        # If the test files are executable on the file system, nose will need
        # the --exe argument to run them
        known_file = os.path.join(os.path.dirname(__file__), '__init__.py')

        if (os.path.exists(known_file) and
            os.stat(known_file).st_mode & stat.S_IXUSR):
            self.nose_argv.append('--exe')

        # manage.py captures everything before "--"
        if len(argv) > 2 and '--' in argv:
            self.nose_argv += argv[(argv.index('--') + 1):]

        # test_labels may be provided to us with some command line arguments,
        # which we would have already added above. We need to sanitize this
        # when adding it to the argument list.
        self.nose_argv += [
            test_label
            for test_label in test_labels
            if (not test_label.startswith('-') and
                test_label not in self.nose_argv)
        ]

        # If specific tests are not requested, test all the configured
        # test packages.
        specific_tests = [
            test_name
            for test_name in self.nose_argv[1:]
            if not test_name.startswith('-')
        ]

        if not specific_tests:
            self.nose_argv += self.test_packages

        self.run_nose()

        self.teardown_databases(old_config)
        self.teardown_test_environment()

        if self.result.success:
            return 0
        else:
            return 1

    def setup_dirs(self):
        """Set up directories to create and use.

        This can return one or more directory paths that need to be created
        before the tests can be run. It may also store settings pointing to
        those paths.

        This is not responsible for creating the directories. Any returned
        paths will be created automatically.

        Returns:
            list of unicode:
            A list of directory paths to create.
        """
        return []

    def run_nose(self):
        """Run the unit tests using nose.

        This will use nose to run the tests, storing the result.

        Returns:
            nose.core.TestProgram:
            The result from the run.
        """
        self.result = nose.main(argv=self.nose_argv, exit=False)
