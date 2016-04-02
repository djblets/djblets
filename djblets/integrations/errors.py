"""Exceptions for integrations."""

from __future__ import unicode_literals

from django.utils.translation import ugettext as _


class IntegrationError(Exception):
    """Base class for integration-related errors."""


class IntegrationRegistrationError(IntegrationError):
    """Error registering an integration."""


class IntegrationAlreadyRegisteredError(IntegrationRegistrationError):
    """An integration was already registered."""

    def __init__(self, integration_id):
        super(IntegrationAlreadyRegisteredError, self).__init__(
            _('The integration ID "%s" was already registered.')
            % integration_id)


class IntegrationNotRegisteredError(IntegrationError):
    """Error indicating that the given integration wasn't registered."""

    def __init__(self, integration_id):
        super(IntegrationNotRegisteredError, self).__init__(
            _('The integration ID "%s" has not been registered.')
            % integration_id)
