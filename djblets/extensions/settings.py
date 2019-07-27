#
# settings.py -- Settings storage operations for extensions.
#
# Copyright (c) 2010-2013  Beanbag, Inc.
# Copyright (c) 2008-2010  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

from django.utils.translation import ugettext as _

from djblets.extensions.signals import settings_saved


class ExtensionSettings(dict):
    """Settings data for an extension.

    This is a glorified dictionary that acts as a proxy for the extension's
    stored settings in the database.

    Callers must call :py:meth:`save` when they want to make the settings
    persistent.

    If a key is not found in the dictionary,
    :py:attr:`Extension.default_settings
    <djblets.extensions.extension.Extension.default_settings>` will be checked
    as well.
    """

    def __init__(self, extension):
        """Initialize and load the settings.

        Args:
            extension (djblets.extensions.extension.Extension):
                The extension the settings is for.
        """
        super(ExtensionSettings, self).__init__()

        self.extension = extension
        self.load()

    def __getitem__(self, key):
        """Retrieve an item from the dictionary.

        This will attempt to return a default value from
        :py:attr:`Extension.default_settings
        <djblets.extensions.extension.Extension.default_settings>` if the
        setting has not been set.

        Args:
            key (unicode):
                The key to retrieve.

        Returns:
            object:
            The value from settings.

        Raises:
            KeyError:
                The key could not be found in stored or default settings.
        """
        if super(Settings, self).__contains__(key):
            return super(Settings, self).__getitem__(key)

        if key in self.extension.default_settings:
            return self.extension.default_settings[key]

        raise KeyError(
            _('The settings key "%(key)s" was not found in extension %(ext)s')
            % {
                'key': key,
                'ext': self.extension.id
            })

    def __contains__(self, key):
        """Return if a setting can be found.

        This will check both the stored settings and the default settings
        for the extension.

        Args:
            key (unicode):
                The key to check.

        Returns:
            bool:
            ``True`` if the setting could be found. ``False`` if it could not.
        """
        return (super(Settings, self).__contains__(key) or
                key in self.extension.default_settings)

    def get(self, key, default=None):
        """Return the value for a setting.

        This will return a value from either the stored settings, the
        extensin's default settings, or the value passed as ``default``.

        Args:
            key (unicode):
                The key to retrieve.

            default (object, optional):
                The default value, if it couldn't be found in the stored
                settings or the extension's default settings.

        Returns:
            object:
            The value for the setting.
        """
        # dict.get doesn't call __getitem__ internally, and instead looks up
        # straight from the internal dictionary data. So, we need to handle it
        # ourselves in order to support defaults through __getitem__.
        try:
            return self[key]
        except KeyError:
            return default

    def set(self, key, value):
        """Set a setting's value.

        This is equivalent to setting the value through standard dictionary
        attribute storage.

        Args:
            key (unicode):
                The key to set.

            value (object):
                The value for the setting.
        """
        self[key] = value

    def load(self):
        """Load the settings from the database."""
        try:
            self.update(self.extension.registration.settings)
        except ValueError:
            # The settings in the database are invalid. We'll have to discard
            # it. Note that this should never happen unless the user
            # hand-modifies the entries and breaks something.
            pass

    def save(self):
        """Save all current settings to the database."""
        registration = self.extension.registration
        registration.settings = dict(self)
        registration.save()

        settings_saved.send(sender=self.extension)

        # Make sure others are aware that the configuration changed.
        self.extension.extension_manager._bump_sync_gen()


#: Legacy name for ExtensionSettings.
#:
#: This is unlikely to be needed outside of the Djblets Extensions code, but
#: is available for any callers who might be dependent on it.
#:
#: Deprecated:
#:     2.0:
#:     Renamed to :py:class:`ExtensionSettings`. This will be removed in
#:     Djblets 3.0.
Settings = ExtensionSettings
