#!/usr/bin/env python

import os
import sys

from django.core.management import call_command


if __name__ == '__main__':
    scripts_dir = os.path.abspath(os.path.dirname(__file__))
    sys.path.insert(0, os.path.abspath(os.path.join(scripts_dir, '..', '..')))

    os.putenv('FORCE_BUILD_MEDIA', '1')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djblets.settings')

    ret = call_command('collectstatic', interactive=False, verbosity=2)
    sys.exit(ret)
