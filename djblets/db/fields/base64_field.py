"""Field for storing data as Base64-encoded values.

See :py:class:`Base64Field` for the main field type and usage instructions.
"""

from __future__ import unicode_literals

try:
    # Python >= 3.1
    from base64 import (decodebytes as base64_decode,
                        encodebytes as base64_encode)
except ImportError:
    # Python < 3.1
    from base64 import (decodestring as base64_decode,
                        encodestring as base64_encode)

from django.db import models
from django.utils import six
from django.utils.encoding import force_text, smart_text
from django.utils.translation import ugettext as _


class Base64TypeError(TypeError):
    """Error indicating an invalid value type was provided for the field."""

    def __init__(self, value):
        """Initialize the error.

        Args:
            value (object):
                The invalid value that was passed.
        """
        super(Base64TypeError, self).__init__(
            _('The provided value must be a string type or a '
              'Base64DecodedValue, not %r.')
            % type(value))


class Base64DecodedValue(bytes):
    """An identifiable wrapper around byte string values for Base64Field.

    This wraps any values coming from :py:class:`Base64Field`, helping make
    a distinction between arbitrary strings and decoded strings from the
    database. It helps prevent double-encoding or double-decoding of data.
    """


class Base64FieldCreator(object):
    """Property-like class used to store/retrieve Base64 values.

    This works much like a property, and takes care of encoding strings for
    storage and decoding them on retrieval. It's set internally by
    :py:class:`Base64Field` in place of the normal field attribute.
    """

    def __init__(self, field):
        """Initialize the creator.

        Args:
            field (Base64Field):
                The field owning this object.
        """
        self.field = field

    def __set__(self, obj, value):
        """Set a new value in the field.

        If this is a :py:class:`Base64DecodedValue`, or the model is new and
        hasn't yet been persisted to the database, the value will be encoded
        and stored. Otherwise, if it's a standard string value or the model
        is not new, it's assumed that this is encoded data for storage, and
        will be stored directly.

        Args:
            obj (django.db.models.Model):
                The model owning the field.

            value (object):
                The value being set. This must be a valid string value or
                :py:class:`Base64DecodedValue`.

        Raises:
            Base64TypeError:
                The type of value provided could not be set.
        """
        if value is not None:
            if not isinstance(value, (bytes, six.memoryview, six.text_type)):
                raise Base64TypeError(value)

            pk_val = obj._get_pk_val(obj.__class__._meta)
            pk_set = pk_val is not None and smart_text(pk_val) != ''

            if isinstance(value, six.text_type):
                if value == r'\x':
                    # On Djblets 2.0 with Python 3 on Postgres, empty byte
                    # strings were being stored as the literal 2-byte string
                    # "\x". Check for this and convert back.
                    value = b''
                else:
                    value = value.encode('utf-8')
            elif isinstance(value, six.memoryview):
                value = bytes(value)

            if isinstance(value, Base64DecodedValue) or not pk_set:
                value = base64_encode(value)

        obj.__dict__[self.field.name] = value

    def __get__(self, obj, *args, **kwargs):
        """Return a decoded value from the field.

        Args:
            obj (django.db.models.Model):
                The model owning the field.

            *args (tuple):
                Unused positional arguments.

            **kwargs (dict):
                Unused keyword arguments.

        Returns:
            Base64DecodedValue:
            The decoded value from the field. If no value has yet been stored,
            this will return ``None`` instead.

        Raises:
            AttributeError:
            A ``None`` value was passed for the object.
        """
        if obj is None:
            raise AttributeError('Can only be accessed via an instance.')

        value = obj.__dict__[self.field.name]

        if value is not None:
            value = Base64DecodedValue(base64_decode(value))

        return value


class Base64Field(models.TextField):
    """A text field for storing Base64-encoded values.

    This is used to store data (such as binary data or encoding-sensitive data)
    to the database in a Base64 encoding. This is useful if you're dealing
    with unknown encodings and must guarantee that no modifications to the text
    occurs and that you can read/write the data in any database with any
    encoding.

    When accessing this field on an instance of a model, a
    :py:class:`Base64DecodedValue` will be returned consisting of the decoded
    data. This is a byte string, and can be treated as such. If set back into
    the field, it will be re-encoded and stored.

    When writing to the field, the behavior changes based on the type of value
    and the state of the model:

    * If the model instance is new (has not yet been saved in the database),
      any string set will be encoded. This allows the value to be passed during
      a ``create()`` call.

    * If the model is not new, any string that's set will be assumed to be
      encoded by the caller.

    * Passing a :py:class:`Base64DecodedValue` byte string will always cause
      the stored data to be encoded.

    The field also adds a :samp:`get_{fieldname}_base64()` method to the
    class, which returns the raw Base64 encoded content from the database.
    """

    def contribute_to_class(self, cls, name):
        """Set attributes on a new model class.

        This is called when constructing a model class making use of this
        field. It sets the field's attribute to a
        :py:class:`Base64FieldCreator` and adds a
        :samp:`get_{fieldname}_base64()` method to the class.

        Args:
            cls (type):
                The class to add the arguments to.

            name (str):
                The name of the field.
        """
        super(Base64Field, self).contribute_to_class(cls, name)

        setattr(cls, self.name, Base64FieldCreator(self))
        setattr(cls, 'get_%s_base64' % self.name,
                lambda model_instance: model_instance.__dict__[self.name])

    def get_prep_value(self, value):
        """Return a value prepared for the field.

        This prepares the value for use in database operations (saving
        or querying). It will convert the value into a Unicode Base64-encoded
        string.

        Args:
            value (object):
                The value to prepare. This is expected to be a string or a
                :py:class:`Base64DecodedValue`. If the latter, it will be
                encoded.

        Returns:
            unicode:
            The resulting value.

        Raises:
            Base64TypeError:
                The type of value provided could not be prepared for writing.
        """
        if value is not None:
            if isinstance(value, Base64DecodedValue):
                value = base64_encode(value).decode('utf-8')
            elif isinstance(value, bytes):
                value = value.decode('utf-8')
            elif isinstance(value, six.memoryview):
                value = force_text(bytes(value))
            elif not isinstance(value, six.text_type):
                raise Base64TypeError(value)

        return value

    def to_python(self, value):
        """Return a Python representation of a value for the field.

        This will decode the value (if not already decoded) and return it.

        Args:
            value (object):
                The value to return a decoded value for.

        Returns:
            Base64DecodedValue:
            The decoded version of the provided value.

        Raises:
            Base64TypeError:
                The type of value provided could not be prepared for writing.
        """
        if value is not None and not isinstance(value, Base64DecodedValue):
            if isinstance(value, six.text_type):
                value = value.encode('utf-8')
            elif isinstance(value, six.memoryview):
                value = bytes(value)
            elif not isinstance(value, bytes):
                raise Base64TypeError(value)

            value = Base64DecodedValue(base64_decode(value))

        return value

    def value_to_string(self, obj):
        """Return a string representation of the value from a model.

        The returned value will be a Base64-encoded string value.

        Args:
            obj (django.db.models.Model):
                The model instance owning the field and value.

        Returns:
            bytes:
            The Base64-encoded byte string for the stored value.
        """
        value = self.value_from_object(obj)
        assert value is None or isinstance(value, Base64DecodedValue)

        if value is not None:
            value = base64_encode(value)

        return value
