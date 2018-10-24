from __future__ import unicode_literals
import warnings

from djblets.deprecation import RemovedInDjblets20Warning
from djblets.forms.fields import TIMEZONE_CHOICES, TimeZoneField


warnings.warn('djblets.util.forms is deprecated. Use '
              'djblets.forms.fields instead.',
              RemovedInDjblets20Warning)


__all__ = [
    'TIMEZONE_CHOICES',
    'TimeZoneField',
]
