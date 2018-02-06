"""Model and cache management for SiteConfiguration."""

from __future__ import unicode_literals

from django.contrib.sites.models import Site
from django.db import models
from django.utils import six

from djblets.siteconfig.signals import siteconfig_reloaded


_SITECONFIG_CACHE = {}


class SiteConfigurationManager(models.Manager):
    """Manages cached instances of a SiteConfiguration.

    This provides functions for retrieving the current
    :py:class:`~djblets.siteconfig.models.SiteConfiguration` instance and
    working with cache expiration. Consumers are expected to use
    :py:meth:`get_current` to retrieve their instance, and are also expected
    to use the :py:class:`~djblets.siteconfig.middleware.SettingsMiddleware`
    to manage expiration between server processes.
    """

    def get_current(self):
        """Return the site configuration for the active site.

        Multiple calls to this method for the same
        :py:class:`~django.contrib.sites.models.Site` will return the same
        instance, as long as the old instance has not expired. Callers should
        not store the result of this method, as it may not be valid for long.

        Returns:
            djblets.siteconfig.models.SiteConfiguration:
            The current site configuration for the active site.

        Raises:
            django.core.exceptions.ImproperlyConfigured:
                Site information wasn't configured in Django.
        """
        return self.get_for_site_id(Site.objects.get_current().pk)

    def get_for_site_id(self, site_id):
        """Return the site configuration for a specific site ID.

        Multiple calls to this method for the same
        :py:class:`~django.contrib.sites.models.Site` will return the same
        instance, as long as the old instance has not expired. Callers should
        not store the result of this method, as it may not be valid for long.

        Args:
            site (int):
                The ID of the site to retrieve the configuration for.

        Returns:
            djblets.siteconfig.models.SiteConfiguration:
            The current site configuration for the specified site.
        """
        try:
            siteconfig = _SITECONFIG_CACHE[site_id]
        except KeyError:
            siteconfig = self.model.objects.get(site_id=site_id)
            _SITECONFIG_CACHE[site_id] = siteconfig

        return siteconfig

    def clear_cache(self):
        """Clear the entire SiteConfiguration cache.

        The next call to :py:meth:`get_current` for any
        :py:class:`~django.contrib.sites.models.Site` will query the
        database.
        """
        global _SITECONFIG_CACHE

        _SITECONFIG_CACHE = {}

    def check_expired(self):
        """Check whether any SiteConfigurations have expired.

        If a :py:class:`~djblets.siteconfig.models.SiteConfiguration` has
        expired (another process/server has saved a more recent version),
        this method will expire the cache for the old version.

        If there are any listeners for the
        :py:data:`~djblets.siteconfig.signals.siteconfig_reloaded` signal,
        a new :py:class:`~djblets.siteconfig.models.SiteConfiguration`
        instance will be immediately loaded and the signal will fire.
        Otherwise, a new instance will not be loaded right away.

        This should be called on each HTTP request. It's recommended that
        consumers use
        :py:class:`~djblets.siteconfig.middleware.SettingsMiddleware` to do
        this. It can also be called manually for long-living processes that
        aren't bound to HTTP requests.

        .. versionchanged:: 1.0.3

           The :py:data:`~djblets.siteconfig.signals.siteconfig_reloaded`
           signal is now emitted with a newly-fetched instance if there are
           any listeners.
        """
        send_signal = siteconfig_reloaded.has_listeners()

        for site_id, siteconfig in six.iteritems(_SITECONFIG_CACHE.copy()):
            if siteconfig.is_expired():
                try:
                    # This is stale. Get rid of it so we can load it next time.
                    del _SITECONFIG_CACHE[site_id]
                except KeyError:
                    # Another thread probably took care of this. We're done
                    # with this one.
                    continue

                # If there are any listeners to the signal, then reload the
                # SiteConfiguration now and let consumers know about it.
                # If there aren't any listeners, we save a database query,
                # and the instance will be loaded next time a caller
                # requests it.
                if send_signal:
                    siteconfig_reloaded.send(
                        sender=None,
                        siteconfig=self.get_for_site_id(site_id),
                        old_siteconfig=siteconfig)
