"""Error classes for user consents."""

from __future__ import unicode_literals

from djblets.registries.errors import AlreadyRegisteredError, ItemLookupError


class ConsentRequirementConflictError(AlreadyRegisteredError):
    """A consent requirement with a given ID was already registered."""


class ConsentRequirementNotFoundError(ItemLookupError):
    """A consent requirement was not found."""
