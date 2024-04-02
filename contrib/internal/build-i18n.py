#!/usr/bin/env python3

import os
import sys

import django
from django.core.management import call_command

import djblets


if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djblets.settings')

    django.setup()

    os.chdir(os.path.dirname(djblets.__file__))

    ret = call_command('compilemessages', verbosity=2)
    sys.exit(ret)
