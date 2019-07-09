#
# forms.py -- Form classes useful for extensions
#
# Copyright (c) 2010-2011  Beanbag, Inc.
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

import warnings

from djblets.forms.forms import KeyValueForm
from djblets.util.decorators import cached_property


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
