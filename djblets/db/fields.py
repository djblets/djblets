#
# fields.py -- Model fields.
#
# Copyright (c) 2007-2008  Christian Hammond
# Copyright (c) 2007-2008  David Trowbridge
# Copyright (c) 2008-2013  Beanbag, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

import base64
import json
import logging
import warnings
import weakref
from ast import literal_eval
from datetime import datetime

import django
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.db.models.signals import (m2m_changed, post_delete, post_init,
                                      post_save, pre_delete)
from django.utils import six
from django.utils.encoding import smart_unicode
try:
    from django.db.models.expressions import Combinable
    QueryExpressionType = Combinable
except ImportError:
    from django.db.models.expressions import ExpressionNode
    QueryExpressionType = ExpressionNode

from djblets.db.validators import validate_json
from djblets.util.dates import get_tz_aware_utcnow
from djblets.util.decorators import cached_property
from djblets.util.serializers import DjbletsJSONEncoder


logger = logging.getLogger(__name__)


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
        pk_set = pk_val is not None and smart_unicode(pk_val) != ''

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


class JSONFormField(forms.CharField):
    """Provides a form field for JSON input.

    This is meant to be used by JSONField, and handles the work of
    normalizing a Python data structure back into a serialized JSON
    string for editing.
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
    """
    A field for storing JSON-encoded data. The data is accessible as standard
    Python data types and is transparently encoded/decoded to/from a JSON
    string in the database.
    """
    serialize_to_string = True
    default_validators = [validate_json]

    def __init__(self, verbose_name=None, name=None, encoder=None,
                 encoder_cls=None, encoder_kwargs=None, **kwargs):
        """Initialize the field.

        Args:
            verbose_name (unicode, optional):
                The verbose name shown for the field.

            name (unicode, optional):
                The attribute name of the field.

            encoder (json.JSONEncoder, optional):
                The explicit JSON encoder instance to use. If specified, this
                takes priority over ``encoder_cls`` and ``encoder_kwargs``,
                and will prevent the field from nicely formatting the
                contents for editing.

                .. deprecated:: 1.0.1

                   ``encoder_cls`` and ``encoder_kwargs`` should be used
                   instead. Specifying ``encoder`` will emit a warning.

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

        if encoder is not None:
            warnings.warn('The encoder argument to JSONField has been '
                          'replaced by the encoder_cls and encoder_kwargs '
                          'arguments. Support for encoder is deprecated.',
                          DeprecationWarning)

            # Override the encoder property to hard-code the provided instance.
            self.encoder = encoder
        elif encoder_cls is None:
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
        def get_json(model_instance):
            return self.dumps(getattr(model_instance, self.attname, None))

        def set_json(model_instance, json):
            setattr(model_instance, self.attname, self.loads(json))

        super(JSONField, self).contribute_to_class(cls, name)

        setattr(cls, "get_%s_json" % self.name, get_json)
        setattr(cls, "set_%s_json" % self.name, set_json)

        post_init.connect(self.post_init, sender=cls)

    def pre_save(self, model_instance, add):
        return self.dumps(getattr(model_instance, self.attname, None))

    def post_init(self, instance=None, **kwargs):
        value = self.value_from_object(instance)

        if value:
            value = self.loads(value)
        else:
            value = {}

        setattr(instance, self.attname, value)

    def get_db_prep_save(self, value, *args, **kwargs):
        if not isinstance(value, six.string_types):
            value = self.dumps(value)

        return super(JSONField, self).get_db_prep_save(value, *args, **kwargs)

    def value_to_string(self, obj):
        return self.dumps(self.value_from_object(obj))

    def dumps(self, data):
        if isinstance(data, six.string_types):
            return data
        else:
            return self.encoder.encode(data)

    def loads(self, val):
        try:
            val = json.loads(val, encoding=settings.DEFAULT_CHARSET)

            # XXX We need to investigate why this is happening once we have
            #     a solid repro case.
            if isinstance(val, six.string_types):
                logger.warning("JSONField decode error. Expected dictionary, "
                               "got string for input '%s'",
                               val)

                # For whatever reason, we may have gotten back
                val = json.loads(val, encoding=settings.DEFAULT_CHARSET)
        except ValueError:
            # There's probably embedded unicode markers (like u'foo') in the
            # string. We have to eval it.
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


