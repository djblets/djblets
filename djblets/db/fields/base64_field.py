from __future__ import unicode_literals

import base64

from django.db import models
from django.utils.encoding import smart_text


class Base64DecodedValue(str):
    """
    A subclass of string that can be identified by Base64Field, in order
    to prevent double-encoding or double-decoding.
    """
    pass


class Base64FieldCreator(object):
    def __init__(self, field):
        self.field = field

    def __set__(self, obj, value):
        pk_val = obj._get_pk_val(obj.__class__._meta)
        pk_set = pk_val is not None and smart_text(pk_val) != ''

        if (isinstance(value, Base64DecodedValue) or not pk_set):
            obj.__dict__[self.field.name] = base64.encodestring(value)
        else:
            obj.__dict__[self.field.name] = value

        setattr(obj, "%s_initted" % self.field.name, True)

    def __get__(self, obj, type=None):
        if obj is None:
            raise AttributeError('Can only be accessed via an instance.')

        value = obj.__dict__[self.field.name]

        if value is None:
            return None
        else:
            return Base64DecodedValue(base64.decodestring(value))


class Base64Field(models.TextField):
    """
    A subclass of TextField that encodes its data as base64 in the database.
    This is useful if you're dealing with unknown encodings and must guarantee
    that no modifications to the text occurs and that you can read/write
    the data in any database with any encoding.
    """
    serialize_to_string = True

    def contribute_to_class(self, cls, name):
        super(Base64Field, self).contribute_to_class(cls, name)

        setattr(cls, self.name, Base64FieldCreator(self))
        setattr(cls, 'get_%s_base64' % self.name,
                lambda model_instance: model_instance.__dict__[self.name])

    def get_db_prep_value(self, value, connection=None, prepared=False):
        if isinstance(value, Base64DecodedValue):
            value = base64.encodestring(value)

        return value

    def save_form_data(self, instance, data):
        setattr(instance, self.name, Base64DecodedValue(data))

    def to_python(self, value):
        if isinstance(value, Base64DecodedValue):
            return value
        else:
            return Base64DecodedValue(base64.decodestring(value))

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)

        if isinstance(value, Base64DecodedValue):
            return base64.encodestring(value)
        else:
            return value
