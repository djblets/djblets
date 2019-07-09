"""Legacy template tags for datagrids.

Deprecated::
    2.0:
    This module is now empty and should no longer be used. It is scheduled
    for removal in Djblets 3.0.
"""

from __future__ import unicode_literals

import warnings

from django import template

from djblets.deprecation import RemovedInDjblets30Warning


register = template.Library()


warnings.warn('djblets.datagrid.templatetags is deprecated and will be '
              'removed in Djblets 3.0.',
              RemovedInDjblets30Warning)
