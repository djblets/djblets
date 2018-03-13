"""Field for managing modification timestamps for a model."""

from __future__ import unicode_literals

from django.db import models
from django.utils import timezone


class ModificationTimestampField(models.DateTimeField):
    """A timestamp field that only updates existing objects or when None.

    This is a subclass of :py:class:`~django.db.models.DateTimeField` that only
    auto-updates the timestamp when updating an existing object or when the
    value of the field is None. It's similar to using ``auto_now=True``, but
    custom timestamp values on new instances will not be replaced.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the field.

        Args:
            *args (tuple):
                Positional arguments for the field.

            **kwargs (dict):
                Additional keyword arguments for the field.
        """
        kwargs.update({
            'editable': False,
            'blank': True,
        })
        super(ModificationTimestampField, self).__init__(*args, **kwargs)

    def pre_save(self, model_instance, add):
        """Return the value of the field just before saving.

        Args:
            model_instance (django.db.models.Model):
                The model instance being saved.

            add (bool):
                Whether this is being saved to the database for the first time.

        Returns:
            datetime.datetime:
            The date/time value being saved.
        """
        if not add or self.value_from_object(model_instance) is None:
            value = timezone.now()
            setattr(model_instance, self.attname, value)
        else:
            value = super(ModificationTimestampField, self).pre_save(
                model_instance, add)

        return value
