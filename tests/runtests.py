#!/usr/bin/env python
import nose
import os
import sys


def run_tests(verbosity=1, interactive=False):
    from django.conf import settings
    from django.core import management
    from django.db import connection
    from django.test.utils import setup_test_environment, \
                                  teardown_test_environment

    setup_test_environment()
    settings.DEBUG = False

    old_db_name = settings.DATABASE_NAME
    connection.creation.create_test_db(verbosity, autoclobber=not interactive)
    management.call_command('syncdb', verbosity=verbosity,
                            interactive=interactive)

    nose_argv = ['runtests.py', '-v',
                 '--with-coverage',
                 '--with-doctest',
                 '--doctest-extension=.txt',
                 '--cover-package=djblets']

    if len(sys.argv) > 2:
        node_argv += sys.argv[2:]

    nose.main(argv=nose_argv)

    connection.creation.destroy_test_db(old_name, verbosity)
    teardown_test_environment()


if __name__ == "__main__":
    os.chdir(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.insert(0, os.getcwd())
    os.environ['DJANGO_SETTINGS_MODULE'] = "tests.settings"
    run_tests()
