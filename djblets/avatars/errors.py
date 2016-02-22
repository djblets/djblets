"""Avatar-specific errors."""

from __future__ import unicode_literals

from djblets.registries.errors import ItemLookupError


class AvatarServiceNotFoundError(ItemLookupError):
    """An avatar service specific lookup error."""


class DisabledServiceError(Exception):
    """An exception for using disabled avatar services.

    This will be thrown when a disabled avatar service is set to be the default
    avatar service.
    """
