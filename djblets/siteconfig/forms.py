"""A base form for working with settings stored on SiteConfigurations."""

from __future__ import unicode_literals

from djblets.forms.forms import KeyValueForm


class SiteSettingsForm(KeyValueForm):
    """A base form for loading/saving settings for a SiteConfiguration.

    This is meant to be subclassed for different settings pages. Any fields
    defined by the form will be loaded/saved automatically.

    Attributes:
        request (django.http.HttpRequest):
            The HTTP request used for this form.

        siteconfig (djblets.siteconfig.models.SiteConfiguration):
            The site configuration settings are loaded from and saved to.
    """

    def __init__(self, siteconfig, *args, **kwargs):
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

        super(SiteSettingsForm, self).__init__(instance=siteconfig,
                                               *args, **kwargs)

    def get_key_value(self, key, default=None):
        """Return the value for a SiteConfiguration settings key.

        Args:
            key (unicode):
                The settings key.

            default (object):
                The default value from the form, which will be ignored,
                so that the registered siteconfig defaults will be used.

        Returns:
            object:
            The resulting value from the settings.
        """
        return self.instance.get(key)

    def set_key_value(self, key, value):
        """Set the value for a SiteConfiguration settings key.

        Args:
            key (unicode):
                The settings key.

            value (object):
                The settings value.
        """
        self.instance.set(key, value)

    def save_instance(self):
        """Save the SiteConfiguration instance."""
        self.instance.save()
