#!/usr/bin/env python

from __future__ import unicode_literals

import os
import sys

import django
from django.core.management import call_command

import djblets


if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djblets.settings')

    if hasattr(django, 'setup'):
        # Django >= 1.7
        django.setup()

    os.chdir(os.path.dirname(djblets.__file__))

    ret = call_command('compilemessages', interactive=False, verbosity=2)
    sys.exit(ret)
