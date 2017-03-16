"""Extension hooks for registering integrations."""

from __future__ import unicode_literals

import logging

from djblets.extensions.hooks import ExtensionHook
from djblets.integrations.errors import IntegrationError
from djblets.integrations.mixins import NeedsIntegrationManagerMixin


class BaseIntegrationHook(NeedsIntegrationManagerMixin, ExtensionHook):
    """Base class for an extension hook for integration management.

    Integrations enable any supporting application to connect with third-party
    services in specialized ways. This class makes it easy to register new
    integrations on an extension, binding their lifecycles to that of the
    extension.

    This is not intended to be used directly by a caller. Instead, a project
    offering integrations should subclass this and provide an implementation
    of :py:meth:`get_integration_manager`.
    """

    def initialize(self, integration_cls):
        """Initialize the hook.

        The provided integration will be registered with the integration
        manager.

        Args:
            integration_cls (type):
                The integration class to register.
        """
        self.integration_cls = integration_cls

        manager = self.get_integration_manager()

        try:
            manager.register_integration_class(self.integration_cls)
        except IntegrationError as e:
            logging.exception('%s could not register integration class '
                              '%s with %s: %s',
                              self.extension.__class__.__name__,
                              self.__class__.__name__,
                              self.integration_cls.__name__,
                              e)

    def shutdown(self):
        """Shut down the hook.

        The integration registered in this hook will be unregistered.
        """
        manager = self.get_integration_manager()

        if manager.enabled:
            try:
                manager.unregister_integration_class(self.integration_cls)
            except IntegrationError as e:
                logging.exception('%s could not unregister integration class '
                                  '%s with %s: %s',
                                  self.extension.__class__.__name__,
                                  self.__class__.__name__,
                                  self.integration_cls.__name__,
                                  e)
