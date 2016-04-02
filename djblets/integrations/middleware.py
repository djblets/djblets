"""Middleware for working with integrations."""

from __future__ import unicode_literals

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from djblets.integrations.manager import get_integration_managers


class IntegrationsMiddleware(object):
    """Middleware to manage integration lifecycles and data.

    Any project making use of
    :py:class:`~djblets.integrations.manager.IntegationManager` must include
    this middleware. This will handle multi-process synchronization and cache
    invalidation, which is needed to ensure that settings aren't stale on
    other processes when a configuration is added, edited, or removed.
    """

    def __init__(self, *args, **kwargs):
        if 'djblets.integrations' not in settings.INSTALLED_APPS:
            raise ImproperlyConfigured(
                'IntegrationsMiddleware requires djblets.integrations to be '
                'listed in settings.INSTALLED_APPS.'
            )

        self.check_expiration = not getattr(settings, 'RUNNING_TEST', False)

    def process_request(self, request):
        """Process an HTTP request.

        This will run through all the integration managers, checking if any
        have expired and ensuring they have the latest state.
        """
        if self.check_expiration:
            for integration_manager in get_integration_managers():
                integration_manager.check_expired()
