"""Configures pytest and Django environment setup for Djblets.

.. important::

   Do not define plugins in this file! Plugins must be in a different
   package (such as in tests/). pytest overrides importers for plugins and
   all modules descending from that module level, which will cause extension
   importers to fail, breaking unit tests.

Version Added:
    3.0
"""

from __future__ import unicode_literals

import os
import shutil
import sys

import django
import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__)))


@pytest.fixture(autouse=True, scope='session')
def django_setup_static(request):
    """Collect static media at session start.

    Args:
        request (object):
            The pytest request.
    """
    from django.conf import settings
    from django.core import management

    for path in (settings.MEDIA_ROOT, settings.STATIC_ROOT):
        shutil.rmtree(path, ignore_errors=True)

        if not os.path.exists(path):
            os.mkdir(path, 0o755)

    management.call_command('collectstatic',
                            verbosity=request.config.option.verbose,
                            interactive=False)


def pytest_report_header(config):
    """Return information for the report header.

    This will log the version of Django.

    Args:
        config (object):
            The pytest configuration object.

    Returns:
        list of unicode:
        The report header entries to log.
    """
    return [
        'django version: %s' % django.get_version(),
    ]
