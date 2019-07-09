"""A registry for managing avatar services."""

from __future__ import unicode_literals

import logging
import warnings

from django.utils.translation import ugettext_lazy as _

from djblets.avatars.errors import (AvatarServiceNotFoundError,
                                    DisabledServiceError)
from djblets.avatars.services.fallback import FallbackService
from djblets.avatars.services.gravatar import GravatarService
from djblets.avatars.services.url import URLAvatarService
from djblets.avatars.settings import AvatarSettingsManager
from djblets.privacy.consent import Consent, get_consent_tracker
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


logger = logging.getLogger(__name__)


class AvatarServiceRegistry(Registry):
    """A registry for avatar services.

    This registry manages a set of avatar services (see
    :py:mod:`djblets.avatars.services.gravatar` for an example). The registries
    are saved to the database and require the use of the
    :py:mod:`djblets.siteconfig` app.

    .. versionchanged:: 1.0.3

       The avatar configuration is now retrieved from and immediately written
       to the current :py:class:`~djblets.siteconfig.models.SiteConfiguration`,
       in order to ensure that the list of enabled avatar services and the
       default service are never stale. This differs from 1.0.0 through 1.0.2,
       where the callers could make change to the local state without ever
       risking it being written to the database (which is generally not the
       desired behavior anyway).
    """

    #: The key name for the list of enabled services.
    ENABLED_SERVICES_KEY = 'avatars_enabled_services'

    #: The key name for specifying whether consent must be checked.
    ENABLE_CONSENT_CHECKS = 'avatars_enable_consent_checks'

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

    #: A fallback service to use if others are not available.
    #:
    #: Version Added:
    #:     1.0.11
    fallback_service_class = FallbackService

    #: The settings manager for avatar services.
    #:
    #: This should be changed in a subclass as the default cannot get or set
    #: avatar service configurations.
    settings_manager_class = AvatarSettingsManager

    def __init__(self):
        """Initialize the avatar service registry."""
        super(AvatarServiceRegistry, self).__init__()

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
            The requested avatar service, or ``None`` if not found.

        Raises:
            djblets.avatars.errors.DisabledServiceError:
                The requested service is disabled.
        """
        service = self._instance_cache.get(avatar_service_id)

        if service is None:
            try:
                service_cls = self.get('avatar_service_id', avatar_service_id)
            except self.lookup_error_class:
                service_cls = None

            if not service_cls:
                return None
        else:
            service_cls = type(service)

        # It's important to note that if the service instance was in the
        # cache before, that doesn't mean it should be considered enabled.
        # Another SiteConfiguration instance on another process/server
        # may have disabled it, and our SiteConfiguration may have picked
        # that up since this was added to the cache.
        if not self.is_enabled(service_cls):
            self._instance_cache.pop(avatar_service_id, None)

            raise DisabledServiceError(self.format_error(
                DISABLED_SERVICE,
                service_id=avatar_service_id))

        if service is None:
            service = self._instance_cache[avatar_service_id] = \
                service_cls(self.settings_manager_class)

        return service

    @property
    def configurable_services(self):
        """Yield the enabled service instances that have configuration forms.

        Yields:
            tuple:
            The enabled service instances that have configuration forms.
        """
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
        siteconfig = SiteConfiguration.objects.get_current()
        services = set()

        for service_id in siteconfig.get(self.ENABLED_SERVICES_KEY):
            try:
                service = self.get('avatar_service_id', service_id)
            except self.lookup_error_class:
                service = None

            if service is not None:
                services.add(service)

        return services

    def set_enabled_services(self, services, save=True):
        """Set the enabled services.

        If the default service would be disabled by setting the set of enabled
        services, the default service will be set to ``None``.

        Args:
            services (set):
                The set of services to set as enabled. Each element must be a
                subclass of :py:class:`~djblets.avatars.service.AvatarService`.

            save (bool, optional):
                Whether to save the settings after setting the list of
                enabled services. The default is to immediately save.

        Raises:
            djblets.avatars.errors.AvatarServiceNotFoundError:
                This exception is raised when an unknown avatar service is
                enabled.
        """
        new_service_ids = set()

        for service in services:
            if service in self:
                new_service_ids.add(service.avatar_service_id)
            else:
                raise self.lookup_error_class(self.format_error(
                    UNKNOWN_SERVICE_ENABLED,
                    service_id=service.avatar_service_id))

        siteconfig = SiteConfiguration.objects.get_current()
        cur_service_ids = \
            set(siteconfig.get(self.ENABLED_SERVICES_KEY))

        if new_service_ids == cur_service_ids:
            return

        to_enable = new_service_ids - cur_service_ids
        to_disable = cur_service_ids - new_service_ids

        for service_id in to_disable:
            self.disable_service_by_id(service_id, save=False)

        for service_id in to_enable:
            self.enable_service_by_id(service_id, save=False)

        default_service = self.default_service

        if (default_service is not None and
            not self.is_enabled(type(default_service))):
            self.set_default_service(None, save=False)

        if save:
            self.save()

    @property
    def default_service(self):
        """The default avatar service.

        Returns:
            djblets.avatars.services.AvatarService:
            The default avatar service, or ``None`` if there isn't one.
        """
        siteconfig = SiteConfiguration.objects.get_current()
        default_service_id = siteconfig.get(self.DEFAULT_SERVICE_KEY)

        if default_service_id is None:
            return None

        enabled_service_ids = siteconfig.get(self.ENABLED_SERVICES_KEY)

        if default_service_id not in enabled_service_ids:
            # The settings listed a default service that was no longer in
            # the list of enabled services. Warn about this, fix it, and
            # save the value in settings.
            logger.error(self.format_error(DISABLED_SERVICE_DEFAULT,
                                           service_id=default_service_id))

            # Set this manually in the SiteConfiguration instead of using
            # disable_service_by_id, to avoid infinitely recursing into this
            # property and that method, and also because it's just not
            # necessary to go through everything that function does.
            siteconfig.set(self.DEFAULT_SERVICE_KEY, None)

            return None

        return self.get_avatar_service(default_service_id)

    @property
    def fallback_service(self):
        """The fallback service used if no other services are available."""
        avatar_service_id = self.fallback_service_class.avatar_service_id
        service = self._instance_cache.get(avatar_service_id)

        if service is None:
            service = self.fallback_service_class(self.settings_manager_class)
            self._instance_cache[avatar_service_id] = service

        return service

    def set_default_service(self, service, save=True):
        """Set the default avatar service.

        Args:
            service (type):
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
        if service is None:
            default_service_id = None
        elif service not in self:
            raise self.lookup_error_class(self.format_error(
                UNKNOWN_SERVICE_DEFAULT, service_id=service.avatar_service_id))
        elif not self.is_enabled(service):
            raise DisabledServiceError(self.format_error(
                DISABLED_SERVICE_DEFAULT,
                service_id=service.avatar_service_id))
        else:
            default_service_id = service.avatar_service_id

        siteconfig = SiteConfiguration.objects.get_current()

        if default_service_id != siteconfig.get(self.DEFAULT_SERVICE_KEY):
            siteconfig.set(self.DEFAULT_SERVICE_KEY, default_service_id)

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
            service (type):
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

        self.disable_service_by_id(service.avatar_service_id, save=save)

    def disable_service_by_id(self, service_id, save=True):
        """Disable an avatar service based on its ID.

        This allows for disabling services that may or may not be registered,
        for instance those that were previously added by an extension that is
        no longer available.

        This has no effect if the service is already disabled. If the default
        service becomes be disabled, it becomes ``None``.

        Args:
            service_id (unicode):
                The ID of the service to disable.

            save (bool, optional):
                Whether or not the avatar service registry will be saved to
                the database after disabling the service. This defaults to
                ``True``.

        Raises:
            djblets.avatars.errors.AvatarServiceNotFoundError:
                This is raised if the service is not registered.
        """
        if (self.default_service is not None and
            self.default_service.avatar_service_id == service_id):
            self.set_default_service(None, save=save)

        self._instance_cache.pop(service_id, None)

        siteconfig = SiteConfiguration.objects.get_current()
        enabled_service_ids = list(siteconfig.get(self.ENABLED_SERVICES_KEY))

        try:
            enabled_service_ids.remove(service_id)
        except ValueError:
            # This wasn't enabled in the stored site configuration, so don't
            # try saving now. We're done.
            pass
        finally:
            siteconfig.set(self.ENABLED_SERVICES_KEY, enabled_service_ids)

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

        self.enable_service_by_id(service.avatar_service_id, save=save)

    def enable_service_by_id(self, service_id, save=True):
        """Enable an avatar service.

        Args:
            service_id (unicode):
                The ID of the service to enable. Callers must take care to
                ensure this matches a service stored in the registry.

            save (bool, optional):
                Whether or not the avatar service registry will be saved to the
                database after enabling the service. This defaults to ``True``.

        Raises:
            djblets.avatars.errors.AvatarServiceNotFoundError:
                This is raised if the service is not registered.
        """
        siteconfig = SiteConfiguration.objects.get_current()
        enabled_service_ids = siteconfig.get(self.ENABLED_SERVICES_KEY)

        if service_id not in enabled_service_ids:
            siteconfig.set(self.ENABLED_SERVICES_KEY,
                           enabled_service_ids + [service_id])

            if save:
                self.save()

    def is_enabled(self, service):
        """Return whether or not the given avatar service is enabled.

        Args:
            service (type):
                The service to check. This must be a ubclass of
                :py:class:`~djblets.avatars.service.AvatarService`.

        Returns:
            bool:
            Whether or not the service ID is registered.
        """
        if service not in self:
            return

        siteconfig = SiteConfiguration.objects.get_current()
        enabled_service_ids = siteconfig.get(self.ENABLED_SERVICES_KEY)

        return service.avatar_service_id in enabled_service_ids

    def unregister(self, service):
        """Unregister an avatar service.

        Note that unregistering a service does not disable it. That must be
        done manually through :py:meth:`disable_service`. Disabling is a
        persistent operation that affects all server instances now and in the
        future, while unregistering may occur during the normal shutdown of a
        particular thread or process (especially if done through an extension).

        Args:
            service (type):
                The avatar service to unregister.

        Raises:
            djblets.avatars.errors.AvatarServiceNotFoundError:
                Raised if the specified service cannot be found.
        """
        self._instance_cache.pop(service.avatar_service_id, None)

        super(AvatarServiceRegistry, self).unregister(service)

    def get_defaults(self):
        """Yield the default avatar services.

        Subclasses should override the
        :py:attr:`default_avatar_service_classes` attribute instead of this in
        most cases.
        """
        for service_class in self.default_avatar_service_classes:
            yield service_class

    def save(self):
        """Save the avatar configuration to the database.

        As the avatar configuration is stored in the
        :py:class:`~djblets.siteconfig.models.SiteConfiguration`, this method
        will save any pending configuration, synchronizing it to all other
        processes/servers.

        If there are pending avatar configuration changes (due to passing
        ``save=False`` to some methods), and there's a separate call to
        :py:meth:`SiteConfiguration.save()
        <djblets.siteconfig.models.SiteConfiguration.save>` without calling
        this method, the new avatar configuration will still be saved.
        """
        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig.save()

    def for_user(self, user, service_id=None, allow_consent_checks=True):
        """Return the requested avatar service for the given user.

        The following options will be tried:

        * The requested avatar service (if it is enabled)
        * The user's chosen avatar service (if it is enabled)
        * The default avatar service (which may be ``None``)

        Args:
            user (django.contrib.auth.models.User):
                The user to retrieve the avatar service for.

            service_id (unicode, optional):
                The unique identifier of the service that is to be retrieved.
                If this is ``None``, the default service will be used.

            allow_consent_checks (bool, optional):
                Whether to allow consent checks to take place, if required
                by the application settings and avatar backends. This should
                only be disabled if presenting configuration options or
                similar.

        Returns:
            djblets.avatars.services.base.AvatarService:
            An avatar service, or ``None`` if one could not be found.
        """
        settings_manager = self.settings_manager_class(user)
        user_service_id = settings_manager.avatar_service_id
        siteconfig = SiteConfiguration.objects.get_current()
        services = []

        for sid in (service_id, user_service_id):
            if sid is None or not self.has_service(sid):
                continue

            if self.is_enabled(self.get('avatar_service_id', sid)):
                services.append(self.get_avatar_service(sid))

        default_service = self.default_service

        if default_service is not None:
            services.append(default_service)

        services.append(self.fallback_service)

        if (allow_consent_checks and
            siteconfig.get(AvatarServiceRegistry.ENABLE_CONSENT_CHECKS)):
            # Filter out any services requiring consent that the user has not
            # consented to.
            consent_tracker = get_consent_tracker()

            services = [
                service
                for service in services
                if (not service.consent_requirement_id or
                    consent_tracker.get_consent(
                        user,
                        service.consent_requirement_id) == Consent.GRANTED)
            ]

        if services:
            return services[0]

        return None


SiteConfiguration.add_global_defaults({
    AvatarServiceRegistry.ENABLED_SERVICES_KEY: [],
    AvatarServiceRegistry.ENABLE_CONSENT_CHECKS: False,
    AvatarServiceRegistry.DEFAULT_SERVICE_KEY: None,
})
