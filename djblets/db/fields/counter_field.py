"""Field for atomically incrementing and decrementing counters in models."""

from __future__ import unicode_literals

from django.db import models
from django.db.models import F
from django.db.models.signals import post_init
from django.utils import six

try:
    from django.db.models.expressions import Combinable as QueryExpressionType
except ImportError:
    from django.db.models.expressions import (ExpressionNode as
                                              QueryExpressionType)


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
    as a parameter, and must return an integer or ``None``. If it returns
    ``None``, the counter will not be updated or saved.

    The model instance will gain four new functions:

    :samp:`increment_{field_name}`
        Atomically increment the field by one.

    :samp:`decrement_{field_name}`
        Atomically decrement the field by one.

    :samp:`reload_{field_name}`
        Reload the value in this instance from the database.

    :samp:`reinit_{field_name}`
        Re-initializes the stored field using the initializer function.

    The field on the class (not the instance) provides two functions for
    batch-updating models:

    ``increment``
        Takes a queryset and increments this field for each object.

    ``decrement``
        Takes a queryset and decrements this field for each object.
    """

    @classmethod
    def increment_many(cls, model_instance, values, reload_object=True):
        """Increment several fields on a model instance at once.

        Args:
            model_instance (django.db.models.Model):
                The model instance containing the fields to increment.

            values (dict):
                A dictionary mapping field names to delta values to increment
                by.

            reload_object (bool, optional):
                Whether to reload the field values in ``model_instance`` to
                reflect the current values in the database after incrementing.
        """
        cls._update_values(model_instance, values, reload_object, multiplier=1)

    @classmethod
    def decrement_many(cls, model_instance, values, reload_object=True):
        """Decrement several fields on a model instance at once.

        Args:
            model_instance (django.db.models.Model):
                The model instance containing the fields to decrement.

            values (dict):
                A dictionary mapping field names to delta values to decrement
                by.

            reload_object (bool, optional):
                Whether to reload the field values in ``model_instance`` to
                reflect the current values in the database after decrementing.
        """
        cls._update_values(model_instance, values, reload_object,
                           multiplier=-1)

    @classmethod
    def _update_values(cls, model_instance, values, reload_object, multiplier):
        """Update several fields on a model instance at once.

        This does the hard work of updating fields for a model instance,
        updating existing values based on multiplying those provided with
        ``multiplier``.

        Args:
            model_instance (django.db.models.Model):
                The model instance containing the fields to update.

            values (dict):
                A dictionary mapping field names to delta values.

            reload_object (bool):
                Whether to reload the field values in ``model_instance`` to
                reflect the current values in the database after updating.

            multiplier (int):
                The value to multiply each of the provided values with.
        """
        cls._set_values(
            model_instance=model_instance,
            values={
                attname: F(attname) + value * multiplier
                for attname, value in six.iteritems(values)
                if value != 0
            },
            reload_object=reload_object)

    @classmethod
    def _set_values(cls, model_instance, values, reload_object=True):
        """Set values for several fields on a model instance at once.

        Args:
            model_instance (django.db.models.Model):
                The model instance containing the fields to update.

            values (dict):
                A dictionary mapping field names to values. Each value can be
                anything allowed in a model update, including a
                :py:class:`query expression <django.db.models.F>`.

            reload_object (bool):
                Whether to reload the field values in ``model_instance`` to
                reflect the current values in the database after updating.
        """
        if not values:
            return

        model_cls = type(model_instance)
        model_cls.objects.filter(pk=model_instance.pk).update(**values)

        if reload_object:
            cls._reload_model_instance(model_instance, six.iterkeys(values))

    @classmethod
    def _reload_model_instance(cls, model_instance, attnames):
        """Reload the value in this instance from the database.

        Args:
            model_instance (django.db.models.Model):
                The model instance containing fields to reload.

            attnames (list of str):
                The list of field attribute names to reload.
        """
        q = type(model_instance).objects.filter(pk=model_instance.pk)
        values = q.values(*attnames)[0]

        for attname, value in six.iteritems(values):
            setattr(model_instance, attname, value)

    def __init__(self, verbose_name=None, name=None,
                 initializer=None, default=None, **kwargs):
        """Initialize the field.

        This can take a default value for the counter, or an initializer
        function that can compute a value (based on database queries or
        anything else needed).

        Args:
            verbose_name (unicode, optional):
                The verbose name to show users in forms. This defaults to a
                variation of the field name.

            name (str, optional):
                The name of the field. This defaults to the attribute name
                on the model.

            initializer (callable, optional):
                A function to call to compute an initial value for the field
                if ``None`` or when re-initializing.

            default (int, optional):
                An explicit default value for the field.

            **kwargs (dict):
                Additional keyword arguments for the field.
        """
        kwargs.update({
            'blank': True,
            'null': True,
        })

        super(CounterField, self).__init__(verbose_name, name, default=default,
                                           **kwargs)

        self._initializer = initializer
        self._locks = {}

    def increment(self, queryset, increment_by=1):
        """Increment this field on every object in the provided queryset.

        By default, this increments by 1, but a custom delta value can be
        provided.

        Args:
            queryset (django.db.models.query.QuerySet):
                The queryset for the update.

            increment_by (int, optional):
                The value to increment by. Defaults to 1.
        """
        queryset.update(**{self.attname: F(self.attname) + increment_by})

    def decrement(self, queryset, decrement_by=1):
        """Decrement this field on every object in the provided queryset.

        By default, this increments by 1, but a custom delta value can be
        provided.

        Args:
            queryset (django.db.models.query.QuerySet):
                The queryset for the update.

            decrement_by (int, optional):
                The value to decrement by. Defaults to 1.
        """
        queryset.update(**{self.attname: F(self.attname) - decrement_by})

    def contribute_to_class(self, cls, name):
        """Add methods to the model class.

        This introduces the methods for incrementing, decrementing,
        reloading, and re-initializing the fields.

        Args:
            cls (type):
                The model class.

            name (str):
                The name of the field on the model.
        """
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
        setattr(cls, '_do_update', type(self)._model_do_update)

        post_init.connect(self._post_init, sender=cls)

    def _increment(self, model_instance, reload_object=True, increment_by=1):
        """Increment this field by a value.

        By default, this increments by 1.

        Args:
            model_instance (django.db.models.Model):
                The model instance containing the field to increment.

            reload_object (bool, optional):
                Whether to reload the field value after incrementing.

            increment_by (int, optional):
                The value to increment by. Defaults to 1.
        """
        if increment_by != 0:
            cls = type(model_instance)
            self.increment(cls.objects.filter(pk=model_instance.pk),
                           increment_by)

            if reload_object:
                self._reload(model_instance)

    def _decrement(self, model_instance, reload_object=True, decrement_by=1):
        """Decrement this field by one.

        By default, this decrements by 1.

        Args:
            model_instance (django.db.models.Model):
                The model instance containing the field to decrement.

            reload_object (bool, optional):
                Whether to reload the field value after decrementing.

            increment_by (int, optional):
                The value to decrement by. Defaults to 1.
        """
        if decrement_by != 0:
            cls = type(model_instance)
            self.decrement(cls.objects.filter(pk=model_instance.pk),
                           decrement_by)

            if reload_object:
                self._reload(model_instance)

    def _reload(self, model_instance):
        """Reload the value in this instance from the database.

        Args:
            model_instance (django.db.models.Model):
                The model instance containing the field to reload.
        """
        self._reload_model_instance(model_instance, [self.attname])

    def _reinit(self, model_instance):
        """Re-initialize the value in the database from the initializer.

        Args:
            model_instance (django.db.models.Model):
                The model instance containing the field to re-initialize.
        """
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

    def _post_init(self, instance, **kwargs):
        """Initialize the field when a model instance is created.

        This will begin the process of initializing the default value for
        the field. It checks to make sure there's not another initialization
        happening due to a second counter field on the same instance modifying
        the state.

        Args:
            instance (django.db.models.Model):
                The instance being initialized.

            **kwargs (dict):
                Extra keyword arguments for the signal handler.
        """
        # Prevent the possibility of recursive lookups where this
        # same CounterField on this same instance tries to initialize
        # more than once. In this case, this will have the updated
        # value shortly.
        if instance is not None:
            instance_id = id(instance)

            if instance_id not in self._locks:
                self._do_post_init(instance)

    def _do_post_init(self, instance):
        """Initialize the value for the field when a model instance is created.

        If a value doesn't already exist on the counter, and an initializer
        is provided, it will be called to set a new value for the counter.

        Args:
            instance (django.db.models.Model):
                The instance being initialized.
        """
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

        # We explicitly need to use ``models.Model._do_update`` here instead of
        # calling ``super(type(model), model)._do_update``.
        #
        # If ``type(model)`` defines a counter field **and** inherits from an
        # abstract model that does the same, then
        # ``super(type(model), model)._do_update`` is **this method**. We will
        # infinitely recurse and blow the stack in this case. Hence we have to
        # skip right to ``models.Model``.
        return models.Model._do_update(
            model, base_qs, using, pk_val, values, update_fields,
            forced_update)
