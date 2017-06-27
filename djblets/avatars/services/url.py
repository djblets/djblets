"""An avatar service for setting absolute URLs for avatars."""

from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from djblets.avatars.services.base import AvatarService


class URLAvatarService(AvatarService):
    """An avatar service for settings absolute URLs for avatars.

    This avatar service is not available to users and is meant to be used by
    bots from extensions to provide their own avatars.

    Automation users can be configured to use this service with the following
    code:

    .. code-block:: python

       from djblets.avatars.services import URLAvatarService


       avatar_services = get_avatar_service_registry()
       service = avatar_services.get_avatar_service(
           URLAvatarService.avatar_service_id)

       service.setup(
           user,
           {
               '1x': 'http://example.com/static/avatar.png',
               '2x': 'http://example.com/static/avatar@2x.png',
           })
    """

    avatar_service_id = 'url'
    name = _('URL Avatar Service')
    hidden = True

    def setup(self, user, urls):
        """Set up this avatar service for the given user.

        The user will be configured to use this service as their avatar service
        and the given URLs will be used for their avatars.

        Args:
            user (django.contrib.auth.models.User):
                The user to set the URLs for.

            urls (dict):
                A dictionary mapping resolutions ('1x', '2x', etc.) to absolute
                URLs.
        """
        settings_manager = self._settings_manager_class(user)
        settings_manager.avatar_service_id = self.avatar_service_id
        settings_manager.configuration_for(self.avatar_service_id).update(urls)
        settings_manager.save()

    def get_avatar_urls_uncached(self, user, size):
        """Return the avatar URLs for the requested user.

        Args:
            user (django.contrib.auth.models.User):
                The user whose avatar URLs are to be fetched.

            size (int):
                The size (in pixels) the avatar is to be rendered at.

        Returns:
            dict:
            A dictionary mapping resolutions ('1x', '2x', etc.) to the user's
            avatar URLs.
        """
        return (
            self._settings_manager_class(user)
            .configuration_for(self.avatar_service_id)
        )

    def get_etag_data(self, user):
        """Return the ETag data for the user's avatar.

        Args:
            user (django.contrib.auth.models.User):
                The user.

        Returns:
            list of unicode:
            The uniquely identifying information for the user's avatar.
        """
        urls = self._settings_manager_class(user).configuration_for(
            self.avatar_service_id)

        data = [self.avatar_service_id]

        # The sort order here does not matter as long as it is consistent.
        for key in sorted(urls):
            data.append(key)
            data.append(urls[key])

        return data
