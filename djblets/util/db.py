from __future__ import unicode_literals
import warnings

from djblets.db.managers import ConcurrencyManager
from djblets.deprecation import RemovedInDjblets20Warning


warnings.warn('djblets.util.db is deprecated', RemovedInDjblets20Warning)


__all__ = ['ConcurrencyManager']
