#!/usr/bin/env python3

from __future__ import unicode_literals

import os
import sys

# This must be called before we import from Django, to ensure collections
# patching works.
import djblets

import django
from django.core.management import call_command


if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djblets.settings')

    if hasattr(django, 'setup'):
        # Django >= 1.7
        django.setup()

    os.chdir(os.path.dirname(djblets.__file__))

    ret = call_command('compilemessages', verbosity=2)
    sys.exit(ret)
