from __future__ import unicode_literals
import warnings

from djblets.db.evolution import FakeChangeFieldType
from djblets.deprecation import RemovedInDjblets20Warning


warnings.warn('djblets.util.dbevolution is deprecated. Use '
              'djblets.db.evolution instead.',
              RemovedInDjblets20Warning)


__all__ = ['FakeChangeFieldType']
