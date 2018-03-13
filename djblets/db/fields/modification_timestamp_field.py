from __future__ import unicode_literals

from datetime import datetime

from django.conf import settings
from django.db import models

from djblets.util.dates import get_tz_aware_utcnow


class ModificationTimestampField(models.DateTimeField):
    """
    A subclass of DateTimeField that only auto-updates the timestamp when
    updating an existing object or when the value of the field is None. This
    specialized field is equivalent to DateTimeField's auto_now=True, except
    it allows for custom timestamp values (needed for
    serialization/deserialization).
    """
    def __init__(self, verbose_name=None, name=None, **kwargs):
        kwargs.update({
            'editable': False,
            'blank': True,
        })
        models.DateTimeField.__init__(self, verbose_name, name, **kwargs)

    def pre_save(self, model, add):
        if not add or getattr(model, self.attname) is None:

            if settings.USE_TZ:
                value = get_tz_aware_utcnow()
            else:
                value = datetime.now()

            setattr(model, self.attname, value)
            return value

        return super(ModificationTimestampField, self).pre_save(model, add)

    def get_internal_type(self):
        return "DateTimeField"

