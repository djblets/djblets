"""Error classes for features."""

from __future__ import unicode_literals

from djblets.registries.errors import AlreadyRegisteredError, ItemLookupError


class FeatureConflictError(AlreadyRegisteredError):
    """A feature was not found."""


class FeatureNotFoundError(ItemLookupError):
    """A feature was not found."""
