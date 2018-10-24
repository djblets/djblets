from __future__ import unicode_literals
import warnings

from djblets.cache.backend_compat import normalize_cache_backend
from djblets.deprecation import RemovedInDjblets20Warning


warnings.warn('djblets.util.cache is deprecated. Use '
              'djblets.cache.backend_compat.',
              RemovedInDjblets20Warning)


__all__ = ['normalize_cache_backend']