class CounterField(models.IntegerField):
    """A field that provides atomic counter updating and smart initialization.

    The CounterField makes it easy to atomically update an integer,
    incrementing or decrementing it, without raise conditions or conflicts.
    It can update a single instance at a time, or a batch of objects at once.

    CounterField is useful for storing counts of objects, reducing the number
    of queries performed. This requires that the calling code properly
    increments or decrements at all the right times, of course.

    This takes an optional ``initializer`` parameter that, if provided, can
    be used to auto-populate the field the first time the model instance is
    loaded, perhaps based on querying a number of related objects. The value
    passed to ``initializer`` must be a function taking the model instance
    as a parameter, and must return an integer or None. If it returns None,
    the counter will not be updated or saved.

    The model instance will gain four new functions:

        * ``increment_{field_name}`` - Atomically increment by one.
        * ``decrement_{field_name}`` - Atomically decrement by one.
        * ``reload_{field_name}`` - Reload the value in this instance from the
                                    database.
        * ``reinit_{field_name}`` - Re-initializes the stored field using the
                                    initializer function.

    The field on the class (not the instance) provides two functions for
    batch-updating models:

        * ``increment`` - Takes a queryset and increments this field for
                          each object.
        * ``decrement`` - Takes a queryset and decrements this field for
                          each object.
    """
    @classmethod
    def increment_many(cls, model_instance, values, reload_object=True):
        """Increments several fields on a model instance at once.

        This takes a model instance and dictionary of fields to values,
        and will increment each of those fields by that value.

        If reload_object is True, then the fields on the instance will
        be reloaded to reflect the current values.
        """
        cls._update_values(model_instance, values, reload_object, 1)

    @classmethod
    def decrement_many(cls, model_instance, values, reload_object=True):
        """Decrements several fields on a model instance at once.

        This takes a model instance and dictionary of fields to values,
        and will decrement each of those fields by that value.

        If reload_object is True, then the fields on the instance will
        be reloaded to reflect the current values.
        """
        cls._update_values(model_instance, values, reload_object, -1)

    @classmethod
    def _update_values(cls, model_instance, values, reload_object, multiplier):
        update_values = {}

        for attname, value in six.iteritems(values):
            if value != 0:
                update_values[attname] = F(attname) + value * multiplier

        cls._set_values(model_instance, update_values, reload_object)

    @classmethod
    def _set_values(cls, model_instance, values, reload_object=True):
        if values:
            queryset = model_instance.__class__.objects.filter(
                pk=model_instance.pk)
            queryset.update(**values)

            if reload_object:
                cls._reload_model_instance(model_instance,
                                           six.iterkeys(values))

    @classmethod
    def _reload_model_instance(cls, model_instance, attnames):
        """Reloads the value in this instance from the database."""
        q = model_instance.__class__.objects.filter(pk=model_instance.pk)
        values = q.values(*attnames)[0]

        for attname, value in six.iteritems(values):
            setattr(model_instance, attname, value)

    def __init__(self, verbose_name=None, name=None,
                 initializer=None, default=None, **kwargs):
        kwargs.update({
            'blank': True,
            'null': True,
        })

        super(CounterField, self).__init__(verbose_name, name, default=default,
                                           **kwargs)

        self._initializer = initializer
        self._locks = {}

    def increment(self, queryset, increment_by=1):
        """Increments this field on every object in the provided queryset."""
        queryset.update(**{self.attname: F(self.attname) + increment_by})

    def decrement(self, queryset, decrement_by=1):
        """Decrements this field on every object in the provided queryset."""
        queryset.update(**{self.attname: F(self.attname) - decrement_by})

    def contribute_to_class(self, cls, name):
        def _increment(model_instance, *args, **kwargs):
            self._increment(model_instance, *args, **kwargs)

        def _decrement(model_instance, *args, **kwargs):
            self._decrement(model_instance, *args, **kwargs)

        def _reload(model_instance):
            self._reload(model_instance)

        def _reinit(model_instance):
            self._reinit(model_instance)

        super(CounterField, self).contribute_to_class(cls, name)

        setattr(cls, 'increment_%s' % self.name, _increment)
        setattr(cls, 'decrement_%s' % self.name, _decrement)
        setattr(cls, 'reload_%s' % self.name, _reload)
        setattr(cls, 'reinit_%s' % self.name, _reinit)
        setattr(cls, self.attname, self)

        # We need to prevent CounterFields (or any subclasses) from being
        # saved by default. We'd ideally override save() or save_base(), but
        # can't safely do that here, and we can't modify update_fields due to
        # how it would impact the save process. So we need to go deeper,
        # overriding _do_update(), which actually receives the values and
        # field instances being saved. From there, we can filter out any
        # CounterFields by default.
        setattr(cls, '_do_update', self.__class__._model_do_update)

        post_init.connect(self._post_init, sender=cls)

    def _increment(self, model_instance, reload_object=True, increment_by=1):
        """Increments this field by one."""
        if increment_by != 0:
            cls = model_instance.__class__
            self.increment(cls.objects.filter(pk=model_instance.pk),
                           increment_by)

            if reload_object:
                self._reload(model_instance)

    def _decrement(self, model_instance, reload_object=True, decrement_by=1):
        """Decrements this field by one."""
        if decrement_by != 0:
            cls = model_instance.__class__
            self.decrement(cls.objects.filter(pk=model_instance.pk),
                           decrement_by)

            if reload_object:
                self._reload(model_instance)

    def _reload(self, model_instance):
        """Reloads the value in this instance from the database."""
        self._reload_model_instance(model_instance, [self.attname])

    def _reinit(self, model_instance):
        """Re-initializes the value in the database from the initializer."""
        if not (model_instance.pk or self._initializer or
                six.callable(self._initializer)):
            # We don't want to end up defaulting this to 0 if creating a
            # new instance unless an initializer is provided. Instead,
            # we'll want to handle this the next time the object is
            # accessed.
            return

        value = 0

        if self._initializer:
            if isinstance(self._initializer, QueryExpressionType):
                value = self._initializer
            elif six.callable(self._initializer):
                model_instance_id = id(model_instance)
                self._locks[model_instance_id] = 1
                value = self._initializer(model_instance)
                del self._locks[model_instance_id]

        if value is not None:
            is_expr = isinstance(value, QueryExpressionType)

            if is_expr and not model_instance.pk:
                value = 0
                is_expr = False

            if is_expr:
                cls = model_instance.__class__
                cls.objects.filter(pk=model_instance.pk).update(**{
                    self.attname: value,
                })

                self._reload_model_instance(model_instance, [self.attname])
            else:
                setattr(model_instance, self.attname, value)

                if model_instance.pk:
                    model_instance.save(update_fields=[self.attname])

    def _post_init(self, instance=None, **kwargs):
        # Prevent the possibility of recursive lookups where this
        # same CounterField on this same instance tries to initialize
        # more than once. In this case, this will have the updated
        # value shortly.
        if instance:
            instance_id = id(instance)

            if instance_id not in self._locks:
                self._do_post_init(instance)

    def _do_post_init(self, instance):
        value = self.value_from_object(instance)

        if value is None:
            reinit = getattr(instance, 'reinit_%s' % self.name)
            reinit()

    @staticmethod
    def _model_do_update(model, base_qs, using, pk_val, values, update_fields,
                         forced_update):
        """Perform a SQL UPDATE for a table.

        We override Django's default implementation to first filter out some
        fields, allowing us to skip CounterFields (unless setting to None or
        explicitly requested in ``update_fields``).

        Args:
            model (django.db.models.Model):
                The model instance that this method was called on.

            base_qs (django.db.models.query.QuerySet):
                The queryset used for the update operation.

            using (unicode):
                The database connection being used.

            pk_val (int):
                The primary key value for the instance.

            values (list of tuple):
                The list of update values. Each item is a tuple in the form
                of ``(field_instance, None, value)``.

            update_fields (list of unicode):
                The specific fields the caller wanted to update. This may be
                ``None``.

            forced_update (bool):
                Whether the requester is specifically forcing a SQL UPDATE.

        Returns:
            bool:
            Whether there were any updates performed.
        """
        values = [
            value
            for value in values
            if (not isinstance(value[0], CounterField) or
                value[2] is None or
                (update_fields and value[0].attname in update_fields))
        ]

        return super(model.__class__, model)._do_update(
            base_qs, using, pk_val, values, update_fields, forced_update)


