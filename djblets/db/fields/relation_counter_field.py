from __future__ import unicode_literals

import threading
import weakref
from contextlib import contextmanager

import django
from django.db.models import F, Q
from django.db.models.signals import (m2m_changed, post_delete, post_save,
                                      pre_delete)
from django.utils import six

from djblets.db.fields.counter_field import CounterField


class InstanceState(weakref.ref):
    """Tracks state for a RelationCounterField instance assocation.

    State instances are bound to the lifecycle of a model instance.
    They're a type of weak reference for model instances that contain
    additional state needed for the tracking and update process.

    These are used for looking up the proper instance and
    RelationCounterFields on the other end of a reverse relation, given
    a model, relation name, and IDs, through the
    :py:attr:`RelationCounterField._saved_instance_states` or
    :py:attr:`RelationCounterField._unsaved_instance_states` or
    dictionaries.

    Instance states can either represent saved instances or unsaved
    instances. Unsaved instance states represent instances that haven't yet
    been saved to the database (with a primary key of ``None``). While saved
    instance states exist per-instance/relation name, there's only one
    unsaved instance state per instance.

    Once an unsaved instance is saved, new instance states will be stored
    for each field associated (which many turn into multiple states, as
    there's one per relation name). The old unsaved instance state is then
    discarded.
    """

    def __init__(self, model_instance):
        """Set up the state.

        Args:
            model_instance (django.db.models.Model):
                The model instance that this state tracks.
        """
        super(InstanceState, self).__init__(model_instance)

        self.to_clear = set()
        self.field_names = set()
        self._model_cls = type(model_instance)

    @property
    def model_instance(self):
        """The model instance being tracked.

        This will be ``None`` if the instance has been destroyed.
        """
        return self()

    def track_field(self, field):
        """Track information on a field referencing this state.

        Args:
            field (django.db.models.Field):
                The field to track.
        """
        self.field_names.add(field.attname)

    def __repr__(self):
        """Return a string representation of the instance state.

        Returns:
            unicode:
            A string representation listing the instance information.
        """
        model_instance = self.model_instance

        if model_instance is not None:
            return '<InstanceState for %s.pk=%s>' % (
                model_instance.__class__.__name__,
                model_instance.pk)
        else:
            return '<InstanceState for %r (destroyed)>' % self.model_cls


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
                # This is a ManyToManyField, and we can get the 'remote_field'
                # or 'rel' attribute (depending on Django version) through it
                # below.
                m2m_field = self._rel_field
            else:
                # This is a RelatedObject. We need to get the field through
                # this.
                m2m_field = self._rel_field.field

            if hasattr(m2m_field, 'remote_field'):
                # Django >= 1.7
                remote_field = m2m_field.remote_field
            else:
                remote_field = m2m_field.rel

            if is_rel_direct:
                self._related_name = remote_field.related_name
            else:
                self._related_name = m2m_field.attname

            # Listen for all M2M updates on the through table for this
            # ManyToManyField. Unfortunately, we can't look at a
            # particular instance, but we'll use state tracking to do the
            # necessary lookups and updates in the handler.
            m2m_changed.connect(
                self._on_m2m_changed,
                weak=False,
                sender=remote_field.through,
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

    def _increment_fields(self, states, by=1):
        """Increment all associated fields' counters on instance states.

        Args:
            states (list of InstanceState):
                The instance states containing the model instance fields to
                increment.

            by (int, optional):
                The value to increment by.
        """
        with self._update_sync_fields(states) as (model_instance, field_names):
            RelationCounterField.increment_many(
                model_instance,
                {
                    field_name: by
                    for field_name in field_names
                })

    def _decrement_fields(self, states, by=1):
        """Decrement all associated fields' counters on instance states.

        Args:
            states (list of InstanceState):
                The instance states containing the model instance fields to
                decrement.

            by (int, optional):
                The value to decrement by.
        """
        with self._update_sync_fields(states) as (model_instance, field_names):
            RelationCounterField.decrement_many(
                model_instance,
                {
                    field_name: by
                    for field_name in field_names
                })

    def _zero_fields(self, states):
        """Zero out all associated fields' counters on instance states.

        Args:
            states (list of InstanceState):
                The instance states containing the model instance fields to
                zero out.
        """
        with self._update_sync_fields(states) as (model_instance, field_names):
            RelationCounterField._set_values(
                model_instance,
                {
                    field_name: 0
                    for field_name in field_names
                })

    def _reload_fields(self, states):
        """Reload all associated fields' counters on instance states.

        Args:
            states (list of InstanceState):
                The instance states containing the model instance fields to
                reload.
        """
        with self._update_sync_fields(states) as (model_instance, field_names):
            RelationCounterField._reload_model_instance(model_instance,
                                                        field_names)

    @contextmanager
    def _update_sync_fields(self, states):
        """Update field values and synchronize them to other model instances.

        This calculates a main state from the list of instance states,
        gathering the model instance and field names and yielding them as
        context to the calling method. After that method makes the field
        changes needed, this will synchronize those values to all other model
        instances from the other states passed.

        Args:
            states (list of InstanceState):
                The list of states to update.

        Yields:
            tuple of (InstanceState, list of unicode):
            The main model instance to work on, and the list of field names
            to update.
        """
        main_state = states[0]
        model_instance = main_state.model_instance

        if model_instance is not None:
            yield model_instance, main_state.field_names

            if len(states) > 1:
                self._sync_fields_from_main_state(main_state, states[1:])

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
            states = RelationCounterField._get_saved_states(
                type(instance), instance.pk, self._rel_field_name)

            if states:
                # Perform the database modifications with only the first
                # instance state. The rest will get reloaded later.
                if pk_set and is_post_add:
                    self._increment_fields(states, by=len(pk_set))
                elif pk_set and is_post_remove:
                    self._decrement_fields(states, by=len(pk_set))
                elif is_post_clear:
                    self._zero_fields(states)

                if not pk_set and is_post_clear:
                    # See the note below for 'pre_clear' for an explanation
                    # of why we're doing this.
                    main_state = states[0]
                    pk_set = main_state.to_clear
                    main_state.to_clear = set()

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
                    states = RelationCounterField._get_saved_states(
                        model, pk, self._related_name)

                    if states:
                        self._reload_fields(states)
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
            states = RelationCounterField._get_saved_states(
                instance.__class__, instance.pk, self._rel_field_name)

            if states:
                main_state = states[0]
                mgr = getattr(instance, self._rel_field_name)
                main_state.to_clear.update(mgr.values_list('pk', flat=True))

    def _on_related_delete(self, instance, **kwargs):
        """Handler for when a ForeignKey relation is deleted.

        This will check if a model entry that has a ForeignKey relation
        to this field's parent model entry has been deleted from the
        database. If so, any associated counter fields on this end will be
        decremented.
        """
        states = self._get_reverse_foreign_key_states(instance)

        if states:
            self._decrement_fields(states)
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

        states = self._get_reverse_foreign_key_states(instance)

        if states:
            self._increment_fields(states)
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
        values = dict(
            (field.attname, F(field.attname) + update_by)
            for field in model_cls._meta.local_fields
            if (isinstance(field, RelationCounterField) and
                (getattr(field._relation_tracker, rel_attname) ==
                    self._rel_field_name))
        )

        if values:
            if len(pks) == 1:
                q = Q(pk=list(pks)[0])
            else:
                q = Q(pk__in=pks)

            model_cls.objects.filter(q).update(**values)

    def _sync_fields_from_main_state(self, main_state, other_states):
        """Synchronize field values across instances.

        This will take a main instance containing up-to-date values and
        synchronize those values to all other instances.

        Args:
            main_state (InstanceState):
                The main state to take values from.

            other_states (list of InstanceState):
                The other states to synchronize values to.
        """
        main_instance = main_state.model_instance

        if main_instance is not None:
            for other_state in other_states:
                other_instance = other_state.model_instance

                if other_instance is not None:
                    for field_name in other_state.field_names:
                        setattr(other_instance, field_name,
                                getattr(main_instance, field_name))
        else:
            # The instance fell out of scope. We'll have to just reload
            # all the other instances. This should be rare.
            for other_state in other_states:
                self._reload_fields(other_state)

    def _get_reverse_foreign_key_states(self, instance):
        """Return InstanceStates for the other end of a ForeignKey.

        This is used when listening to changes on models that establish a
        ForeignKey to this counter field's parent model. Given the instance
        on that end, we can get the state for this end.

        Args:
            instance (django.db.model.Model):
                The instance on the other end of the relation.

        Returns:
            list of InstanceState:
            The list of :py:class:`InstanceState`s for each instance on this
            end of the relation.
        """
        return RelationCounterField._get_saved_states(
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
    # relation, meaning we have to do it ourselves. This dictionary is keyed
    # off a tuple of (model_class, instance_pk, field_name) and maps to a
    # weakref.WeakValueDictionary mapping object IDs for model instances to
    # InstanceState objects (which are tied to the lifecycle of a particular
    # model instancee). These objects are used to look up model instances and
    # their RelationCounterFields.
    _saved_instance_states = {}

    # Stores instance states we're tracking whose instances haven't yet been
    # saved.
    #
    # An unsaved instance may never be saved, but we still need to listen to
    # events on it. To do this, we set up an InstanceState, like above,
    # keeping track of the information and signal connections related to it.
    # Unlike the above, there's only one level to this dictionary. It maps
    # object IDs to InstanceState objects.
    _unsaved_instance_states = {}

    # Most of the hard work really lives in RelationTracker below. Here, we
    # store all registered instances of RelationTracker. There will be one
    # per model_cls/relation_name pair.
    _relation_trackers = {}

    # A lock for handling instance state dictionary modification, to prevent
    # threads from stomping over each other.
    #
    # We use a reentrant lock here so that state updates that end up freeing
    # an InstanceState and then need a new lock during state resets won't
    # end up blocking.
    _state_lock = threading.RLock()

    # Flag for determining if global signal handlers need to be set up.
    _signals_setup = False

    @classmethod
    def has_tracked_states(cls):
        """Return whether there are currently any states being tracked.

        This will begin by cleaning up any expired states whose instances
        have been destroyed, if there are any. Then it will check if there
        are any remaining states still being tracked and return a result.

        Returns:
            bool:
            ``True`` if there are any states still being tracked.
            ``False`` if not.
        """
        cls._cleanup_state()

        return (bool(cls._saved_instance_states) or
                bool(cls._unsaved_instance_states))

    @classmethod
    def _cleanup_state(cls, instance_cls=None, instance_pk=None,
                       instance_id=None):
        """Clean up state for one or more instances.

        This will clear away any state tied to a destroyed instance, an
        instance with a given reference ID, or an instance with a given class
        and database ID. It's used to ensure that any old, removed entries
        (say, from a previous unit test, or when transitioning from an unsaved
        instance to saved) are cleared away before storing new state.

        Args:
            instance_cls (type, optional):
                The model class of the instance being removed.

            instance_pk (int, optional):
                The database ID of the instance (if known and if saved).

            instance_id (int, optional):
                The reference ID of the instance.
        """
        with cls._state_lock:
            cls._cleanup_state_for_dict(cls._unsaved_instance_states,
                                        instance_cls=instance_cls,
                                        instance_pk=instance_pk,
                                        instance_id=instance_id)

            # The saved instances dictionary is a dictionary full of
            # dictionaries, so we'll want to iterate through and see if
            # there's any keys in the outer dictionary that we need to
            # remove by the end.
            to_remove = []

            for key, states in six.iteritems(cls._saved_instance_states):
                cls._cleanup_state_for_dict(states,
                                            instance_cls=instance_cls,
                                            instance_pk=instance_pk,
                                            instance_id=instance_id)

                if not states:
                    # The states dictionary is now empty. Schedule it for
                    # removal.
                    to_remove.append(key)

            for key in to_remove:
                cls._saved_instance_states.pop(key, None)

    @classmethod
    def _cleanup_state_for_dict(cls, states, instance_cls, instance_pk,
                                instance_id):
        """Clean up state in a states dictionary.

        This is a utility function used by :py:meth:`_cleanup_state` for
        clearing out any state entries matching the given instance information
        or for those states that are no longer active.

        Args:
            states (list of InstanceState):
                The list of instance states to clean up.

            instance_cls (type, optional):
                The model class of the instance being removed.

            instance_pk (int, optional):
                The database ID of the instance (if known and if saved).

            instance_id (int, optional):
                The reference ID of the instance.
        """
        to_remove = []

        for key, state in six.iteritems(states):
            model_instance = state.model_instance

            if (model_instance is None or
                id(model_instance) == instance_id or
                (type(model_instance) is instance_cls and
                 model_instance.pk == instance_pk)):
                to_remove.append(key)

        for key in to_remove:
            states.pop(key, None)

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
        cls._cleanup_state()

        with cls._state_lock:
            if instance.pk is None:
                states = cls._unsaved_instance_states
            else:
                main_key = (type(instance), instance.pk, field._rel_field_name)
                states = cls._saved_instance_states.setdefault(main_key, {})

            key = id(instance)

            try:
                state = states[key]
            except KeyError:
                state = InstanceState(instance)
                states[key] = state

            state.track_field(field)

            # Mark that this instance tracks RelationCounterField states,
            # so our signal handlers have something they can easily look for.
            instance._tracks_relcounterfield_states = True

            if instance.pk is not None:
                # Attach the state to the field. This, along with being stored
                # in a WeakValueDictionary above, ensures that, so long as the
                # field remains in memory, the state will remain as well, and
                # that the state will be removed once the field instance
                # disappears (which will happen when the model instance
                # disappears).
                #
                # There should never be more than one state attached for a
                # field, since store_state() is only called once per model
                # instance per field, and field names are unique.
                setattr(instance, '_%s_instance_state' % field.attname, state)

    @classmethod
    def _get_saved_states(cls, model_cls, instance_pk, rel_field_name):
        """Return instance states for the given parameters.

        The returned dictionary will contain a mapping of object IDs for
        each instance to the :py:class:`InstanceState` for each saved instance
        matching the model class, primary key, and field name.

        Args:
            model_cls (type):
                The model class of the instances to look up.

            instance_pk (int):
                The database ID of the instances to look up.

            rel_field_name (unicode):
                The name of the field relationship associated with the
                instances.

        Returns:
            list of InstanceState:
            A list of all alive instance states for the given criteria. The
            first is considered the "main" state for an operation.

            If no suitable instances are found, this will return ``None``.
        """
        key = (model_cls, instance_pk, rel_field_name)

        with cls._state_lock:
            states = cls._saved_instance_states.get(key)

            if states is not None:
                return [
                    state
                    for state in six.itervalues(states)
                    if state.model_instance is not None
                ]

        return None

    @classmethod
    def _on_instance_first_save(cls, instance=None, created=False, **kwargs):
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

        Returns:
            bool:
            ``True`` if this instance was handled. ``False`` if it was ignored.
        """
        if (instance is None or
            not instance.pk or
            not created or
            not getattr(instance, '_tracks_relcounterfield_states', False)):
            # This isn't an instance we're tracking. Ignore it.
            return False

        instance_id = id(instance)

        try:
            state = cls._unsaved_instance_states[instance_id]
        except KeyError:
            # This isn't a tracked unsaved instance. We can skip it.
            return

        model_instance = state.model_instance

        if model_instance is None:
            # The references dropped. We're no longer working with this state.
            return False

        assert instance is model_instance

        with cls._state_lock:
            # Remove the old state information from the dictionary. We could
            # do this with a .pop(key, None) above, but we don't want to lock
            # unnecessarily.
            #
            # Even though we just fetched it, we can't assume that the data
            # is still there, since another thread could have done something
            # with it, so we can't do a plain del().
            cls._unsaved_instance_states.pop(instance_id, None)

        # Now we can register each RelationCounterField on here.
        for field in type(instance)._meta.local_fields:
            if isinstance(field, cls):
                cls._store_state(instance, field)

        return True

    @classmethod
    def _on_instance_pre_delete(cls, instance=None, **kwargs):
        """Handler for when an instance is about to be deleted.

        This will reset the state of the instance, unregistering it from
        lists, and removing any pending signal connections.

        Args:
            instance (django.db.models.Model):
                The instance being deleted.

            **kwargs (dict):
                Extra keyword arguments passed to the handler.

        Returns:
            bool:
            ``True`` if this instance was handled. ``False`` if it was ignored.
        """
        if (instance is None or
            not getattr(instance, '_tracks_relcounterfield_states', False)):
            # This isn't an instance we're tracking. Ignore it.
            return False

        instance_id = id(instance)
        assert instance_id not in cls._unsaved_instance_states

        cls._cleanup_state(instance_cls=type(instance),
                           instance_pk=instance.pk,
                           instance_id=instance_id)

        return True

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

        cls = type(self)

        # The first time we reach this, we want to let the class itself begin
        # listening for signals for instance saves and deletes.
        #
        # Note that, in theory, this could end up being called twice, but
        # that's ultimately okay, since we'll be using the same dispatch UID
        # on all signal connections, and the signals will ensure in a
        # thread-safe way that there's only one callback per dispatch UID.
        if not cls._signals_setup:
            dispatch_uid = '%s.%s' % (cls.__module__, cls.__name__)
            post_save.connect(cls._on_instance_first_save,
                              dispatch_uid=dispatch_uid)
            pre_delete.connect(cls._on_instance_pre_delete,
                               dispatch_uid=dispatch_uid)
            cls._signals_setup = True

        cls._store_state(instance, self)

        if not self._relation_tracker:
            instance_cls = type(instance)
            key = (instance_cls, self._rel_field_name)

            try:
                self._relation_tracker = cls._relation_trackers[key]
            except KeyError:
                self._relation_tracker = RelationTracker(instance_cls,
                                                         self._rel_field_name)
                cls._relation_trackers[key] = self._relation_tracker
