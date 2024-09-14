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

import djblets


if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djblets.settings')

    django.setup()

    os.chdir(os.path.dirname(djblets.__file__))

    ret = call_command('compilemessages', verbosity=2)
    sys.exit(ret)
