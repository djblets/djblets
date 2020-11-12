from __future__ import unicode_literals

import copy
import json
import logging
import warnings
from ast import literal_eval

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_init
from django.utils import six
from django.utils.translation import ugettext_lazy as _

from djblets.db.validators import validate_json
from djblets.util.decorators import cached_property
from djblets.util.serializers import DjbletsJSONEncoder


logger = logging.getLogger(__name__)


class JSONFormField(forms.CharField):
    """Provides a form field for JSON input.

    This is meant to be used by :py:class:`JSONField`, and handles the work of
    rendering JSON content in a more human-editable way for editing (by sorting
    keys and adding indentation), and then validating and returning the
    resulting JSON document back for storage in the field.

    Attributes:
        encoder (json.JSONEncoder):
            The JSON encoder being used to serialize JSON data for editing.
    """

    def __init__(self, encoder=None, encoder_cls=None, encoder_kwargs=None,
                 *args, **kwargs):
        """Initialize the field.

        Args:
            encoder (json.JSONEncoder, optional):
                The explicit JSON encoder instance to use. If specified, this
                takes priority over ``encoder_cls`` and ``encoder_kwargs``,
                and will prevent the field from nicely formatting the
                contents for editing.

                .. deprecated:: 1.0.1

                   ``encoder_cls`` and ``encoder_kwargs`` should be used
                   instead.

            encoder_cls (type, optional):
                The type of encoder to use for serializing the JSON document
                for editing. This must be a subclass of
                :py:class:`json.JSONEncoder`.

            encoder_kwargs (dict, optional):
                Keyword arguments to pass to the constructor for the encoder.

            *args (tuple):
                Extra positional arguments to pass to the field.

            **kwargs (dict):
                Extra keyword arguments to pass to the field.
        """
        super(JSONFormField, self).__init__(*args, **kwargs)

        if encoder is None:
            if encoder_cls is None:
                encoder_cls = DjbletsJSONEncoder
                encoder_kwargs = {
                    'strip_datetime_ms': False,
                }

            encoder = encoder_cls(**dict({
                'indent': 2,
                'separators': (',', ': '),
                'sort_keys': True,
            }, **encoder_kwargs))

        self.encoder = encoder

    def prepare_value(self, value):
        """Prepare a field's value for storage in the database.

        This will encode the value to JSON (unless it's already a string).

        Args:
            value (object):
                The JSON-serializable value to encode.

        Returns:
            unicode: The resulting JSON string.
        """
        if isinstance(value, six.string_types):
            return value
        else:
            return self.encoder.encode(value)

    def to_python(self, value):
        """Return the Python representation of the value in the field.

        This will attempt to deserialize the value and return it. If the
        value is not a string, it will be returned directly.

        Args:
            value (object):
                The value stored for the field. This is expected to be a
                string representing serialized JSON data.

        Returns:
            object:
            The deserialized JSON object, or ``None`` if it's an empty string.

        Raises:
            django.core.exceptions.ValidationError:
                The value was not able to be deserialized as JSON content.
        """
        if isinstance(value, six.string_types):
            if not value:
                return None

            try:
                return json.loads(value)
            except ValueError as e:
                raise ValidationError(
                    six.text_type(e),
                    code='invalid',
                    params={
                        'value': value,
                    })
        else:
            return value


