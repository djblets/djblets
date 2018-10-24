from __future__ import unicode_literals
import warnings

from djblets.deprecation import RemovedInDjblets20Warning
from djblets.urls.root import urlpatterns


warnings.warn('djblets.util.rooturl is deprecated. Use '
              'djblets.urls.root instead.',
              RemovedInDjblets20Warning)


__all__ = ['urlpatterns']
