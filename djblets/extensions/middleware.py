#
# middleware.py -- Middleware for extensions.
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

from djblets.extensions.base import get_extension_managers


class ExtensionsMiddleware(object):
    """Middleware to manage extension lifecycles and data."""
    def process_request(self, request):
        self._check_expired()

    def process_view(self, request, view, args, kwargs):
        request._djblets_extensions_kwargs = kwargs

    def _check_expired(self):
        """Checks each ExtensionManager for expired extension state.

        When the list of extensions on an ExtensionManager changes, or when
        the configuration of an extension changes, any other threads/processes
        holding onto extensions and configuration will go stale. This function
        will check each of those to see if they need to re-load their
        state.

        This is meant to be called before every HTTP request.
        """
        for extension_manager in get_extension_managers():
            if extension_manager.is_expired():
                extension_manager.load(full_reload=True)