class RelationCounterField(CounterField):
    """A field that provides an atomic count of a relation.

    RelationCounterField is a specialization of CounterField that tracks
    how many objects there are on the other side of a ManyToManyField or
    ForeignKey relation.

    RelationCounterField takes the name of a relation (either a field name,
    for a forward ManyToManyField relation, or the "related_name" for
    the reverse relation of another model's ForeignKey or ManyToManyField.
    (Note that using a forward ForeignKey relation is considered invalid,
    as the count can only be 1 or 0.)

    The counter will be initialized with the number of objects on the
    other side of the relation, and this will be kept updated so long as
    all updates to the table are made using standard create/save/delete
    operations on models.

    Note that updating a relation outside of a model's regular API (such as
    through raw SQL or something like an update() call) will cause the
    counters to get out of sync. They would then need to be reset using
    ``reinit_{field_name}``.
    """
    # Stores state across all saved instances of a RelationCounterField.
    #
    # Django doesn't make it easy to track updates to the other side of a
    # relation, meaning we have to do it ourselves. This dictionary will
    # weakly track InstanceState objects (which are tied to the lifecycle of
    # a particular model instancee). These objects are used to look up model
    # instances and their RelationCounterFields, given a model name, model
    # instance ID, and a relation name.
    _saved_instance_states = weakref.WeakValueDictionary()

    # Stores instance states we're tracking whose instances haven't yet been
    # saved.
    #
    # An unsaved instance may never be saved, but we still need to listen to
    # events on it. To do this, we set up an InstanceState, like above,
    # keeping track of the information and signal connections related to it.
    _unsaved_instance_states = {}

    # Most of the hard work really lives in RelationTracker below. Here, we
    # store all registered instances of RelationTracker. There will be one
    # per model_cls/relation_name pair.
    _relation_trackers = {}

    class InstanceState(object):
        """Tracks state for a RelationCounterField instance assocation.

        State instances are bound to the lifecycle of a model instance.
        They keep track of the model instance (using a weak reference) and
        all RelationCounterFields tied to the relation name provided.

        These are used for looking up the proper instance and
        RelationCounterFields on the other end of a reverse relation, given
        a model, relation name, and IDs, through the
        :py:attr:`RelationCounterField._saved_instance_states` or
        :py:attr:`RelationCounterField._unsaved_instance_states` or
        dictionaries.

        Instance states can either represent saved instances or unsaved
        instances. Unsaved instance states represent instances that haven't yet
        been saved to the database (with a primary key of None). While saved
        instance states exist per-instance/relation name, there's only one
        unsaved instance state per instance.

        Once an unsaved instance is saved, new instance states will be stored
        for each field associated (which many turn into multiple states, as
        there's one per relation name). The old unsaved instance state is then
        discarded.
        """

        def __init__(self, model_instance, fields):
            """Initialize the state.

            Args:
                model_instance (django.db.models.Model):
                    The model instance that this state tracks.

                fields (list of django.db.models.Field):
                    The list of field instances tracked along with this state.
                    For a saved instance state, these are all fields that have
                    the same relation. For an unsaved instance state, these
                    are simply all fields tracked on the instance.
            """
            self.fields = fields
            self.to_clear = set()
            self.dispatch_uid = '%s.%s:%s' % (self.__class__.__module__,
                                              self.__class__.__name__,
                                              id(model_instance))
            self.model_instance_ref = weakref.ref(model_instance,
                                                  self._on_instance_destroyed)
            self.model_cls = model_instance.__class__
            self.model_instance_id = id(model_instance)

            if model_instance.pk is None:
                post_save.connect(self._on_instance_first_save,
                                  sender=self.model_cls,
                                  dispatch_uid=self.dispatch_uid)
            else:
                pre_delete.connect(self._on_instance_pre_delete,
                                   sender=self.model_cls,
                                   dispatch_uid=self.dispatch_uid)

        @property
        def model_instance(self):
            return self.model_instance_ref()

        def reinit_fields(self):
            """Reinitializes all associated fields' counters."""
            model_instance = self.model_instance

            for field in self.fields:
                field._reinit(model_instance)

        def increment_fields(self, by=1):
            """Increments all associated fields' counters."""
            RelationCounterField.increment_many(
                self.model_instance,
                dict([(field.attname, by) for field in self.fields]))

        def decrement_fields(self, by=1):
            """Decrements all associated fields' counters."""
            RelationCounterField.decrement_many(
                self.model_instance,
                dict([(field.attname, by) for field in self.fields]))

        def zero_fields(self):
            """Zeros out all associated fields' counters."""
            RelationCounterField._set_values(
                self.model_instance,
                dict([(field.attname, 0) for field in self.fields]))

        def reload_fields(self):
            """Reloads all associated fields' counters."""
            RelationCounterField._reload_model_instance(
                self.model_instance,
                [field.attname for field in self.fields])

        def __repr__(self):
            """Return a string representation of the instance state.

            Returns:
                unicode:
                A string representation listing the instance information.
            """
            model_instance = self.model_instance

            if model_instance:
                return '<RelationCounterField.InstanceState for %s.pk=%s>' % (
                    model_instance.__class__.__name__,
                    model_instance.pk)
            else:
                return (
                    '<RelationCounterField.InstanceState for %r (destroyed)>'
                    % self.model_cls)

        def _on_instance_first_save(self, instance, created=False, **kwargs):
            """Handler for the first save on a newly created instance.

            This will reset information on this instance, removing this
            existing state, and will then add new instance states for each
            field relation.

            Args:
                instance (django.db.models.Model):
                    The model instance being saved.

                created (bool):
                    Whether the object was created. This must always be
                    true for this handler.

                **kwargs (dict):
                    Extra keyword arguments passed to the handler.
            """
            if instance is not self.model_instance:
                return

            assert created
            assert instance.pk is not None

            instance_cls = instance.__class__

            # Stop listening immediately for any new signals here.
            # The Signal stuff deals with thread locks, so we shouldn't
            # have to worry about reaching any of this twice.
            post_save.disconnect(sender=instance_cls,
                                 dispatch_uid=self.dispatch_uid)

            # This is a new row in the database (that is, the model instance
            # has been saved for the very first time), we need to flush any
            # existing state. This will ensure the unsaved version of this
            # state does not remain.
            RelationCounterField._reset_state(instance_cls=instance_cls,
                                              instance_pk=instance.pk,
                                              instance_id=id(instance))

            # Now we can register each RelationCounterField on here.
            for field in instance_cls._meta.local_fields:
                if isinstance(field, RelationCounterField):
                    RelationCounterField._store_state(instance, field)

        def _on_instance_destroyed(self, *args):
            """Handler for when the instance is destroyed.

            This will remove all state related to the instance. That will
            result in the state object being destroyed.

            Args:
                *args (tuple, unused):
                    Arguments passed to the callback.
            """
            RelationCounterField._reset_state(
                instance_cls=self.model_cls,
                instance_pk=None,
                instance_id=self.model_instance_id)

        def _on_instance_pre_delete(self, instance, **kwargs):
            """Handler for when an instance is about to be deleted.

            This will reset the state of the instance, unregistering it from
            lists, and removing any pending signal connections.

            Args:
                instance (django.db.models.Model):
                    The instance being deleted.
            """
            if instance is self.model_instance:
                RelationCounterField._reset_state(
                    instance_cls=instance.__class__,
                    instance_pk=instance.pk,
                    instance_id=id(instance))

            pre_delete.disconnect(sender=self.model_cls,
                                  dispatch_uid=self.dispatch_uid)

    class RelationTracker(object):
        """Tracks relations and updates state for all affected CounterFields.

        This class is responsible for all the hard work of updating
        RelationCounterFields refererring to a relation, based on updates
        to that relation. It's really the meat of RelationCounterField.

        Each RelationTracker is responsible for a given model/relation name
        pairing, across all instances of a model and across all
        RelationCounterFields following that relation name.

        The main reason the code lives here instead of in each
        RelationCounterField is to keep state better in sync and to ensure
        we're only ever dealing with one set of queries per relation name.
        We're also simplifying signal registration, helping to make things
        less error-prone.
        """
        def __init__(self, model_cls, rel_field_name):
            self._rel_field_name = rel_field_name

            if django.VERSION >= (1, 8):
                # Django >= 1.8
                self._rel_field = model_cls._meta.get_field(rel_field_name)
                rel_model = self._rel_field.model
                is_rel_direct = (not self._rel_field.auto_created or
                                 self._rel_field.concrete)
                is_m2m = self._rel_field.many_to_many
            else:
                # Django < 1.8
                self._rel_field, rel_model, is_rel_direct, is_m2m = \
                    model_cls._meta.get_field_by_name(rel_field_name)

            self._is_rel_reverse = not is_rel_direct

            if not is_m2m and is_rel_direct:
                # This combination doesn't make any sense. There's only ever
                # one item on this side, so no point in counting. Let's just
                # complain about it.
                raise ValueError(
                    "RelationCounterField cannot work with the forward end of "
                    "a ForeignKey ('%s')"
                    % rel_field_name)

            dispatch_uid = '%s-%s.%s-related-save' % (
                id(self),
                self.__class__.__module__,
                self.__class__.__name__)

            if is_m2m:
                # This is going to be one end or the other of a ManyToManyField
                # relation.
                if is_rel_direct:
                    # This is a ManyToManyField, and we can get the 'rel'
                    # attribute through it.
                    m2m_field = self._rel_field
                    self._related_name = m2m_field.rel.related_name
                else:
                    # This is a RelatedObject. We need to get the field through
                    # this.
                    m2m_field = self._rel_field.field
                    self._related_name = m2m_field.attname

                # Listen for all M2M updates on the through table for this
                # ManyToManyField. Unfortunately, we can't look at a
                # particular instance, but we'll use state tracking to do the
                # necessary lookups and updates in the handler.
                m2m_changed.connect(
                    self._on_m2m_changed,
                    weak=False,
                    sender=m2m_field.rel.through,
                    dispatch_uid=dispatch_uid)
            else:
                # This is a ForeignKey or similar. It must be the reverse end.
                assert not is_rel_direct

                model = self._get_rel_field_related_model(self._rel_field)
                self._related_name = self._rel_field.field.attname

                # Listen for deletions and saves on that model type. In the
                # handler, we'll look up state for the other end of the
                # relation (the side owning this RelationCounterField), so that
                # we can update the counts.
                #
                # Unfortunately, we can't listen on the particular instance, so
                # we use the state tracking.
                post_delete.connect(
                    self._on_related_delete,
                    weak=False,
                    sender=model,
                    dispatch_uid=dispatch_uid)
                post_save.connect(
                    self._on_related_save,
                    weak=False,
                    sender=model,
                    dispatch_uid=dispatch_uid)

        def _on_m2m_changed(self, instance, action, reverse, model, pk_set,
                            **kwargs):
            """Handler for when a M2M relation has been updated.

            This will figure out the necessary operations that may need to be
            performed, given the update.

            For post_add/post_remove operations, it's pretty simple. We see
            if there are any instances (by way of stored state) for any of the
            affected IDs, and we re-initialize them.

            For clear operations, it's more tricky. We have to fetch all
            instances on the other side of the relation before any database
            changes are made, cache them in the InstanceState, and then update
            them all in post_clear.
            """
            if reverse != self._is_rel_reverse:
                # This doesn't match the direction we're paying attention to.
                # Ignore it.
                return

            is_post_clear = (action == 'post_clear')
            is_post_add = (action == 'post_add')
            is_post_remove = (action == 'post_remove')

            if is_post_clear or is_post_add or is_post_remove:
                state = RelationCounterField._get_state(
                    instance.__class__, instance.pk, self._rel_field_name)

                if state:
                    if is_post_add:
                        state.increment_fields(by=len(pk_set))
                    elif is_post_remove:
                        state.decrement_fields(by=len(pk_set))
                    elif is_post_clear:
                        state.zero_fields()

                    if not pk_set and is_post_clear:
                        # See the note below for 'pre_clear' for an explanation
                        # of why we're doing this.
                        pk_set = state.to_clear
                        state.to_clear = set()

                if pk_set:
                    # If any of the models have their own
                    # RelationCounterFields, make sure they've been updated to
                    # handle this side of things.
                    if is_post_add:
                        update_by = 1
                    else:
                        update_by = -1

                    # Update all RelationCounterFields on the other side of the
                    # relation that are referencing this relation.
                    self._update_counts(model, pk_set, '_related_name',
                                        update_by)

                    for pk in pk_set:
                        state = RelationCounterField._get_state(
                            model, pk, self._related_name)

                        if state:
                            state.reload_fields()
            elif action == 'pre_clear':
                # m2m_changed doesn't provide any information on affected IDs
                # for clear events (pre or post). We can, however, look up
                # these IDs ourselves, and if they match any existing
                # instances, we can re-initialize their counters in post_clear
                # above.
                #
                # We do this by fetching the IDs (without instantiating new
                # models) and storing it in the associated InstanceState. We'll
                # use those IDs above in the post_clear handler.
                state = RelationCounterField._get_state(
                    instance.__class__, instance.pk, self._rel_field_name)

                if state:
                    mgr = getattr(instance, self._rel_field_name)
                    state.to_clear.update(mgr.values_list('pk', flat=True))

        def _on_related_delete(self, instance, **kwargs):
            """Handler for when a ForeignKey relation is deleted.

            This will check if a model entry that has a ForeignKey relation
            to this field's parent model entry has been deleted from the
            database. If so, any associated counter fields on this end will be
            decremented.
            """
            state = self._get_reverse_foreign_key_state(instance)

            if state:
                state.decrement_fields()
            else:
                self._update_unloaded_fkey_rel_counts(instance, -1)

        def _on_related_save(self, instance=None, created=False, raw=False,
                             **kwargs):
            """Handler for when a ForeignKey relation is created.

            This will check if a model entry has been created that has a
            ForeignKey relation to this field's parent model entry. If so, any
            associated counter fields on this end will be decremented.
            """
            if raw or not created:
                return

            state = self._get_reverse_foreign_key_state(instance)

            if state:
                state.increment_fields()
            else:
                self._update_unloaded_fkey_rel_counts(instance, 1)

        def _update_unloaded_fkey_rel_counts(self, instance, by):
            """Updates unloaded model entry counters for a ForeignKey relation.

            This will get the ID of the model being referenced by the
            matching ForeignKey in the provided instance. If set, it will
            update all RelationCounterFields on that model that are tracking
            the ForeignKey.
            """
            rel_pk = getattr(instance, self._rel_field.field.attname)

            if rel_pk is not None:
                self._update_counts(
                    self._get_rel_field_parent_model(self._rel_field),
                    [rel_pk], '_rel_field_name', by)

        def _update_counts(self, model_cls, pks, rel_attname, update_by):
            """Updates counts on all model entries matching the given criteria.

            This will update counts on all RelationCounterFields on all entries
            of the given model in the database that are tracking the given
            relation.
            """
            values = dict([
                (field.attname, F(field.attname) + update_by)
                for field in model_cls._meta.local_fields
                if (isinstance(field, RelationCounterField) and
                    (getattr(field._relation_tracker, rel_attname) ==
                        self._rel_field_name))
            ])

            if values:
                if len(pks) == 1:
                    q = Q(pk=list(pks)[0])
                else:
                    q = Q(pk__in=pks)

                model_cls.objects.filter(q).update(**values)

        def _get_reverse_foreign_key_state(self, instance):
            """Return an InstanceState for the other end of a ForeignKey.

            This is used when listening to changes on models that establish a
            ForeignKey to this counter field's parent model. Given the instance
            on that end, we can get the state for this end.
            """
            return RelationCounterField._get_state(
                self._get_rel_field_parent_model(self._rel_field),
                getattr(instance, self._rel_field.field.attname),
                self._rel_field_name)

        def _get_rel_field_parent_model(self, rel_field):
            """Return the model owning a relation field.

            This provides compatibility across different versions of Django.
            """
            if hasattr(rel_field, 'parent_model'):
                # Django < 1.7
                return rel_field.parent_model
            else:
                # Django >= 1.7
                return rel_field.model

        def _get_rel_field_related_model(self, rel_field):
            """Return the model on the other side of a relation field.

            This provides compatibility across different versions of Django.
            """
            if hasattr(rel_field, 'related_model'):
                # Django >= 1.7
                return rel_field.related_model
            else:
                # Django < 1.7
                return rel_field.model

    @classmethod
    def _reset_state(cls, instance_cls, instance_pk, instance_id):
        """Reset state for an instance.

        This will clear away any state tied to a destroyed instance, an
        instance with a given reference ID, or an instance with a given class
        and database ID. It's used to ensure that any old, removed entries
        (say, from a previous unit test, or when transitioning from an unsaved
        instance to saved) are cleared away before storing new state.

        Args:
            instance_cls (type):
                The model class of the instance being removed.

            instance_pk (int):
                The database ID of the instance (if known and if saved).

            instance_id (int):
                The reference ID of the instance.
        """
        for states in (cls._saved_instance_states,
                       cls._unsaved_instance_states):
            for key, state in list(six.iteritems(states)):
                model_instance = state.model_instance

                if (model_instance is None or
                    id(model_instance) == instance_id or
                    (model_instance.__class__ is instance_cls and
                     model_instance.pk == instance_pk)):
                    del states[key]

    @classmethod
    def _store_state(cls, instance, field):
        """Store state for a model instance and field.

        This constructs an :py:class:`InstanceState` instance for the given
        model instance and :py:class:`RelationCounterField`. It then associates
        it with the model instance and stores it.

        If the instance has not yet been saved, the constructed state will be
        tied to the instance and stored in :py:attr:`_unsaved_instance_states`.
        If the instance has been saved, the constructed state will be tied to
        a combination of the instance and field relation name and stoerd in
        :py:attr:`_saved_instance_states`.

        Saved instances will have a :samp:`_{fieldname}_state` attribute stored
        that points to the :py:class:`InstanceState`, keeping the state's
        reference alive as long as the instance is alive.
        """
        if instance.pk is None:
            states = cls._unsaved_instance_states
            key = id(instance)
        else:
            states = cls._saved_instance_states
            key = (instance.__class__, instance.pk, field._rel_field_name)

        try:
            state = states[key]
            state.fields.append(field)
        except KeyError:
            state = cls.InstanceState(instance, [field])
            states[key] = state

        if instance.pk is not None:
            setattr(instance, '_%s_state' % field.attname, state)

    @classmethod
    def _get_state(cls, model_cls, instance_pk, rel_field_name):
        """Return a saved InstanceState instance for the given parameters.

        This only considers state for saved instances, as those are the only
        ones we want to consider for relation tracking updates.

        Args:
            model_cls (type):
                The model class of the instance being removed.

            instance_pk (int):
                The database ID of the instance.

            rel_field_name (unicode):
                The name of the field relationship associated with the
                instance.

        Returns:
            InstanceState:
            The instance state, or ``None`` if not found.
        """
        return cls._saved_instance_states.get(
            (model_cls, instance_pk, rel_field_name))

    def __init__(self, rel_field_name=None, *args, **kwargs):
        def _initializer(model_instance):
            if model_instance.pk:
                return getattr(model_instance, rel_field_name).count()
            else:
                return 0

        kwargs['initializer'] = _initializer

        super(RelationCounterField, self).__init__(*args, **kwargs)

        self._rel_field_name = rel_field_name
        self._relation_tracker = None

    def _do_post_init(self, instance):
        """Handle initialization of an instance of the parent model.

        This will begin the process of storing state about the model
        instance and listening to signals coming from the model on the
        other end of the relation.

        Args:
            instance (django.db.models.Model):
                The model instance being initialized.
        """
        super(RelationCounterField, self)._do_post_init(instance)

        RelationCounterField._store_state(instance, self)

        if not self._relation_tracker:
            instance_cls = instance.__class__
            key = (instance_cls, self._rel_field_name)
            self._relation_tracker = \
                RelationCounterField._relation_trackers.get(key)

            if not self._relation_tracker:
                self._relation_tracker = \
                    self.RelationTracker(instance_cls, self._rel_field_name)
                RelationCounterField._relation_trackers[key] = \
                    self._relation_tracker
