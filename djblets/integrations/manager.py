"""A manager for tracking and working with integrations."""

from __future__ import unicode_literals

import atexit
import logging
import threading
import weakref

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models.signals import post_delete, post_save
from django.utils import six

from djblets.cache.synchronizer import GenerationSynchronizer
from djblets.integrations.errors import (IntegrationAlreadyRegisteredError,
                                         IntegrationNotRegisteredError,
                                         IntegrationRegistrationError)


_integration_managers = weakref.WeakValueDictionary()


class IntegrationManager(object):
    """Manages integrations with third-party services.

    The manager keeps track of the integrations registered by extensions
    or other components of an application, providing the ability to
    register new ones, unregister existing ones, and list any that are
    currently enabled.

    It also manages the lookups of configurations for integrations, taking
    care to cache the lookups for any integrations and invalidate them when
    a configuration has been updated.

    Attributes:
        config_model (type):
            The model used to store configuration data. This is a subclass of
            :py:class:`djblets.integrations.models.BaseIntegrationConfig`.

        enabled (bool):
            The integration manager is enabled and can be used for registering,
            unregistering, and otherwise using integrations. If this is
            ``False``, then :py:meth:`shutdown` has been called, and it should
            be assumed that no integrations are registered or need to be
            unregistered.
    """

    def __init__(self, config_model):
        """Initialize the integration manager.

        Args:
            config_model (type):
                The model used to store configuration data. This must be a
                subclass of
                :py:class:`djblets.integrations.models.BaseIntegrationConfig`.
        """
        # Check that the Django environment is set up for integrations to
        # properly function.
        if 'djblets.integrations' not in settings.INSTALLED_APPS:
            raise ImproperlyConfigured(
                'IntegrationManager requires djblets.integrations to be '
                'listed in settings.INSTALLED_APPS.'
            )

        middleware = 'djblets.integrations.middleware.IntegrationsMiddleware'

        if middleware not in settings.MIDDLEWARE_CLASSES:
            raise ImproperlyConfigured(
                'IntegrationManager requires %s to be listed in '
                'settings.MIDDLEWARE_CLASSES'
                % middleware
            )

        self.config_model = config_model

        key = ('integrationmgr:%s.%s'
               % (self.__class__.__module__, self.__class__.__name__))

        self.enabled = True

        self._integration_classes = {}
        self._integration_configs = {}
        self._integration_instances = {}
        self._lock = threading.Lock()
        self._needs_recalc = False
        self._gen_sync = GenerationSynchronizer('%s:gen' % key)

        instance_id = id(self)
        _integration_managers[instance_id] = self

        # Listen for any config model saves/deletes, so we can mark whether
        # a reload of state is needed.
        dispatch_uid = '%s:%s' % (key, id(self))

        post_delete.connect(self._on_config_changes,
                            sender=config_model,
                            dispatch_uid=dispatch_uid)
        post_save.connect(self._on_config_changes,
                          sender=config_model,
                          dispatch_uid=dispatch_uid)

    def shutdown(self):
        """Shut down the integrations on this integration manager.

        This should be called when the integration manager and integrations
        will no longer be used. It will shut down every integration and
        unregister all integrations.
        """
        for integration in self.get_integrations():
            integration.disable_integration()

        self._integration_classes = {}
        self._integration_configs = {}
        self._integration_instances = {}
        self._needs_recalc = False

        try:
            del _integration_managers[id(self)]
        except KeyError:
            pass

        self.enabled = False

    def get_integration_classes(self):
        """Return all the integration classes that have been registered.

        This is not sorted in any particular order. It is up to the caller
        to determine the correct sorting order.

        Yields:
            type:
            The registered integration classes.
        """
        return six.itervalues(self._integration_classes)

    def get_integration(self, integration_id):
        """Return an integration instance for a given ID.

        Args:
            integration_id (unicode):
                The integration ID that was registered.

        Returns:
            djblets.integrations.integration.Integration:
            The integration instance.

        Raises:
            djblets.integrations.errors.IntegrationNotRegisteredError:
                The integration class provided wasn't registered.
        """
        try:
            return self._integration_instances[integration_id]
        except KeyError:
            raise IntegrationNotRegisteredError(integration_id)

    def get_integrations(self):
        """Return all the integration instances.

        This is not sorted in any particular order. It is up to the caller
        to determine the correct sorting order.

        Yields:
            djblets.integrations.integration.Integration:
            The integration instances.
        """
        return six.itervalues(self._integration_instances)

    def get_integration_configs(self, integration_cls=None, **filter_kwargs):
        """Return a list of saved integration configurations.

        By default, all configurations will be returned for all integrations,
        including configurations that are disabled. This can be filtered
        down by specifying an integration class and/or by filtering by fields
        in the model through keyword arguments.

        Each set of results for a unique combination of integration class and
        filter arguments will be cached locally, to speed up further lookups.
        This cache can be flushed using :py:meth:`clear_configs_cache` or
        :py:meth:`clear_all_configs_cache`, and will be automatically cleared
        when cnofigurations are added, updated, or removed.

        Args:
            integration_cls (type, optional):
                The integration class to filter by.

            **filter_kwargs (dict, optional):
                Keyword arguments to filter by. Each must match a field and
                value on the model.

        Returns:
            list of djblets.integrations.models.BaseIntegrationConfig:
            A list of saved integration configurations matching the query.
        """
        key = self._make_config_filter_cache_key(integration_cls,
                                                 **filter_kwargs)

        try:
            configs = self._integration_configs[key]
        except KeyError:
            queryset = self.config_model.objects.all()

            if integration_cls:
                queryset = queryset.filter(
                    integration_id=integration_cls.integration_id)

            if filter_kwargs:
                queryset = queryset.filter(**filter_kwargs)

            configs = list(queryset)
            self._integration_configs[key] = configs

        return configs

    def clear_configs_cache(self, integration_cls=None, **filter_kwargs):
        """Clear the configuration cache matching the given filters.

        This is used to clear a subset of the configs cache, matching the exact
        query arguments passed to a previous call to
        :py:meth:`get_integration_configs`.

        To clear the entire cache, use :py:meth:`clear_all_configs_cache`.

        Args:
            integration_cls (type, optional):
                The integration class for the filter.

            **filter_kwargs (dict, optional):
                Keyword arguments for the filter.
        """
        key = self._make_config_filter_cache_key(integration_cls,
                                                 **filter_kwargs)

        try:
            del self._integration_configs[key]
        except KeyError:
            pass

    def clear_all_configs_cache(self):
        """Clear the entire configuration cache.

        This will force all future lookups to re-query the database. To
        clear only a subset of the cache, use :py:meth:`clear_configs_cache`.
        """
        self._integration_configs = {}

    def is_expired(self):
        """Return whether the integration manager has expired state.

        Returns:
            bool:
            ``True`` if there's either expired configuration state or
            integrations that need their enabled state recalculated.
        """
        return self._needs_recalc or self._gen_sync.is_expired()

    def check_expired(self):
        """Check for and handle expired integration state.

        If the configurations of one or more integrations have been updated
        by another process, or there are new integrations registered that
        may need to be enabled, this method will reset the cache state and
        re-calculate the integrations to enable/disable.
        """
        if self.is_expired():
            # We're going to check the expiration, and then only lock if it's
            # expired. Following that, we'll check again.
            #
            # We do this in order to prevent locking unnecessarily, which could
            # impact performance or cause a problem if a thread is stuck.
            #
            # We're checking the expiration twice to prevent every blocked
            # thread from making its own attempt to reload the integrations
            # state the first thread holding the lock finishes.
            with self._lock:
                # Check again, since another thread may have already
                # reloaded.
                if self.is_expired():
                    self._gen_sync.refresh()
                    self.clear_all_configs_cache()
                    self._recalc_enabled_integrations()

    def register_integration_class(self, integration_cls):
        """Register a class for an integration.

        This will instantiate the integration and make it available for new
        configurations.

        Args:
            integration_cls (type):
                The integration class to register.

        Returns:
            djblets.integrations.integration.Integration:
            The new instance of the registered integration class.

        Raises:
            djblets.integrations.errors.IntegrationAlreadyRegisteredError:
                The integration class was already registered.

            djblets.integrations.errors.IntegrationConstructionError:
                Error initializing an instance of the integration. The
                integration will not be registered.
        """
        if not integration_cls.integration_id:
            # A pre-existing integration ID doesn't exist, so create one
            # based on the class path.
            integration_cls.integration_id = '%s.%s' % (
                integration_cls.__module__,
                integration_cls.__name__)

        integration_id = integration_cls.integration_id

        if integration_id in self._integration_classes:
            raise IntegrationAlreadyRegisteredError(integration_id)

        try:
            # We're going to instantiate the integration, but we won't
            # initialize it until later when we know that there are
            # configurations available.
            integration = integration_cls(self)
            self._integration_instances[integration_id] = integration
            self._integration_classes[integration_id] = integration_cls
        except Exception as e:
            # This should never happen, unless the subclass overrode
            # __init__.
            raise IntegrationRegistrationError(
                'Unexpected error when constructing integration %s: %s'
                % (integration_cls.__name__, e))

        # Flag that we need to recalculate the list of enabled integrations.
        # The next time a request is served, the middleware will perform the
        # recalculation. We do it this way instead of during registration in
        # order to cut back on the number of queries needed.
        self._needs_recalc = True

        return integration

    def unregister_integration_class(self, integration_cls):
        """Unregister a class for an integration.

        The integration instance will be shut down, and the integration will
        no longer be made available for any further configuration.

        If there is an error shutting down the integration, the output will
        be logged, but no error will be returned.

        Args:
            integration_cls (type):
                The integration class to unregister.

        Raises:
            djblets.integrations.errors.IntegrationNotRegisteredError:
                The integration class was not previously registered.
        """
        integration_id = integration_cls.integration_id

        if (not integration_id or
            integration_id not in self._integration_classes):
            raise IntegrationNotRegisteredError(integration_id)

        integration = self.get_integration(integration_id)

        if integration.enabled:
            try:
                integration.disable_integration()
            except Exception as e:
                logging.exception(
                    'Unexpected error when shutting down integration %r: %s',
                    integration_cls, e)

        del self._integration_classes[integration_id]
        del self._integration_instances[integration_id]

    def _recalc_enabled_integrations(self):
        """Recalculate the enabled states of all integrations.

        The list of enabled configurations for integrations will be queried
        from the database. Based on this, the desired enabled state of each
        integration will be calculated. Those that are disabled but have
        enabled configurations will be enabled, and those that are enabled
        but no longer have enabled configurations will be disabled.

        This allows us to keep memory requirements and event handling at a
        minimum for any integrations not currently in use.
        """
        enabled_integration_ids = set(
            self.config_model.objects
            .filter(enabled=True)
            .distinct()
            .values_list('integration_id', flat=True)
        )

        for integration in self.get_integrations():
            should_enable = (integration.integration_id in
                             enabled_integration_ids)

            if should_enable != integration.enabled:
                if should_enable:
                    integration.enable_integration()
                else:
                    integration.disable_integration()

        self._needs_recalc = False

    def _make_config_filter_cache_key(self, integration_cls, **filter_kwargs):
        """Return a cache key for a config query filter.

        Args:
            integration_cls (type):
                The integration class used for the query.

            **filter_kwargs (dict):
                The filter keyword arguments used for the query.

        Returns:
            unicode:
            The resulting cache key.
        """
        if integration_cls:
            return '%s:%s' % (integration_cls.integration_id, filter_kwargs)
        else:
            return '*:%s' % (filter_kwargs,)

    def _on_config_changes(self, **kwargs):
        """Handler for when configuration state changes.

        This will force the list of integrations to recalculate on this
        process and others when a configuration is created, saved, or deleted.

        Args:
            **kwargs (dict):
                Keyword arguments passed to the signal.
        """
        self._needs_recalc = True
        self._gen_sync.mark_updated()


def get_integration_managers():
    """Return all integration manager instances.


    This will return all the integration managers that have been constructed.
    The order is not guaranteed.

    Returns:
        list: The list of :py:class:`IntegrationManager` instances.
    """
    return list(six.itervalues(_integration_managers))


def shutdown_integration_managers():
    """Shut down all integration managers.

    This is called automatically when the process exits, but can be run
    manually.
    """
    # Make a copy of the list as we iterate, since the integration managers
    # will be removing themselves from the list.
    for integration_manager in list(get_integration_managers()):
        integration_manager.shutdown()


# When the process ends, shut down the integrations on each manager. That will
# help work around bugs in Django where it attempts to work with garbage state
# being held onto by extensions.
atexit.register(shutdown_integration_managers)
