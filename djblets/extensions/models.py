#
# models.py -- Extension models.
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

from django.db import models

from djblets.extensions.errors import InvalidExtensionError
from djblets.util.fields import JSONField


class RegisteredExtension(models.Model):
    """Extension registration info.

    An extension that was both installed and enabled at least once. This
    may contain settings for the extension.

    This does not contain full information for the extension, such as the
    author or description. That is provided by the Extension object itself.
    """
    class_name = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=32)
    enabled = models.BooleanField(default=False)
    installed = models.BooleanField(default=False)
    settings = JSONField()

    def __unicode__(self):
        return self.name

    def get_extension_class(self):
        """Retrieves the python object for the extensions class."""
        try:
            # Import the function here to avoid a mutual
            # dependency.
            from djblets.extensions.base import get_extension_managers
        except:
            return None

        managers = get_extension_managers()
        for manager in managers:
            try:
                extension = manager.get_installed_extension(self.class_name)
                return extension
            except InvalidExtensionError:
                continue

        return None
