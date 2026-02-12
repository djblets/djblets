"""Configures pytest and Django environment setup for Djblets.

.. important::

   Do not define plugins in this file! Plugins must be in a different
   package (such as in tests/). pytest overrides importers for plugins and
   all modules descending from that module level, which will cause extension
   importers to fail, breaking unit tests.

Version Added:
    3.0
"""

from __future__ import annotations

import os
import sys

import djblets


sys.path.insert(0, os.path.join(os.path.dirname(__file__)))


def pytest_report_header(
    *args,
    **kwargs,
) -> list[str]:
    """Return information for the report header.

    This will log the version of Djblets.

    Args:
        *args (tuple):
            Unused positional arguments.

        **kwargs (dict):
            Unused keyword arguments.

    Returns:
        list of str:
        The report header entries to log.
    """
    return [
        f'Djblets: {djblets.get_version_string()}',
    ]
