"""A base form for working with settings stored on SiteConfigurations."""

from __future__ import annotations

from typing import Optional

from django.http import HttpRequest

from djblets.forms.forms import KeyValueForm
from djblets.siteconfig.models import (SiteConfiguration,
                                       SiteConfigurationSettingsValue)


class SiteSettingsForm(KeyValueForm):
    """A base form for loading/saving settings for a SiteConfiguration.

    This is meant to be subclassed for different settings pages. Any fields
    defined by the form will be loaded/saved automatically.
    """

    #: The HTTP request used for this form.
    #:
    #: Type:
    #:     django.http.HttpRequest
    request: HttpRequest

    #: The site configuration settings that are loaded from and saved to.
    #:
    #: Type:
    #:      djblets.siteconfig.models.SiteConfiguration
    siteconfig: SiteConfiguration

    def __init__(
        self,
        siteconfig: SiteConfiguration,
        *args,
        **kwargs,
    ) -> None:
        """Initialize the form.

        Args:
            siteconfig (djblets.siteconfig.models.SiteConfiguration):
                The site configuration to work with on the form.

            *args (tuple):
                Positional arguments to pass to the parent constructor.

            **kwargs (dict):
                Keyword arguments to pass to the parent constructor.
        """
        self.request = kwargs.pop('request', None)
        self.siteconfig = siteconfig

        super().__init__(instance=siteconfig, *args, **kwargs)

    def get_key_value(
        self,
        key: str,
        default: Optional[SiteConfigurationSettingsValue] = None,
    ) -> Optional[SiteConfigurationSettingsValue]:
        """Return the value for a SiteConfiguration settings key.

        Args:
            key (str):
                The settings key.

            default (object, unused):
                The default value from the form, which will be ignored,
                so that the registered siteconfig defaults will be used.

        Returns:
            object:
            The resulting value from the settings.
        """
        return self.siteconfig.get(key)

    def set_key_value(
        self,
        key: str,
        value: SiteConfigurationSettingsValue,
    ) -> None:
        """Set the value for a SiteConfiguration settings key.

        Args:
            key (str):
                The settings key.

            value (object):
                The settings value.
        """
        self.siteconfig.set(key, value)

    def save_instance(self) -> None:
        """Save the SiteConfiguration instance."""
        self.siteconfig.save()
