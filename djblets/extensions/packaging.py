"""Packaging support for extensions."""

from __future__ import annotations

import inspect
import json
import os
import re
import sys
from distutils.errors import DistutilsExecError
from fnmatch import fnmatch
from typing import Dict, List, TYPE_CHECKING, Type

import django
import pkg_resources
from django.core.management import call_command
from setuptools.command.build_py import build_py
from setuptools import Command

from djblets.dependencies import frontend_buildkit_npm_dependencies
from djblets.pipeline.settings import build_pipeline_settings
from djblets.util.filesystem import is_exe_in_path

if TYPE_CHECKING:
    from djblets.extensions.extension import Extension


class BuildStaticFiles(Command):
    """Builds static files for the extension.

    This will build the static media files used by the extension. JavaScript
    bundles will be minified and versioned. CSS bundles will be processed
    through lesscss (if using .less files), minified and versioned.

    This must be subclassed by the project offering the extension support.
    The subclass must provide the extension_entrypoint_group and
    django_settings_module parameters.

    extension_entrypoint_group is the group name that entry points register
    into.

    django_settings_module is the Python module path for the project's
    settings module, for use in the DJANGO_SETTINGS_MODULE environment
    variable.
    """

    description = 'Build static media files'
    extension_entrypoint_group = None
    django_settings_module = None

    user_options = [
        (str('remove-source-files'), None,
         'remove source files from the package'),
    ]
    boolean_options = [str('remove-source-files')]

    def initialize_options(self):
        self.build_lib = None
        self.remove_source_files = False

    def finalize_options(self):
        self.set_undefined_options('build', ('build_lib', 'build_lib'))

    def get_lessc_global_vars(self):
        """Returns a dictionary of LessCSS global variables and their values.

        This can be implemented by subclasses to provide global variables for
        .less files for processing.

        By default, this defines two variables: ``STATIC_ROOT`` and ``DEBUG``.

        ``STATIC_ROOT`` is set to ``/static/``. Any imports using
        ``@{STATIC_ROOT}`` will effectively look up the requested file in
        ``<import_path>/@{STATIC_ROOT}``. This assumes that the project
        serving the static files keeps them in :file:`static/{appname}/`.

        Projects using less.js for the runtime can then define ``STATIC_ROOT``
        to ``settings.STATIC_URL``, ensuring lookups work for development and
        packaged extensions.

        ``DEBUG`` is set to false. Runtimes using less.js can set this to
        ``settings.DEBUG`` for templates. This can be useful for LessCSS
        guards.

        This requires LessCSS 1.5.1 or higher.
        """
        return {
            'DEBUG': False,
            'STATIC_ROOT': '/static/',
        }

    def get_lessc_include_path(self):
        """Returns the include path for LessCSS imports.

        By default, this will include the parent directory of every path in
        STATICFILES_DIRS, plus the static directory of the extension.
        """
        from django.conf import settings

        less_include = set()

        for staticfile_dir in settings.STATICFILES_DIRS:
            if isinstance(staticfile_dir, tuple):
                staticfile_dir = staticfile_dir[1]

            dirname = os.path.dirname(staticfile_dir)
            less_include.add(dirname)

            if os.path.basename(dirname) == 'static':
                # This code is here for compatibility reasons. With a proper
                # Babel setup, .less files should be able to reference others
                # relative to static/ directories. However, some paths may
                # still prefix /static/ to any paths, and we don't want those
                # to break. So, add the parent of this static/ directory
                # in order to allow those lookups to continue working.
                dirname = os.path.dirname(dirname)

            less_include.add(dirname)

        return less_include

    def install_pipeline_deps(
        self,
    ) -> str:
        """Install dependencies needed for the static media pipelining.

        This will install the build tools needed for any static media.

        Subclasses can override this to support additional tools.

        Returns:
            str:
            The path to the resulting :file:`node_modules` directory.
        """
        cwd = os.getcwd()
        build_dir = os.path.join(cwd, 'build')
        node_modules_dir = os.path.join(build_dir, 'node_modules')

        if not os.path.exists(build_dir):
            os.mkdir(build_dir, 0o755)

        if not os.path.exists(node_modules_dir):
            os.mkdir(node_modules_dir, 0o755)

        # Generate a package.json to install the dependencies for building
        # static media.
        with open(os.path.join(build_dir, 'package.json'), 'w') as fp:
            json.dump(
                {
                    'devDependencies': frontend_buildkit_npm_dependencies,
                    'name': '%s-extension' % os.path.basename(cwd),
                    'private': 'true',
                },
                fp,
                indent=2,
                sort_keys=True)

        # Install the dependencies.
        os.chdir(build_dir)

        try:
            self.npm_install()
        finally:
            os.chdir(cwd)

        return node_modules_dir

    def get_bundle_file_matches(self, bundles, pattern):
        """Return whether there's any files in a bundle matching a pattern.

        Args:
            bundles (dict):
                A dictionary of bundles.

            pattern (unicode):
                The filename pattern to match against.

        Returns:
            bool:
            ``True`` if a filename in one or more bundles matches the pattern.
            ``False`` if no filenames match.
        """
        for bundle_name, bundle_info in bundles.items():
            for filename in bundle_info.get('source_filenames', []):
                if fnmatch(filename, pattern):
                    return True

        return False

    def npm_install(self, package_spec=None):
        """Install a package via npm.

        This will first determine if npm is available, and then attempt to
        install the given package.

        Args:
            package_spec (unicode, optional):
                The package specification (name and optional version range)
                to install. If not specified, this will use the default
                behavior of reading :file:`package.json`.

        Raises:
            distutils.errors.DistutilsExecError:
                :command:`npm` could not be found, or there was an error
                installing the package.
        """
        if not hasattr(self, '_checked_npm'):
            if not is_exe_in_path('npm'):
                raise DistutilsExecError(
                    'Unable to locate npm in the path, which is needed to '
                    'install %s. Static media cannot be built.'
                    % package_spec)

            self._checked_npm = True

        if package_spec:
            # Ensure there's a node_modules directory here, so it doesn't
            # install higher up in the directory hierarchy.
            if not os.path.exists('node_modules'):
                os.mkdir('node_modules', 0o755)

            print('Installing %s...' % package_spec)
            result = os.system('npm install %s' % package_spec)
        else:
            print('Installing node packages...')
            result = os.system('npm install')

        if result != 0:
            raise DistutilsExecError('Installation from npm failed.')

    def run(self):
        from django.conf import settings

        # Prepare to import the project's settings file, and the extension
        # modules that are being shipped, so we can scan for the bundled
        # media.
        old_settings_module = os.environ.get('DJANGO_SETTINGS_MODULE')
        os.environ['DJANGO_SETTINGS_MODULE'] = self.django_settings_module

        # Skip any initial pipeline settings validation in the consuming
        # project's settings.py. The paths may not exist at this stage. We'll
        # be creating them.
        os.environ['DJBLETS_SKIP_PIPELINE_VALIDATION'] = '1'

        django.setup()

        cwd = os.getcwd()
        sys.path = [
            os.path.join(cwd, package_name)
            for package_name in self.distribution.packages
        ] + sys.path

        # Set up the common Django settings for the builds.
        settings.STATICFILES_FINDERS = (
            'djblets.extensions.staticfiles.PackagingFinder',
        )
        settings.STORAGES['staticfiles']['BACKEND'] = \
            'djblets.extensions.staticfiles.PackagingCachedFilesStorage'
        settings.INSTALLED_APPS = [
            'django.contrib.staticfiles',
        ]
        settings.CACHES = {
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            },
        }

        # Load the entry points this package is providing, so we'll know
        # which extensions to scan.
        #
        # Note that Command subclasses still use pkg_resources.Distribution,
        # rather than importlib.metadata.Distribution, so that's what we're
        # working with here.
        entrypoints = pkg_resources.EntryPoint.parse_map(
            self.distribution.entry_points,
            dist=self.distribution)

        extension_entrypoints = \
            entrypoints.get(self.extension_entrypoint_group)
        assert extension_entrypoints, 'No extension entry points were defined.'

        # Begin building pipeline bundles for each of the bundles defined
        # in the extension.
        for ep_name, entrypoint in extension_entrypoints.items():
            try:
                extension = entrypoint.load(require=False)
            except ImportError:
                sys.stderr.write(
                    'Error loading the extension for entry point %s\n'
                    % ep_name)
                raise

            self._build_static_media(extension)

        # Restore the environment, so we don't possibly interfere with
        # anything else.
        if old_settings_module is not None:
            os.environ['DJANGO_SETTINGS_MODULE'] = old_settings_module

        sys.path = sys.path[len(self.distribution.packages):]

    def _build_static_media(
        self,
        extension_cls: Type[Extension],
    ) -> None:
        """Build static media files for the extension.

        This will configure Pipeline for the extension, install any
        dependencies required, and then compile the static media.

        Args:
            extension_cls (type):
                The extension being packaged.
        """
        from django.conf import settings

        build_root = self.build_lib
        assert build_root

        pipeline_js = self._make_bundle(
            extension_bundles=extension_cls.js_bundles,
            default_dir='js',
            ext='.js')
        pipeline_css = self._make_bundle(
            extension_bundles=extension_cls.css_bundles,
            default_dir='css',
            ext='.css')

        # Get the location of the static/ directory within the module in the
        # source tree. We're going to use it to look up static files for
        # input, and as a relative path within the module for the output.
        static_dir = os.path.join(
            os.path.dirname(inspect.getfile(extension_cls)),
            'static')

        if not os.path.exists(static_dir):
            # This extension doesn't define any static files. There's nothing
            # to do.
            return

        from djblets.extensions.staticfiles import PackagingFinder
        PackagingFinder.extension_static_dir = static_dir

        settings.STATICFILES_DIRS = list(settings.STATICFILES_DIRS) + [
            static_dir,
        ]

        settings.STATIC_ROOT = os.path.join(build_root,
                                            os.path.relpath(static_dir))

        # Install any dependencies that might be needed by the bundles.
        #
        # We'll only do this if the extension is using Pipeline. They may just
        # have plain source files.
        if pipeline_css or pipeline_js:
            node_modules_dir = self.install_pipeline_deps()

            from pipeline.conf import settings as pipeline_settings

            # Update the Pipeline settings.
            pipeline_settings.update(build_pipeline_settings(
                pipeline_enabled=True,
                node_modules_path=node_modules_dir,
                static_root=settings.STATIC_ROOT,
                javascript_bundles=pipeline_js,
                stylesheet_bundles=pipeline_css,
                use_rollup=True,
                extra_config={
                    # Tell djblets.pipeline.compiles.less.LessCompiler not to
                    # check for outdated files using its special import script,
                    # and to in fact assume all files are outdated so they'll
                    # all be rebuilt. This will also prevent access denied
                    # issues (due to referenced files not being in the
                    # sandboxed tree defined for the static media).
                    '_DJBLETS_LESS_ALWAYS_REBUILD': True,

                    # Overwrite the arguments from build_pipeline_settings(),
                    # and add our own instead.
                    'LESS_ARGUMENTS': self._build_lessc_args(),
                }))

        # Collect and process all static media files.
        call_command('collectstatic', interactive=False, verbosity=2)

        if self.remove_source_files:
            # Remove source files from the package, if requested by the
            # packager. This will leave only the CSS and JavaScript bundles.
            self._remove_source_files(
                pipeline_css, os.path.join(settings.STATIC_ROOT, 'css'))
            self._remove_source_files(
                pipeline_js, os.path.join(settings.STATIC_ROOT, 'js'))

    def _build_lessc_args(
        self,
    ) -> List[str]:
        """Build the list of arguments for the less compiler.

        This will return a set of arguments that define any global variables
        or include paths for the less compiler. It respects most existing
        arguments already in ``settings.PIPELINE['LESS_ARGUMENTS']``, but
        will filter out any existing include paths and global variables needed
        for packaging.

        Returns:
            list:
            A list of arguments to pass to lessc.
        """
        from django.conf import settings

        # Get all the arguments that the application defines, but remove those
        # that we need to override or the ones that aren't compatible with
        # building this media.
        lessc_global_vars = self.get_lessc_global_vars()
        exclude_re = re.compile(
            '^--(include-path=|global-var="?(%s)=)'
            % '|'.join(
                re.escape(global_var)
                for global_var in lessc_global_vars.keys()
            ))

        lessc_args = [
            lessc_arg
            for lessc_arg in settings.PIPELINE.get('LESS_ARGUMENTS', [])
            if not exclude_re.match(lessc_arg)
        ]

        # Register the include path and any global variables used for
        # building .less files.
        return lessc_args + [
            '--include-path=%s'
            % os.path.pathsep.join(self.get_lessc_include_path())
        ] + [
            '--global-var=%s=%s'
            % (key, self._serialize_lessc_value(value))
            for key, value in lessc_global_vars.items()
        ]

    def _make_bundle(
        self,
        *,
        extension_bundles: Dict[str, Dict],
        default_dir: str,
        ext,
    ) -> Dict[str, Dict]:
        """Return a new Pipeline bundle based on an extension's bundle.

        Args:
            extension_bundles (dict):
                The bundles defined on the extension.

            default_dir (str):
                The default directory for the source files, for any bundles
                that don't specify an explicit output filename.

            ext (str):
                The default extension for the source files, for any bundles
                that don't specify an explicit output filename.

        Returns:
            dict:
            The new extension bundle.
        """
        pipeline_bundles: Dict[str, Dict] = {}

        for name, bundle in extension_bundles.items():
            if 'output_filename' not in bundle:
                bundle['output_filename'] = f'{default_dir}/{name}.min{ext}'

            pipeline_bundles[name] = bundle

        return pipeline_bundles

    def _remove_source_files(self, pipeline_bundles, media_build_dir):
        """Removes all source files, leaving only built bundles."""
        for root, dirs, files in os.walk(media_build_dir, topdown=False):
            for name in files:
                # A valid file will be represented as one of:
                #
                #     (bundle_name, 'min', stamp, ext)
                #     (bundle_name, 'min', ext)
                #
                # We keep both the pre-stamped and post-stamped versions so
                # that Django's CachedFilesStorage can generate and cache
                # the stamp from the contents of the non-stamped file.
                name_parts = name.split('.')

                if (len(name_parts) < 3 or
                    name_parts[0] not in pipeline_bundles or
                    name_parts[1] != 'min'):
                    # This doesn't appear to be a file representing a bundle,
                    # so we should get rid of it.
                    os.unlink(os.path.join(root, name))

            for name in dirs:
                try:
                    os.rmdir(os.path.join(root, name))
                except Exception:
                    # The directory is probably not empty yet.
                    pass

    def _serialize_lessc_value(self, value):
        if isinstance(value, str):
            return '"%s"' % value
        elif isinstance(value, bool):
            if value:
                return 'true'
            else:
                return 'false'
        elif isinstance(value, int):
            return '%d' % value
        else:
            raise TypeError('%r is not a valid lessc global variable value'
                            % value)


class BuildPy(build_py):
    def run(self):
        self.run_command('build_static_files')
        build_py.run(self)


def build_extension_cmdclass(build_static_files_cls):
    """Builds a cmdclass to pass to setup.

    This is passed a subclass of BuildStaticFiles, and returns something
    that can be passed to setup().
    """
    return {
        'build_static_files': build_static_files_cls,
        'build_py': BuildPy,
    }
