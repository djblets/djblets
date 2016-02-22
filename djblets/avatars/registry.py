"""A registry for managing avatar services."""

from __future__ import unicode_literals

import logging

from django.utils.translation import ugettext_lazy as _

from djblets.avatars.errors import (AvatarServiceNotFoundError,
                                    DisabledServiceError)
from djblets.avatars.services.gravatar import GravatarService
from djblets.registries.errors import ItemLookupError
from djblets.registries.registry import (ALREADY_REGISTERED,
                                         ATTRIBUTE_REGISTERED, DEFAULT_ERRORS,
                                         NOT_REGISTERED, Registry, UNREGISTER)
from djblets.siteconfig.models import SiteConfiguration


DISABLED_SERVICE_DEFAULT = 'disabled_service_default'
UNKNOWN_SERVICE_DEFAULT = 'unknown_service_default'
UNKNOWN_SERVICE_DISABLED = 'unknown_service_disabled'
UNKNOWN_SERVICE_ENABLED = 'unknown_service_enabled'


AVATAR_SERVICE_DEFAULT_ERRORS = DEFAULT_ERRORS.copy()
AVATAR_SERVICE_DEFAULT_ERRORS.update({
    ALREADY_REGISTERED: _(
        'Could not register avatar service %(item)s: This service is already '
        'registered.'
    ),
    ATTRIBUTE_REGISTERED: _(
        'Could not register avatar service %(attr_value)s: This service is '
        'already registered.'
    ),
    DISABLED_SERVICE_DEFAULT: _(
        'Could not set the default service to %(service_id)s: This service is '
        'disabled.'
    ),
    NOT_REGISTERED: _(
        'Could not unregister unknown avatar service %(attr_value)s: This '
        'service is not registered.'
    ),
    UNKNOWN_SERVICE_DEFAULT: _(
        'Could not set the default avatar service to %(service_id)s: This '
        'service is not registered.'
    ),
    UNKNOWN_SERVICE_DISABLED: _(
        'Could not disable unknown avatar service %(service_id)s: This '
        'service is not registered.'
    ),
    UNKNOWN_SERVICE_ENABLED: _(
        'Could not enable unknown avatar service %(service_id)s: This service '
        'is not registered.'
    ),
    UNREGISTER: _(
        'Could not unregister unknown avatar service %(item)s: This service '
        'is not registered.'
    ),
})


