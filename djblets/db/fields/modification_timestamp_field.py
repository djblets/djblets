"""Field for managing modification timestamps for a model."""

from __future__ import unicode_literals

from django.db import models
from django.utils import timezone


class ModificationState(object):
    """Modification state for a tracked value.

    Attributes:
        first_set (bool):
            Whether or not the next :py:func:`setattr` will be the first.

            When this is ``True``, we do not consider the next
            :py:func:`setattr` to be a modification since the field will be
            set during model initialization.

        modified (bool):
            Whether or not the value has been manually modified.
    """

    def __init__(self):
        """Initialize the state."""
        self.modified = False
        self.first_set = False

    @staticmethod
    def get_attr_name(field_name):
        """Return the attribute name for the state for the named field.

        Args:
            field_name (unicode):
                The attribute name of the
                :py:class:`ModificationTimestampField`.

        Returns:
            unicode:
            The name of the modification state attribute.
        """
        return '_%s_state' % field_name


class ModificationTrackedValue(object):
    """A descriptor for tracking the modification of a value.

    Attributes:
        field_name (unicode):
            The attribute name of the field on the model.

        state_name (unicode):
            The attribute name of the state on the model.
    """

    def __init__(self, field_name, state_name):
        """Initialize the descriptor.

        Args:
            field_name (unicode):
                The name of the field attribute.

            state_name (unicode):
                The name of the state attribute.
        """
        self.field_name = field_name
        self.state_name = state_name

    def __get__(self, instance, objtype=None):
        """Return the value.

        Args:
            instance (django.db.models.Model):
                The model instance.

            objtype (type, optional):
                The model class.

        Returns:
            datetime.datetime:
            The value.
        """
        return instance.__dict__[self.field_name]

    def __set__(self, instance, value):
        """Set the value.

        This tracks modifications and updates the state if this is not the
        first call to this method (which occurs during model initialization).

        Args:
            instance (django.db.models.Model):
                The instance to set the the value on.

            value (datetime.datetime):
                The value to set.state.first_set:
        """
        state = getattr(instance, self.state_name)

        if state.first_set:
            state.first_set = False
        else:
            state.modified = True

        instance.__dict__[self.field_name] = value


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

    def contribute_to_class(self, cls, name):
        """Contribute the field attributes to the class.

        Args:
            cls (type):
                The model class to contribute the field to.

            name (unicode):
                The name of the field.
        """
        super(ModificationTimestampField, self).contribute_to_class(cls, name)

        state_name = ModificationState.get_attr_name(self.name)
        setattr(cls, self.name,
                ModificationTrackedValue(self.name, state_name))
        setattr(cls, state_name, ModificationState())

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
        state = getattr(model_instance,
                        ModificationState.get_attr_name(self.name))
        existing_value = getattr(model_instance, self.attname)

        if ((not add and not state.modified) or
            (add and existing_value is None)):
            value = timezone.now()
            setattr(model_instance, self.attname, value)
        elif ((not add and state.modified) or
              (add and existing_value is not None)):
            value = super(ModificationTimestampField, self).pre_save(
                model_instance, add)

        state.modified = False
        return value
