"""A registry for managing avatar services."""

from __future__ import unicode_literals

import logging

from django.utils.translation import ugettext_lazy as _

from djblets.avatars.errors import (AvatarServiceNotFoundError,
                                    DisabledServiceError)
from djblets.avatars.services.gravatar import GravatarService
from djblets.avatars.services.url import URLAvatarService
from djblets.avatars.settings import AvatarSettingsManager
from djblets.registries.registry import (ALREADY_REGISTERED,
                                         ATTRIBUTE_REGISTERED, DEFAULT_ERRORS,
                                         NOT_REGISTERED, Registry, UNREGISTER)
from djblets.siteconfig.models import SiteConfiguration


DISABLED_SERVICE = 'disabled_service'
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
    DISABLED_SERVICE: _(
        'Could not fetch instance of %(service_id)s service: This service is '
        'disabled.'
    ),
    DISABLED_SERVICE_DEFAULT: _(
        'Could not set the default service to %(service_id)s: This service is '
        'disabled.'
    ),
    NOT_REGISTERED: _(
        'Unknown avatar service %(attr_value)s: This service is not '
        'registered.'
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

    #: The default avatar service classes.
    default_avatar_service_classes = [
        GravatarService,
        URLAvatarService,
    ]

    #: The settings manager for avatar services.
    #:
    #: This should be changed in a subclass as the default cannot get or set
    #: avatar service configurations.
    settings_manager_class = AvatarSettingsManager

    def __init__(self):
        """Initialize the avatar service registry."""
        super(AvatarServiceRegistry, self).__init__()

        self._enabled_services = set()
        self._default_service_id = None
        self._instance_cache = {}

    def get_avatar_service(self, avatar_service_id):
        """Return an instance of the requested avatar service.

        The instance will be instantiated with the
        :py:attr:`settings_manager_class`.

        Args:
            avatar_service_id (unicode):
                The unique identifier for the avatar service.

        Returns:
            djblets.avatars.services.base.AvatarService:
            The requested avatar service.

        Raises:
            AvatarServiceNotFoundError:
                Raised if the avatar service cannot be found.

            DisabledServiceError:
                Raised if the requested service is disabled.
        """
        if avatar_service_id not in self._instance_cache:
            try:
                service_cls = self.get('avatar_service_id', avatar_service_id)
            except self.lookup_error_class:
                service_cls = None

            if service_cls:
                if not self.is_enabled(service_cls):
                    raise DisabledServiceError(self.format_error(
                        DISABLED_SERVICE,
                        service_id=avatar_service_id))

                service = self._instance_cache[avatar_service_id] = \
                    service_cls(self.settings_manager_class)
            else:
                # If get() returns None, that means ExceptionFreeGetterMixin is
                # used, so we will return None here too. Otherwise, if the
                # mixin is not used, we will have thrown by now.
                return None
        else:
            service = self._instance_cache[avatar_service_id]
            assert self.is_enabled(type(service))

        return service

    @property
    def configurable_services(self):
        """Yield the enabled service instances that have configuration forms.

        Yields:
            tuple:
            djblets.avatars.forms.AvatarServiceConfigForm:
            The enabled services that have configuration forms.
        """
        self.populate()
        return (
            self.get_avatar_service(service.avatar_service_id)
            for service in self.enabled_services
            if service.is_configurable() and not service.hidden
        )

    @property
    def enabled_services(self):
        """Return the enabled services.

        Returns:
            set:
            The set of enabled avatar services, as
            :py:class:`djblets.avatars.service.AvatarService` instances.
        """
        self.populate()

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
                The set of services to set as enabled. Each element must be a
                subclass of :py:class:`~djblets.avatars.service.AvatarService`.

        Raises:
            djblets.avatars.errors.AvatarServiceNotFoundError:
                This exception is raised when an unknown avatar service is
                enabled.
        """
        self.populate()

        if not isinstance(services, set):
            services = set(services)

        for service in services:
            if service not in self:
                raise self.lookup_error_class(self.format_error(
                    UNKNOWN_SERVICE_ENABLED,
                    service_id=service.avatar_service_id))

        new_service_ids = {
            service.avatar_service_id
            for service in services
        }

        to_enable = new_service_ids - self._enabled_services
        to_disable = self._enabled_services - new_service_ids

        for service_id in to_disable:
            self.disable_service(self.get('avatar_service_id', service_id),
                                 save=False)

        for service_id in to_enable:
            self.enable_service(self.get('avatar_service_id', service_id),
                                save=False)

        default_service = self.default_service

        if (default_service is not None and
            not self.is_enabled(type(default_service))):
            self.set_default_service(None)

        self.save()

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

        return self.get_avatar_service(self._default_service_id)

    def set_default_service(self, service, save=True):
        """Set the default avatar service.

        Args:
            service (Type[AvatarService]):
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
                UNKNOWN_SERVICE_DEFAULT, service_id=service.avatar_service_id))
        elif not self.is_enabled(service):
            raise DisabledServiceError(self.format_error(
                DISABLED_SERVICE_DEFAULT,
                service_id=service.avatar_service_id))
        else:
            self._default_service_id = service.avatar_service_id

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
            return self.get('avatar_service_id', service_id) in self
        except self.lookup_error_class:
            return False

    def disable_service(self, service, save=True):
        """Disable an avatar service.

        This has no effect if the service is already disabled. If the default
        service becomes be disabled, it becomes ``None``.

        Args:
            service (Type[AvatarService]):
                The service to disable

            save (bool, optional):
                Whether or not the avatar service registry will be saved to
                the database after disabling the service. This defaults to
                ``True``.

        Raises:
            djblets.avatars.errors.AvatarServiceNotFoundError:
                This is raised if the service is not registered.
        """
        if service not in self:
            raise self.lookup_error_class(self.format_error(
                UNKNOWN_SERVICE_DISABLED,
                service_id=service.avatar_service_id))

        default_service = type(self.default_service)
        self._enabled_services.discard(service.avatar_service_id)

        if default_service is service:
            self.set_default_service(None)

        try:
            del self._instance_cache[service.avatar_service_id]
        except KeyError:
            pass

        if save:
            self.save()

    def enable_service(self, service, save=True):
        """Enable an avatar service.

        Args:
            service (type):
                The service to enable. This must be a subclass of
                :py:class:`~djblets.avatars.service.AvatarService`.

            save (bool, optional):
                Whether or not the avatar service registry will be saved to the
                database after enabling the service. This defaults to ``True``.

        Raises:
            djblets.avatars.errors.AvatarServiceNotFoundError:
                This is raised if the service is not registered.
        """
        if service not in self:
            raise self.lookup_error_class(self.format_error(
                UNKNOWN_SERVICE_ENABLED, service_id=service.avatar_service_id))

        self._enabled_services.add(service.avatar_service_id)

        if save:
            self.save()

    def is_enabled(self, service):
        """Return whether or not the given avatar service is enabled.

        Args:
            service (type):
                The service to check. This must be a ubclass of
                :py:class:`~djblets.avatars.service.AvatarService`.

        Returns:
            bool: Whether or not the service ID is registered.
        """
        return (service in self and
                service.avatar_service_id in self._enabled_services)

    def unregister(self, service):
        """Unregister an avatar service.

        If the service is enabled, it will be disabled.

        Args:
            service (Type[AvatarService]):
                The avatar service to unregister.

        Raises:
            djblets.avatars.errors.AvatarServiceNotFoundError:
                Raised if the specified service cannot be found.
        """
        self.disable_service(service)
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
                    self.enable_service(
                        self.get('avatar_service_id', avatar_service_id),
                        save=False)
                else:
                    logging.error(self.format_error(
                        UNKNOWN_SERVICE_ENABLED, service_id=avatar_service_id))

        default_service_id = siteconfig.get(self.DEFAULT_SERVICE_KEY)

        if default_service_id is not None:
            try:
                default_service = self.get('avatar_service_id',
                                           default_service_id)
                self.set_default_service(default_service)
            except self.lookup_error_class:
                logging.error(self.format_error(UNKNOWN_SERVICE_DEFAULT,
                                                service_id=default_service_id))
            except DisabledServiceError:
                logging.error(self.format_error(DISABLED_SERVICE_DEFAULT,
                                                service_id=default_service_id))
        self.save()

    def get_defaults(self):
        """Yield the default avatar services.

        Subclasses should override the
        :py:attr:`default_avatar_service_classes` attribute instead of this in
        most cases.
        """
        for service_class in self.default_avatar_service_classes:
            yield service_class

    def save(self):
        """Save the list of enabled avatar services to the database."""
        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig.set(self.ENABLED_SERVICES_KEY, list(self._enabled_services))
        siteconfig.set(self.DEFAULT_SERVICE_KEY, self._default_service_id)
        siteconfig.save()

    def for_user(self, user, service_id=None):
        """Return the requested avatar service for the given user.

        The following options will be tried:

            * the requested avatar service (if it is enabled);
            * the user's chosen avatar service (if it is enabled); or
            * the default avatar service (which may be ``None``).

        Args:
            user (django.contrib.auth.models.User):
                The user to retrieve the avatar service for.

            service_id (unicode, optional):
                The unique identifier of the service that is to be retrieved.
                If this is ``None``, the default service will be used.

        Returns:
            djblets.avatars.services.base.AvatarService:
            An avatar service, or ``None`` if one could not be found.
        """
        settings_manager = self.settings_manager_class(user)
        user_service_id = settings_manager.avatar_service_id

        for sid in (service_id, user_service_id):
            if sid is None or not self.has_service(sid):
                continue

            service = self.get('avatar_service_id', sid)

            if self.is_enabled(service):
                return self.get_avatar_service(sid)

        return self.default_service
