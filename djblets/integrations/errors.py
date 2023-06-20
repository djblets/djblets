"""Exceptions for integrations."""

from __future__ import annotations

from typing import Optional

from django.utils.translation import gettext as _


class IntegrationError(Exception):
    """Base class for integration-related errors."""


class IntegrationRegistrationError(IntegrationError):
    """Error registering an integration."""


class IntegrationAlreadyRegisteredError(IntegrationRegistrationError):
    """An integration was already registered."""

    def __init__(
        self,
        integration_id: str,
    ) -> None:
        """Initialize the error.

        Args:
            integration_id (str):
                The ID of the integration that was already registered.
        """
        super().__init__(
            _('The integration ID "%s" was already registered.')
            % integration_id)


class IntegrationNotRegisteredError(IntegrationError):
    """Error indicating that the given integration wasn't registered."""

    def __init__(
        self,
        integration_id: Optional[str],
    ) -> None:
        """Initialize the error.

        Args:
            integration_id (str):
                The ID of the integration that has not been registered.
        """
        if integration_id is None:
            message = _('No integration ID has been provided.')
        else:
            message = (
                _('The integration ID "%s" has not been registered.')
                % integration_id
            )

        super().__init__(message)
