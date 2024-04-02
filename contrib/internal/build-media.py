#!/usr/bin/env python3

import os
import sys

scripts_dir = os.path.abspath(os.path.dirname(__file__))

# Source root directory
sys.path.insert(0, os.path.abspath(os.path.join(scripts_dir, '..', '..')))

# Script config directory
sys.path.insert(0, os.path.join(scripts_dir, 'conf'))

import django
from django.core.management import call_command


if __name__ == '__main__':
    os.putenv('FORCE_BUILD_MEDIA', '1')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djblets.settings')

    django.setup()

    # This will raise a CommandError or call sys.exit(1) on failure.
    call_command('collectstatic', interactive=False, verbosity=2)
