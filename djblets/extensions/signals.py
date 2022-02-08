"""Extension-related signals."""

from django.dispatch import Signal


#: A signal fired when an extension is disabled.
#:
#: Args:
#:     extension (djblets.extensions.extension.Extension):
#:         The extension that was disabled.
extension_disabled = Signal()


#: A signal fired when an extension is enabled.
#:
#: Args:
#:     extension (djblets.extensions.extension.Extension):
#:         The extension that was enabled.
extension_enabled = Signal()


#: A signal fired when an extension is initialized.
#:
#: Args:
#:     extension (type):
#:         The extension class that was initialized.
#:
#:         This will be a subclass of
#:         :py:class:`djblets.extensions.extension.Extension`.
extension_initialized = Signal()


#: A signal fired when an extension is uninitialized.
#:
#: Args:
#:     extension (type):
#:         The extension class that was uninitialized.
#:
#:         This will be a subclass of
#:         :py:class:`djblets.extensions.extension.Extension`.
extension_uninitialized = Signal()


#: A signal fired when an extension's settings are saved.
settings_saved = Signal()