class AvatarServiceRegistry(Registry):
    """A registry for avatar services.

    This registry manages a set of avatar services (see
    :py:mod:`djblets.avatars.services.gravatar` for an example). The registries
    are saved to the database and require the use of the
    :py:mod:`djblets.siteconfig` app.
    """

    #: The key name for the list of enabled services.
    ENABLED_SERVICES_KEY = 'avatars_enabled_services'

    #: The key name for the default service.
    DEFAULT_SERVICE_KEY = 'avatars_default_service'

    lookup_attrs = ('avatar_service_id',)

    default_errors = AVATAR_SERVICE_DEFAULT_ERRORS

    lookup_error_class = AvatarServiceNotFoundError

    def __init__(self):
        """Initialize the avatar service registry."""
        super(AvatarServiceRegistry, self).__init__()

        self._enabled_services = set()
        self._default_service_id = None

    @property
    def enabled_services(self):
        """Return the enabled services.

        Returns:
            set:
            The set of enabled avatar services, as
            :py:class:`djblets.avatars.service.AvatarService` instances.
        """
        return {
            self.get('avatar_service_id', service_id)
            for service_id in self._enabled_services
        }

    @enabled_services.setter
    def enabled_services(self, services):
        """Set the enabled services.

        If the default service would be disabled by setting the set of enabled
        services, the default service will be set to ``None``.

        Args:
            services (set):
                A list of the unique service identifiers (each as
                :py:class:`~djblets.avatars.service.AvatarService`
                subclasses).

        Raises:
            djblets.avatars.errors.AvatarServiceNotFoundError:
                This exception is raised when an unknown avatar service is
                enabled.
        """
        if not isinstance(services, set):
            services = set(services)

        for service in services:
            if not self.has_service(service.id):
                raise self.lookup_error_class(self.format_error(
                    UNKNOWN_SERVICE_ENABLED, service_id=service.id))

        self._enabled_services = {service.id for service in services}
        default_service = self.default_service

        if (default_service is not None and
            not self.is_enabled(default_service.avatar_service_id)):
            self.set_default_service(None)

    @property
    def default_service(self):
        """Return the default avatar service.

        Returns:
            djblets.avatars.services.AvatarService:
            The default avatar service, or ``None`` if there isn't one.
        """
        self.populate()

        if self._default_service_id is None:
            return None

        return self.get('avatar_service_id', self._default_service_id)

    def set_default_service(self, service, save=True):
        """Set the default avatar service.

        Args:
            service (djblets.avatars.service.AvatarService):
                The avatar service to set as default.

            save (bool):
                Whether or not the registry should be saved to the database
                afterwards.

        Raises:
            djblets.avatars.errors.AvatarServiceNotFoundError:
                Raised if the service cannot be found.

            djblets.avatars.errors.DisabledServiceError:
                Raised if the service is not enabled.
        """
        self.populate()

        if service is None:
            self._default_service_id = None
        elif service not in self:
            raise self.lookup_error_class(self.format_error(
                UNKNOWN_SERVICE_DEFAULT, service_id=service.id))
        elif not self.is_enabled(service.id):
            raise DisabledServiceError(self.format_error(
                DISABLED_SERVICE_DEFAULT, service_id=service.id))
        else:
            self._default_service_id = service.id

        if save:
            self.save()

    def has_service(self, service_id):
        """Return whether or not the avatar service ID is registered.

        Args:
            service_id (unicode):
                The service's unique identifier.

        Returns:
            bool: Whether or not the service ID is registered.
        """
        try:
            # We do this to get around usage of the ExceptionFreeGetterMixin.
            return self.get('avatar_service_id', service_id) in self
        except ItemLookupError:
            return False

    def disable_service(self, service_id, save=True):
        """Disable an avatar service.

        This has no effect if the service is already disabled. If the default
        service becomes be disabled, it becomes ``None``.

        Args:
            service_id (unicode):
                The service's unique identifier.

            save (bool, optional):
                Whether or not the avatar service registry will be saved to
                the database after disabling the service. This defaults to
                ``True``.

        Raises:
            djblets.avatars.errors.AvatarServiceNotFoundError:
                This is raised if the service is not registered.
        """
        if not self.has_service(service_id):
            raise self.lookup_error_class(self.format_error(
                UNKNOWN_SERVICE_DISABLED, service_id=service_id))

        self._enabled_services.discard(service_id)
        default_service = self.default_service

        if default_service is not None and default_service.id == service_id:
            self.set_default_service(None)

        if save:
            self.save()

    def enable_service(self, service_id, save=True):
        """Enable an avatar service.

        Args:
            service_id (unicode):
                The service's unique identifier.

            save (bool, optional):
                Whether or not the avatar service registry will be saved to the
                database after enabling the service. This defaults to ``True``.

        Raises:
            djblets.avatars.errors.AvatarServiceNotFoundError:
                This is raised if the service is not registered.
        """
        if not self.has_service(service_id):
            raise self.lookup_error_class(self.format_error(
                UNKNOWN_SERVICE_ENABLED, service_id=service_id))

        self._enabled_services.add(service_id)

        if save:
            self.save()

    def is_enabled(self, service_id):
        """Return whether or not the given avatar service is enabled.

        Args:
            service_id (unicode):
                The service's unique identifier.

        Returns:
            bool: Whether or not the service ID is registered.
        """
        return (self.has_service(service_id) and
                service_id in self._enabled_services)

    def unregister(self, service):
        """Unregister an avatar service.

        If the service is enabled, it will be disabled.

        Args:
            service (djblets.avatars.services.AvatarService):
                The avatar service to unregister.

        Raises:
            djblets.avatars.errors.AvatarServiceNotFoundError:
                Raised if the specified service cannot be found.
        """
        self.disable_service(service.id)
        super(AvatarServiceRegistry, self).unregister(service)

    def populate(self):
        """Populate the avatar service registry.

        The registry is populated from the site configuration in the database.
        Both the list of enabled avatar services and the default avatar service
        are retrieved from the database.

        This method intentionally does not throw exceptions -- errors here will
        be logged instead.
        """
        if self.populated:
            return

        super(AvatarServiceRegistry, self).populate()

        siteconfig = SiteConfiguration.objects.get_current()
        avatar_service_ids = siteconfig.get(self.ENABLED_SERVICES_KEY)

        if avatar_service_ids:
            for avatar_service_id in avatar_service_ids:
                if self.has_service(avatar_service_id):
                    self.enable_service(avatar_service_id, save=False)
                else:
                    logging.error(self.format_error(
                        UNKNOWN_SERVICE_ENABLED, service_id=avatar_service_id))

        default_service_id = siteconfig.get(self.DEFAULT_SERVICE_KEY)

        if default_service_id is not None:
            try:
                default_service = self.get('avatar_service_id',
                                           default_service_id)
                self.set_default_service(default_service)
            except ItemLookupError:
                logging.error(self.format_error(UNKNOWN_SERVICE_DEFAULT,
                                                service_id=default_service_id))
            except DisabledServiceError:
                logging.error(self.format_error(DISABLED_SERVICE_DEFAULT,
                                                service_id=default_service_id))
        self.save()

    def get_defaults(self):
        """Yield the default avatar services.

        By default, this is only the Gravatar service.
        """
        yield GravatarService()

    def save(self):
        """Save the list of enabled avatar services to the database."""
        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig.set(self.ENABLED_SERVICES_KEY, list(self._enabled_services))
        siteconfig.set(self.DEFAULT_SERVICE_KEY, self._default_service_id)
        siteconfig.save()
