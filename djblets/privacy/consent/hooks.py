"""Extension hooks for consent requirements."""

from __future__ import unicode_literals

from django.utils import six

from djblets.extensions.hooks import BaseRegistryHook, ExtensionHookPoint
from djblets.privacy.consent.registry import get_consent_requirements_registry


@six.add_metaclass(ExtensionHookPoint)
class ConsentRequirementHook(BaseRegistryHook):
    """Registers a ConsentRequirement for use of personal data."""

    @property
    def registry(self):
        """The registry that the hook interfaces with."""
        return get_consent_requirements_registry()
