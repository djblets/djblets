"""Error classes for user consents."""

from djblets.registries.errors import AlreadyRegisteredError, ItemLookupError


class ConsentRequirementConflictError(AlreadyRegisteredError):
    """A consent requirement with a given ID was already registered."""


class ConsentRequirementNotFoundError(ItemLookupError):
    """A consent requirement was not found."""
