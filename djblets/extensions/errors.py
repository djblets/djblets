"""Error classes for extensions."""

from __future__ import annotations

from typing import Optional

from django.utils.translation import gettext as _


class EnablingExtensionError(Exception):
    """An extension could not be enabled."""

    def __init__(
        self,
        message: str,
        load_error: Optional[str] = None,
        needs_reload: bool = False,
    ) -> None:
        """Initialize the error.

        Args:
            message (str):
                The detailed error message.

            load_error (str, optional):
                An exception from the attempt to enable the extension, or
                other useful information to display to the user to help
                diagnose the problem.

            needs_reload (bool, optional):
                Whether fixing this error requires reloading the extension.
        """
        super().__init__(message)

        self.load_error = load_error
        self.needs_reload = needs_reload


class DisablingExtensionError(Exception):
    """An extension could not be disabled."""
    pass


class InstallExtensionError(Exception):
    """An extension could not be installed."""

    def __init__(
        self,
        message: str,
        load_error: Optional[str] = None,
    ) -> None:
        """Initialize the error.

        Args:
            message (str):
                The detailed error message.

            load_error (str, optional):
                An exception from the attempt to enable the extension, or
                other useful information to display to the user to help
                diagnose the problem.
        """
        super().__init__(message)
        self.load_error = load_error


class InstallExtensionMediaError(InstallExtensionError):
    """An error indicating that extension media files could not be installed.
    """


class InvalidExtensionError(Exception):
    """An extension does not exist."""

    def __init__(
        self,
        extension_id: str,
    ) -> None:
        """Initialize the error.

        Args:
            extension_id (str):
                The ID of the extension which could not be found.
        """
        super().__init__(_('Cannot find extension with id %s') % extension_id)


class ExtensionPackagingError(Exception):
    """An error packaging an extension.

    Version Added:
        5.0
    """
