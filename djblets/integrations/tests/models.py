"""Test models for integration unit tests."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from djblets.integrations.models import BaseIntegrationConfig

if TYPE_CHECKING:
    from djblets.integrations.manager import IntegrationManager


class IntegrationConfig(BaseIntegrationConfig):
    """Integration configuration model for unit tests."""

    manager: Optional[IntegrationManager] = None

    @classmethod
    def get_integration_manager(cls) -> IntegrationManager:
        """Return the integration manager for this model.

        Returns:
            djblets.integrations.manager.IntegrationManager:
            The integration manager for this configuration.
        """
        assert cls.manager is not None

        return cls.manager
