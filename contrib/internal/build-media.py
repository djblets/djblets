#!/usr/bin/env python

import os
import sys

scripts_dir = os.path.abspath(os.path.dirname(__file__))

# Source root directory
sys.path.insert(0, os.path.abspath(os.path.join(scripts_dir, '..', '..')))

from djblets.dependencies import django_version

import __main__
__main__.__requires__ = ['Django' + django_version]

# This is required to re-import.
import pkg_resources

from django.core.management import call_command


if __name__ == '__main__':
    os.putenv('FORCE_BUILD_MEDIA', '1')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djblets.settings')

    ret = call_command('collectstatic', interactive=False, verbosity=2)
    sys.exit(ret)
