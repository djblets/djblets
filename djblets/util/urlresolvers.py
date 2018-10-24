from __future__ import unicode_literals
import warnings

from djblets.deprecation import RemovedInDjblets20Warning
from djblets.urls.resolvers import DynamicURLResolver


warnings.warn('djblets.util.urlresolvers is deprecated. See '
              'djblets.urls.resolvers.',
              RemovedInDjblets20Warning)


__all__ = ['DynamicURLResolver']
