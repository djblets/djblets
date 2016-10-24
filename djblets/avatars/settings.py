"""Settings managers for avatar service registries."""

from __future__ import unicode_literals


class AvatarSettingsManager(object):
    """The settings manager is responsible for loading and saving settings.

    Each user can have different avatar configuration and the settings
    manager is responsible for loading and saving per-user configuration for
    services.

    This class is intended to be sub-classed to be able to provide
    configuration management for individual users.
    """

    def __init__(self, user):
        """Initialize the settings manager.

        Args:
            user (django.contrib.auth.models.User):
                The user.
        """
        self.user = user

    @property
    def avatar_service_id(self):
        """The service ID for the user's selected avatar service.

        Returns:
            unicode:
            The avatar service ID for the user's selected avatar service, or
            ``None`` if they have not selected one.
        """
        raise NotImplementedError('%s does not implement avatar_service_id'
                                  % type(self).__name__)

    @avatar_service_id.setter
    def avatar_service_id(self, avatar_service_id):
        """Set the avatar service ID for the user.

        Args:
            avatar_service_id (unicode):
                The ID of the :py:class:`avatar service
                <djblets.avatars.services.base.AvatarService>` to set.
        """
        raise NotImplementedError('%s does not implement avatar_service_id'
                                  % type(self).__name__)

    @property
    def configuration(self):
        """The user's configuration for the service.

        This must be implemented in a subclasses.

        Returns:
            dict:
            The user's configuration.
        """
        raise NotImplementedError('%s does not implement configuration'
                                  % type(self).__name__)

    @configuration.setter
    def configuration(self, settings):
        """Set the user's configuration for the service.

        This must be implemented in a subclass.

        Args:
            settings (dict):
                The settings to save.
        """
        raise NotImplementedError('%s does not implement configuration'
                                  % type(self).__name__)

    def configuration_for(self, avatar_service_id):
        """Get the configuration for the requested avatar service.

        Args:
            avatar_service_id (unicode):
                The ID of the :py:class:`avatar service
                <djblets.avatars.services.base.AvatarService>` to retrieve
                configuration for.
        """
        raise NotImplementedError('%s does not implement configuration_for'
                                  % type(self).__name__)

    def save(self):
        """Save the configuration.

        This must be implemented in a subclass.
        """
        raise NotImplementedError('%s does not implement save()')
