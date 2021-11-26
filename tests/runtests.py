#!/usr/bin/env python3

import os
import shutil
import stat
import sys
import warnings

# This has to happen before we import nose.
import djblets.util.compat.python.collections

import nose


def run_tests(verbosity=1, interactive=False):
    import django
    from django.conf import settings
    from django.core import management
    from django.db import connection
    from django.test.utils import (setup_test_environment,
                                   teardown_test_environment)

    django.setup()

    # Restore warnings, if Django turns them off.
    warnings.simplefilter('default')

    setup_test_environment()
    settings.DEBUG = False

    for path in (settings.MEDIA_ROOT, settings.STATIC_ROOT):
        shutil.rmtree(path, ignore_errors=True)

        if not os.path.exists(path):
            os.mkdir(path, 0o755)

    management.call_command('collectstatic',
                            verbosity=verbosity,
                            interactive=interactive)

    old_db_name = 'default'
    connection.creation.create_test_db(verbosity, autoclobber=not interactive)

    management.call_command('migrate',
                            use_syncdb=True,
                            verbosity=verbosity,
                            interactive=interactive)

    nose_argv = [
        'runtests.py',
        '-v',
        '--match=^test',
        '--with-id',
    ]

    if '--with-coverage' in sys.argv:
        sys.argv.remove('--with-coverage')
        nose_argv += [
            '--with-coverage',
            '--cover-inclusive',
            '--cover-package=djblets',
        ]

    nose_argv += sys.argv[1:]

    # If the test files are executable on the file system, nose will need the
    #  --exe argument to run them
    known_file = os.path.join(os.path.dirname(__file__), '..', 'djblets',
                              'settings.py')

    if (os.path.exists(known_file) and
        os.stat(known_file).st_mode & stat.S_IXUSR):
        nose_argv.append('--exe')

    nose.main(argv=nose_argv)

    connection.creation.destroy_test_db(old_db_name, verbosity)
    teardown_test_environment()


if __name__ == "__main__":
    os.chdir(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.insert(0, os.getcwd())
    os.environ['DJANGO_SETTINGS_MODULE'] = "tests.settings"
    run_tests()
