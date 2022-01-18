"""Error classes for extensions."""

from django.utils.translation import gettext as _


class EnablingExtensionError(Exception):
    """An extension could not be enabled."""

    def __init__(self, message, load_error=None, needs_reload=False):
        """Initialize the error.

        Args:
            message (unicode):
                The detailed error message.

            load_error (unicode, optional):
                An exception from the attempt to enable the extension, or
                other useful information to display to the user to help
                diagnose the problem.

            needs_reload (bool, optional):
                Whether fixing this error requires reloading the extension.
        """
        super(EnablingExtensionError, self).__init__(message)

        self.load_error = load_error
        self.needs_reload = needs_reload


class DisablingExtensionError(Exception):
    """An extension could not be disabled."""
    pass


class InstallExtensionError(Exception):
    """An extension could not be installed."""
    def __init__(self, message, load_error=None):
        self.message = message
        self.load_error = load_error


class InstallExtensionMediaError(InstallExtensionError):
    """An error indicating that extension media files could not be installed.
    """


class InvalidExtensionError(Exception):
    """An extension does not exist."""
    def __init__(self, extension_id):
        super(InvalidExtensionError, self).__init__()
        self.message = _("Cannot find extension with id %s") % extension_id
