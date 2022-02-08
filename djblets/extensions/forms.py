"""Form definitions for extensions."""

from djblets.forms.forms import KeyValueForm


class SettingsForm(KeyValueForm):
    """Settings form for extension configuration.

    A base form for loading/saving settings for an extension. This is meant
    to be overridden by extensions to provide configuration pages. Any fields
    defined by the form will be loaded and saved automatically.
    """

    def __init__(self, extension, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.extension = extension
        self.settings = extension.settings

        super(SettingsForm, self).__init__(instance=extension.settings,
                                           *args, **kwargs)

    def set_key_value(self, key, value):
        """Set the value for an extension settings key.

        Args:
            key (unicode):
                The settings key.

            value (object):
                The settings value.
        """
        self.instance.set(key, value)

    def save_instance(self):
        """Save the instance."""
        self.instance.save()
