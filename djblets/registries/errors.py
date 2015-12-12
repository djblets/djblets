"""Exception classes for dealing with Djblets registries."""

from __future__ import unicode_literals


class ItemLookupError(Exception):
    """An error that occurs during item lookup."""


class RegistrationError(Exception):
    """An error that occurs during registration."""


class AlreadyRegisteredError(RegistrationError):
    """An error that occurs during registering the same item."""
