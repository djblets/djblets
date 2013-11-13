from __future__ import unicode_literals
import warnings

from djblets.db.fields import (Base64DecodedValue, Base64Field,
                               Base64FieldCreator, CounterField, JSONField,
                               ModificationTimestampField)
from djblets.db.validators import validate_json


warnings.warn('djblets.util.fields is deprecated. Use '
              'djblets.db.fields instead.', DeprecationWarning)


__all__ = [
    'Base64DecodedValue',
    'Base64Field',
    'Base64FieldCreator',
    'CounterField',
    'JSONField',
    'ModificationTimestampField',
    'validate_json',
]
