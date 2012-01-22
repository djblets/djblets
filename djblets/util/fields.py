#
# fields.py -- Model fields.
#
# Copyright (c) 2007-2008  Christian Hammond
# Copyright (c) 2007-2008  David Trowbridge
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

import base64
import logging
from datetime import datetime

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models import F
from django.utils import simplejson
from django.utils.encoding import smart_unicode


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
        pk_set = pk_val is not None and smart_unicode(pk_val) != u''

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
            value = datetime.now()
            setattr(model, self.attname, value)
            return value

        return super(ModificationTimestampField, self).pre_save(model, add)

    def get_internal_type(self):
        return "DateTimeField"


class JSONField(models.TextField):
    """
    A field for storing JSON-encoded data. The data is accessible as standard
    Python data types and is transparently encoded/decoded to/from a JSON
    string in the database.
    """
    serialize_to_string = True

    def __init__(self, verbose_name=None, name=None,
                 encoder=DjangoJSONEncoder(), **kwargs):
        blank = kwargs.pop('blank', True)
        models.TextField.__init__(self, verbose_name, name, blank=blank,
                                  **kwargs)
        self.encoder = encoder

    def contribute_to_class(self, cls, name):
        def get_json(model_instance):
            return self.dumps(getattr(model_instance, self.attname, None))

        def set_json(model_instance, json):
            setattr(model_instance, self.attname, self.loads(json))

        super(JSONField, self).contribute_to_class(cls, name)

        setattr(cls, "get_%s_json" % self.name, get_json)
        setattr(cls, "set_%s_json" % self.name, set_json)

        models.signals.post_init.connect(self.post_init, sender=cls)

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
        if not isinstance(value, basestring):
            value = self.dumps(value)

        return super(JSONField, self).get_db_prep_save(value, *args, **kwargs)

    def value_to_string(self, obj):
        return self.dumps(self.value_from_object(obj))

    def dumps(self, data):
        return self.encoder.encode(data)

    def loads(self, val):
        try:
            val = simplejson.loads(val, encoding=settings.DEFAULT_CHARSET)

            # XXX We need to investigate why this is happening once we have
            #     a solid repro case.
            if isinstance(val, basestring):
                logging.warning("JSONField decode error. Expected dictionary, "
                                "got string for input '%s'" % val)
                # For whatever reason, we may have gotten back
                val = simplejson.loads(val, encoding=settings.DEFAULT_CHARSET)
        except ValueError:
            # There's probably embedded unicode markers (like u'foo') in the
            # string. We have to eval it.
            val = eval(val)

        return val


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
    as a parameter, and must return an integer.

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

    def increment(self, queryset):
        """Increments this field on every object in the provided queryset."""
        queryset.update(**{self.attname: F(self.attname) + 1})

    def decrement(self, queryset):
        """Decrements this field on every object in the provided queryset."""
        queryset.update(**{self.attname: F(self.attname) - 1})

    def contribute_to_class(self, cls, name):
        def _increment(model_instance, reload_object=True):
            """Increments this field by one."""
            self.increment(cls.objects.filter(pk=model_instance.pk))

            if reload_object:
                _reload(model_instance)

        def _decrement(model_instance, reload_object=True):
            """Decrements this field by one."""
            self.decrement(cls.objects.filter(pk=model_instance.pk))

            if reload_object:
                _reload(model_instance)

        def _reload(model_instance):
            """Reloads the value in this instance from the database."""
            q = cls.objects.filter(pk=model_instance.pk)
            setattr(model_instance, self.attname,
                    q.values(self.attname)[0][self.attname])

        def _reinit(model_instance):
            """Re-initializes the value in the database from the initializer."""
            if not model_instance.pk:
                # We don't want to end up defaulting this to 0 if creating a
                # new instance. Instead, we'll want to handle this the next
                # time the object is accessed.
                return

            if self._initializer and callable(self._initializer):
                self._locks[model_instance] = 1
                value = self._initializer(model_instance)
                del self._locks[model_instance]
            else:
                value = 0

            setattr(model_instance, self.attname, value)

            if model_instance.pk:
                model_instance.save()

        super(CounterField, self).contribute_to_class(cls, name)

        setattr(cls, 'increment_%s' % self.name, _increment)
        setattr(cls, 'decrement_%s' % self.name, _decrement)
        setattr(cls, 'reload_%s' % self.name, _reload)
        setattr(cls, 'reinit_%s' % self.name, _reinit)
        setattr(cls, self.attname, self)

        models.signals.post_init.connect(self._post_init, sender=cls)

    def _post_init(self, instance=None, **kwargs):
        if not instance or instance in self._locks:
            # Prevent the possibility of recursive lookups where this
            # same CounterField on this same instance tries to initialize
            # more than once. In this case, this will have the updated
            # value shortly.
            return

        value = self.value_from_object(instance)

        if value is None:
            reinit = getattr(instance, 'reinit_%s' % self.name)
            reinit()
