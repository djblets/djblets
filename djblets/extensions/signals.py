#
# signals.py -- Extension-related signals.
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

from django.dispatch import Signal


#: A signal fired when an extension is disabled.
#:
#: Args:
#:     extension (djblets.extensions.extension.Extension):
#:         The extension that was disabled.
extension_disabled = Signal(providing_args=['extension'])


#: A signal fired when an extension is enabled.
#:
#: Args:
#:     extension (djblets.extensions.extension.Extension):
#:         The extension that was enabled.
extension_enabled = Signal(providing_args=['extension'])


#: A signal fired when an extension is initialized.
#:
#: Args:
#:     extension (type):
#:         The extension class that was initialized.
#:
#:         This will be a subclass of
#:         :py:class:`djblets.extensions.extension.Extension`.
extension_initialized = Signal(providing_args=['ext_class'])


#: A signal fired when an extension is uninitialized.
#:
#: Args:
#:     extension (type):
#:         The extension class that was uninitialized.
#:
#:         This will be a subclass of
#:         :py:class:`djblets.extensions.extension.Extension`.
extension_uninitialized = Signal(providing_args=['ext_class'])


#: A signal fired when an extension's settings are saved.
settings_saved = Signal()
