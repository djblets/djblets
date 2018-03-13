from __future__ import unicode_literals

import threading
import weakref

import django
from django.db.models import F, Q
from django.db.models.signals import (m2m_changed, post_delete, post_save,
                                      pre_delete)
from django.utils import six

from djblets.db.fields.counter_field import CounterField


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

        def setup(self, model_instance):
            """Set up the state.

            Args:
                model_instance (django.db.models.Model):
                    The model instance that this state tracks.
            """
            self.fields = set()
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

        def increment_fields(self, by=1):
            """Increment all associated fields' counters.

            Args:
                by (int):
                    The value to increment by.
            """
            model_instance = self.model_instance

            if model_instance is not None:
                RelationCounterField.increment_many(
                    model_instance,
                    dict((field.attname, by) for field in self.fields))

        def decrement_fields(self, by=1):
            """Decrement all associated fields' counters.

            Args:
                by (int):
                    The value to decrement by.
            """
            model_instance = self.model_instance

            if model_instance is not None:
                RelationCounterField.decrement_many(
                    model_instance,
                    dict((field.attname, by) for field in self.fields))

        def zero_fields(self):
            """Zero out all associated fields' counters."""
            model_instance = self.model_instance

            if model_instance is not None:
                RelationCounterField._set_values(
                    model_instance,
                    dict((field.attname, 0) for field in self.fields))

        def reload_fields(self):
            """Reload all associated fields' counters."""
            model_instance = self.model_instance

            if model_instance is not None:
                RelationCounterField._reload_model_instance(
                    model_instance,
                    [field.attname for field in self.fields])

        def __repr__(self):
            """Return a string representation of the instance state.

            Returns:
                unicode:
                A string representation listing the instance information.
            """
            model_instance = self.model_instance

            if model_instance is not None:
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
            model_instance = self.model_instance

            if model_instance is None or instance is not model_instance:
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
            try:
                RelationCounterField._reset_state(
                    instance_cls=self.model_cls,
                    instance_pk=None,
                    instance_id=self.model_instance_id)
            except AttributeError:
                # Ignore any attribute errors when this fails. It is most
                # likely occurring while a thread/process is shutting down,
                # and some state no longer exists. We've seen this manifest
                # as two separate AttributeErrors so far.
                pass

        def _on_instance_pre_delete(self, instance, **kwargs):
            """Handler for when an instance is about to be deleted.

            This will reset the state of the instance, unregistering it from
            lists, and removing any pending signal connections.

            Args:
                instance (django.db.models.Model):
                    The instance being deleted.
            """
            model_instance = self.model_instance

            if model_instance is not None and instance is model_instance:
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
                states = RelationCounterField._get_saved_states(
                    instance.__class__, instance.pk, self._rel_field_name)

                if states:
                    main_state, other_states = \
                        self._separate_saved_states(states)

                    # Perform the database modifications with only the first
                    # instance state. The rest will get reloaded later.
                    if pk_set and is_post_add:
                        main_state.increment_fields(by=len(pk_set))
                    elif pk_set and is_post_remove:
                        main_state.decrement_fields(by=len(pk_set))
                    elif is_post_clear:
                        main_state.zero_fields()

                    if not pk_set and is_post_clear:
                        # See the note below for 'pre_clear' for an explanation
                        # of why we're doing this.
                        pk_set = main_state.to_clear
                        main_state.to_clear = set()

                    self._sync_fields_from_main_state(main_state, other_states)

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

                        if not states:
                            continue

                        main_state, other_states = \
                            self._separate_saved_states(states)

                        main_state.reload_fields()
                        self._sync_fields_from_main_state(main_state,
                                                          other_states)
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
                    main_state = next(six.itervalues(states))
                    mgr = getattr(instance, self._rel_field_name)
                    main_state.to_clear.update(mgr.values_list('pk',
                                                               flat=True))

        def _on_related_delete(self, instance, **kwargs):
            """Handler for when a ForeignKey relation is deleted.

            This will check if a model entry that has a ForeignKey relation
            to this field's parent model entry has been deleted from the
            database. If so, any associated counter fields on this end will be
            decremented.
            """
            states = self._get_reverse_foreign_key_states(instance)

            if states:
                main_state, other_states = self._separate_saved_states(states)
                main_state.decrement_fields()
                self._sync_fields_from_main_state(main_state, other_states)
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
                main_state, other_states = self._separate_saved_states(states)
                main_state.increment_fields()
                self._sync_fields_from_main_state(main_state, other_states)
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

        def _separate_saved_states(self, saved_states):
            """Return a main state separated from other states.

            This takes a dictionary of saved instance states, filters it for
            those containing non-dropped model instances, and picks one as
            a "main" state to perform operations on, separating it out from
            the other states.

            Args:
                saved_states (weakref.WeakValueDictionary):
                    The dictionary of saved states.

            Returns:
                tuple:
                A tuple of ``(main_state, [state, state, ...])``.
            """
            with RelationCounterField._state_lock:
                states = (
                    state
                    for state in six.itervalues(saved_states)
                    if state.model_instance is not None
                )

                return (next(states), list(states))

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
                        for field in other_state.fields:
                            setattr(other_instance, field.attname,
                                    getattr(main_instance, field.attname))
            else:
                # The instance fell out of scope. We'll have to just reload
                # all the other instances. This should be rare.
                for other_state in other_states:
                    other_state.reload_fields()

        def _get_reverse_foreign_key_states(self, instance):
            """Return InstanceStates for the other end of a ForeignKey.

            This is used when listening to changes on models that establish a
            ForeignKey to this counter field's parent model. Given the instance
            on that end, we can get the state for this end.

            Args:
                instance (django.db.model.Model):
                    The instance on the other end of the relation.

            Returns:
                weakref.WeakValueDictionary:
                The dictionary of :py:class:`InstanceState`s for each instance
                on this end of the relation.
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
        with cls._state_lock:
            for states in ([cls._unsaved_instance_states] +
                           list(six.itervalues(cls._saved_instance_states))):
                to_remove = []

                for key, state in six.iteritems(states):
                    model_instance = state.model_instance

                    if (model_instance is None or
                        id(model_instance) == instance_id or
                        (model_instance.__class__ is instance_cls and
                         model_instance.pk == instance_pk)):
                        to_remove.append(key)

                for key in to_remove:
                    states.pop(key, None)

            for key in list(six.iterkeys(cls._saved_instance_states)):
                if not cls._saved_instance_states[key]:
                    del cls._saved_instance_states[key]

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
        with cls._state_lock:
            if instance.pk is None:
                states = cls._unsaved_instance_states
            else:
                states = cls._saved_instance_states
                key = (instance.__class__, instance.pk, field._rel_field_name)

                try:
                    states = cls._saved_instance_states[key]
                except KeyError:
                    states = weakref.WeakValueDictionary()
                    cls._saved_instance_states[key] = states

            key = id(instance)

            try:
                state = states[key]
                state_is_new = False
            except KeyError:
                state = cls.InstanceState()
                state_is_new = True
                states[key] = state

            if instance.pk is not None:
                setattr(instance, '_%s_state' % field.attname, state)

        if state_is_new:
            state.setup(instance)

        state.fields.add(field)

    @classmethod
    def _get_saved_states(cls, model_cls, instance_pk, rel_field_name):
        """Return a dictionary of instances states for the given parameters.

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
            dict:
            The resulting dictionary of instances. If populated, this will
            be a :py:class:`weakref.WeakValueDictionary`.
        """
        return cls._saved_instance_states.get(
            (model_cls, instance_pk, rel_field_name), {})

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

            try:
                self._relation_tracker = \
                    RelationCounterField._relation_trackers[key]
            except KeyError:
                self._relation_tracker = \
                    self.RelationTracker(instance_cls, self._rel_field_name)
                RelationCounterField._relation_trackers[key] = \
                    self._relation_tracker
