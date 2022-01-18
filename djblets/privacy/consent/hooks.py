"""Extension hooks for consent requirements."""

from djblets.extensions.hooks import BaseRegistryHook, ExtensionHookPoint
from djblets.privacy.consent.registry import get_consent_requirements_registry


class ConsentRequirementHook(BaseRegistryHook, metaclass=ExtensionHookPoint):
    """Registers a ConsentRequirement for use of personal data."""

    @property
    def registry(self):
        """The registry that the hook interfaces with."""
        return get_consent_requirements_registry()
