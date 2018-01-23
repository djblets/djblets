"""Middleware for managing site configurations."""

from __future__ import unicode_literals

from djblets.siteconfig.models import SiteConfiguration


class SettingsMiddleware(object):
    """Middleware for performing expiration checks for site configuration.

    This will check the site configuration before each request is handled in
    order to see if it has expired, ensuring that the the request is able to
    work with the most up-to-date settings from the database.
    """

    def process_request(self, request):
        """Process the HTTP request.

        This will perform an expiration check for the site configurations.

        Args:
            request (django.http.HttpRequest):
                The HTTP request being processed.
        """
        SiteConfiguration.objects.check_expired()
