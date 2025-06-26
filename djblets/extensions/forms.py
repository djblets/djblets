"""Form definitions for extensions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from djblets.extensions.settings import ExtensionSettings
from djblets.forms.forms import KeyValueForm

if TYPE_CHECKING:
    from django.http import HttpRequest

    from djblets.extensions.extension import Extension
    from djblets.util.typing import JSONValue


class SettingsForm(KeyValueForm[ExtensionSettings]):
    """Settings form for extension configuration.

    A base form for loading/saving settings for an extension. This is meant
    to be overridden by extensions to provide configuration pages. Any fields
    defined by the form will be loaded and saved automatically.
    """

    def __init__(
        self,
        extension: Extension,
        *args,
        request: (HttpRequest | None) = None,
        **kwargs,
    ) -> None:
        """Initialize the form.

        Args:
            extension (djblets.extensions.extension.Extension):
                The extension instance.

            *args (tuple):
                Positional arguments to pass through to the parent class.

            request (django.http.HttpRequest, optional):
                The HTTP request from the client.

            **kwargs (dict):
                Keyword arguments to pass through to the parent class.
        """
        self.request = request
        self.extension = extension
        self.settings = extension.settings

        super().__init__(instance=extension.settings, *args, **kwargs)

    def set_key_value(
        self,
        key: str,
        value: JSONValue,
    ) -> None:
        """Set the value for an extension settings key.

        Args:
            key (str):
                The settings key.

            value (object):
                The settings value.
        """
        assert self.instance is not None
        self.instance.set(key, value)

    def save_instance(self) -> None:
        """Save the instance."""
        assert self.instance is not None
        self.instance.save()