class JSONField(models.TextField):
    """A field for storing JSON-encoded data.

    The data is accessible as standard Python data types and is transparently
    encoded to and decoded from a JSON string in the database.

    Consumers can specify custom encoding behavior by providing an encoder
    class and keyword arguments. By default,
    :py:class:`~djblets.util.serializes.DjbletsJSONEncoder` is used, which
    supports lazy strings, datetimes, and model-specified custom encoding
    behavior.
    """

    serialize_to_string = True
    default_validators = [validate_json]
    default_error_messages = {
        'invalid_type': _('%(type)s is not a supported value type.'),
    }

    def __init__(self, verbose_name=None, name=None, encoder_cls=None,
                 encoder_kwargs=None, **kwargs):
        """Initialize the field.

        Args:
            verbose_name (unicode, optional):
                The verbose name shown for the field.

            name (unicode, optional):
                The attribute name of the field.

            encoder_cls (type, optional):
                The type of encoder to use for serializing the JSON document
                for storage and editing. This must be a subclass of
                :py:class:`json.JSONEncoder`.

            encoder_kwargs (dict, optional):
                Keyword arguments to pass to the constructor for the encoder.
                This may be modified by the field.

            **kwargs (dict):
                Additional keyword arguments for the field.
        """
        super(JSONField, self).__init__(verbose_name,
                                        name,
                                        blank=kwargs.pop('blank', True),
                                        **kwargs)

        if encoder_cls is None:
            encoder_cls = DjbletsJSONEncoder
            encoder_kwargs = {
                'strip_datetime_ms': False,
            }

        self.encoder_cls = encoder_cls
        self.encoder_kwargs = encoder_kwargs or {}
        self.encoder_kwargs['sort_keys'] = True

    @cached_property
    def encoder(self):
        """An encoder instance used for this field."""
        return self.encoder_cls(**self.encoder_kwargs)

    def contribute_to_class(self, cls, name):
        """Add methods/signal handlers to the model owning this field.

        This will add :samp:`get_{fieldname}_json()` and
        :samp:`set_{fieldname}_json()` methods to the model, which will
        allow retrieving and setting the serialized data directly.

        It also listens for when an instance of the model is initialized and
        sets the field to point to the deserialized JSON data.

        Args:
            cls (type):
                The :py:class:`~django.db.models.Model` class to contribute to.

            name (unicode):
                The name of this field on the model.
        """
        def get_json(model_instance):
            return self.value_to_string(model_instance)

        def set_json(model_instance, json):
            setattr(model_instance, self.attname, self.loads(json))

        super(JSONField, self).contribute_to_class(cls, name)

        setattr(cls, 'get_%s_json' % self.name, get_json)
        setattr(cls, 'set_%s_json' % self.name, set_json)

        post_init.connect(self.post_init, sender=cls)

    def pre_save(self, model_instance, add):
        """Return serialized field data to save on a model instance.

        Args:
            model_instance (django.db.models.Model):
                The model instance being saved.

            add (bool, unused):
                Whether this is a new instance being added to the database.
                This is ignored.

        Returns:
            unicode:
            The serialized data to save.
        """
        return self.dumps(getattr(model_instance, self.attname, None))

    def post_init(self, instance, **kwargs):
        """Handle initialization of a model instance.

        This will deserialize the stored data from the database and set it as
        the field data on the model.

        Args:
            instance (django.db.models.Model):
                The model instance being initialized.

            **kwargs (dict):
                Extra keyword arguments from the signal.
        """
        # Check if the field is deferred. If so, we don't want to do anything,
        # as a fetch attempt would result in an SQL query.
        if self.attname not in instance.__dict__:
            return

        value = self.value_from_object(instance)

        if isinstance(value, (dict, list)):
            value = copy.deepcopy(value)
        elif isinstance(value, six.string_types):
            value = self.loads(value)
        elif value is None:
            value = {}
        else:
            raise ValidationError(
                self.error_messages['invalid_type'],
                code='invalid',
                params={
                    'type': type(value),
                })

        setattr(instance, self.attname, value)

    def get_prep_value(self, value):
        """Return the serialized value prepared for storage.

        This will serialize the data, if it's a JSON structure and not
        already a string, preparing it for storage in the database or
        another location.

        Args:
            value (object):
                The value to prepare.

        Returns:
            unicode:
            The serialized representation of the value.
        """
        if value is None or isinstance(value, six.string_types):
            return value

        return self.dumps(value)

    def value_to_string(self, obj):
        """Return the serialized JSON data from the field.

        Args:
            obj (django.db.models.Model):
                The model instance containing the field.

        Returns:
            unicode:
            The serialized JSON data from the field.
        """
        return self.dumps(self.value_from_object(obj))

    def to_python(self, value):
        """Return a value suitable for using in Python code.

        This will return the deserialized version of the data, allowing
        Python code to work with the data directly.

        Args:
            value (object):
                The value to make usable in Python code.

        Returns:
            object:
            The deserialized data.
        """
        if isinstance(value, six.string_types):
            value = self.loads(value)

        return value

    def dumps(self, data):
        """Return serialized version of the provided JSON document.

        If the data is already a string, it will be provided directly.
        Otherwise, it will use the field's associated JSON encoder to serialize
        the data.

        Args:
            data (object):
                The data to serialize.

        Returns:
            unicode:
            The serialized JSON data.
        """
        if isinstance(data, six.string_types):
            return data
        else:
            return self.encoder.encode(data)

    def loads(self, val):
        """Return a JSON document from the serialized JSON data.

        This will first attempt to deserialize the JSON data using the standard
        JSON decoder. If it's unable to do so, or it gets back what appears
        to be a double-encoded JSON document or a Python string representation
        of a JSON document, it will attempt to parse the value and return a
        proper representation.

        Args:
            val (unicode):
                The serialized JSON data to deserialize.

        Returns:
            object:
            The deserialized JSON document.
        """
        if not val:
            return {}

        try:
            if not isinstance(val, six.text_type):
                val = val.decode(settings.DEFAULT_CHARSET)

            val = json.loads(val)

            # Old versions of JSONField could end up double-encoding JSON
            # data, resulting in a string being stored that then needs to be
            # parsed again. Check for this and try to deserialize. Worst-case,
            # the JSON decoder decides it's actually a string and returns it.
            if isinstance(val, six.string_types):
                logger.warning('JSONField decode error. Expected dictionary, '
                               'got string for input "%s"',
                               val)

                val = json.loads(val)
        except ValueError:
            # There's probably embedded unicode markers (like u'foo') in the
            # string, due to bugs in old versions of JSONField. We have to
            # eval it.
            try:
                val = literal_eval(val)
            except Exception as e:
                logger.error('Failed to eval JSONField data "%r": %s',
                             val, e)
                val = {}

            if isinstance(val, six.string_types):
                logger.warning('JSONField decode error after literal_eval: '
                               'Expected dictionary, got string: %r',
                               val)
                val = {}

        return val

    def formfield(self, **kwargs):
        """Return a form field that can be used to edit this data.

        Args:
            **kwargs (dict):
                Keyword arguments to pass to the subclass.

        Returns:
            JSONFormField:
            The resulting form field.
        """
        formfield_kwargs = dict({
            'form_class': JSONFormField,
            'encoder': None,
            'encoder_cls': self.encoder_cls,
            'encoder_kwargs': self.encoder_kwargs,
        }, **kwargs)

        if self.encoder_cls is None:
            # We're coming from a legacy caller that's providing an encoder
            # instance instead of the class/keyword arguments. Pass that
            # encoder to JSONFormField. It will go into legacy mode and turn
            # off some niceties for editing content.
            formfield_kwargs['encoder'] = self.encoder

        return super(JSONField, self).formfield(**formfield_kwargs)

    def deconstruct(self):
        """Deconstruct the field for Django migrations.

        This makes JSONField migration-safe by encoding the default value
        to a string so that it can be safely loaded into the database.

        This is only used on Django 1.7+.

        .. versionadded:: 0.9

        Returns:
            tuple:
            A tuple of (name, module path, positional arguments, keyword
            arguments).
        """
        name, path, field_args, field_kwargs = \
            super(JSONField, self).deconstruct()

        default = field_kwargs.get('default')

        if default is not None:
            if isinstance(default, type):
                default = self.dumps(default())
            else:
                default = self.dumps(default)

            field_kwargs['default'] = default

        return name, path, field_args, field_kwargs
