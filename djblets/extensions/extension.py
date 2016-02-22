#
# extension.py -- Base classes for extensions
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

import inspect
import os

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import get_mod_func
from django.utils.encoding import python_2_unicode_compatible

from djblets.extensions.settings import Settings


class JSExtension(object):
    """Base class for a JavaScript extension.

    This can be subclassed to provide the information needed to initialize
    a JavaScript extension.

    The JSExtension subclass is expected to define a :py:attr:`model_class`
    attribute naming its JavaScript counterpart. This would be the variable
    name for the (uninitialized) model for the extension, defined in a
    JavaScript bundle.

    It may also define :py:attr:`apply_to`, which is a list of URL names that
    the extension will be initialized on. If not provided, the extension will
    be initialized on all pages.

    To provide additional data to the model instance, the JSExtension subclass
    can implement :py:meth:`get_model_data` and return a dictionary of data
    to pass. You may also override the :py:meth`get_settings` method to return,
    a dict of settings to the :py:class:`model_class`. By default, the
    associated extension's settings are returned.
    """
    model_class = None
    apply_to = None

    def __init__(self, extension):
        self.extension = extension

    def applies_to(self, url_name):
        """Returns whether this extension applies to the given URL name."""
        return self.apply_to is None or url_name in self.apply_to

    def get_model_data(self):
        """Returns model data for the Extension model instance in JavaScript.

        Subclasses can override this to return custom data to pass to
        the extension.
        """
        return {}

    def get_settings(self):
        """Return the settings for the JS Extension.

        By default, this is the associated :py:class:`Extension` object's
        settings. Subclasses may override this method to provide different
        settings.

        These settings will be provided to the :py:attr:`model_class` as a
        ``settings`` key in its initialization options.

        Returns:
            dict:
            The extension settings.
        """
        return self.extension.settings


class Extension(object):
    """Base class for an extension.

    Extensions must subclass this class. They'll automatically have support for
    settings, adding hooks, and plugging into the administration UI.

    For information on writing extensions, see :ref:`writing-extensions`.
    """

    metadata = None
    is_configurable = False
    default_settings = {}
    has_admin_site = False
    requirements = []
    resources = []
    apps = []
    context_processors = []
    middleware = []

    css_bundles = {}
    js_bundles = {}

    js_extensions = []

    def __init__(self, extension_manager):
        self.extension_manager = extension_manager
        self.hooks = set()
        self.settings = Settings(self)
        self.admin_site = None
        self.middleware_instances = []

        for middleware_cls in self.middleware:
            # We may be loading in traditional middleware (which doesn't take
            # any parameters in the constructor), or special Extension-aware
            # middleware (which takes an extension parameter). We need to
            # try to introspect and figure out what it is.
            try:
                arg_spec = inspect.getargspec(middleware_cls.__init__)
            except (AttributeError, TypeError):
                # There's no custom __init__ here. It may not exist
                # in the case of an old-style object, in which case we'll
                # get an AttributeError. Or, it may be a new-style object
                # with no custom __init__, in which case we'll get a TypeError.
                arg_spec = None

            if arg_spec and len(arg_spec) >= 2 and arg_spec[1] == 'extension':
                middleware_instance = middleware_cls(self)
            else:
                middleware_instance = middleware_cls()

            self.middleware_instances.append(middleware_instance)

        self.initialize()

    def initialize(self):
        """Initializes the extension.

        Subclasses can override this to provide any custom initialization.
        They do not need to call the parent function, as it does nothing.
        """
        pass

    def shutdown(self):
        """Shuts down the extension.

        By default, this calls shutdown_hooks.

        Subclasses should override this if they need custom shutdown behavior.
        """
        self.shutdown_hooks()

    def shutdown_hooks(self):
        """Shuts down all hooks for the extension."""
        for hook in self.hooks:
            if hook.initialized:
                hook.shutdown()

    def _get_admin_urlconf(self):
        if not hasattr(self, "_admin_urlconf_module"):
            try:
                name = "%s.%s" % (get_mod_func(self.__class__.__module__)[0],
                                  "admin_urls")
                self._admin_urlconf_module = __import__(name, {}, {}, [''])
            except Exception as e:
                raise ImproperlyConfigured(
                    "Error while importing extension's admin URLconf %r: %s" %
                    (name, e))

        return self._admin_urlconf_module
    admin_urlconf = property(_get_admin_urlconf)

    def get_bundle_id(self, name):
        """Returns the ID for a CSS or JavaScript bundle."""
        return '%s-%s' % (self.id, name)


@python_2_unicode_compatible
class ExtensionInfo(object):
    """Information on an extension.

    This class stores the information and metadata on an extension. This
    includes the name, version, author information, where it can be downloaded,
    whether or not it's enabled or installed, and anything else that may be
    in the Python package for the extension.
    """
    def __init__(self, entrypoint, ext_class):
        metadata = {}

        for line in entrypoint.dist.get_metadata_lines("PKG-INFO"):
            key, value = line.split(": ", 1)

            if value != "UNKNOWN":
                metadata[key] = value

        # Extensions will often override "Name" to be something
        # user-presentable, but we sometimes need the package name
        self.package_name = metadata.get('Name')

        if ext_class.metadata is not None:
            metadata.update(ext_class.metadata)

        self.metadata = metadata
        self.name = metadata.get('Name')
        self.version = metadata.get('Version')
        self.summary = metadata.get('Summary')
        self.description = metadata.get('Description')
        self.author = metadata.get('Author')
        self.author_email = metadata.get('Author-email')
        self.license = metadata.get('License')
        self.url = metadata.get('Home-page')
        self.author_url = metadata.get('Author-home-page', self.url)
        self.app_name = '.'.join(ext_class.__module__.split('.')[:-1])
        self.enabled = False
        self.installed = False
        self.is_configurable = ext_class.is_configurable
        self.has_admin_site = ext_class.has_admin_site
        self.installed_htdocs_path = \
            os.path.join(settings.MEDIA_ROOT, 'ext', self.package_name)
        self.installed_static_path = \
            os.path.join(settings.STATIC_ROOT, 'ext', ext_class.id)

    def __str__(self):
        return "%s %s (enabled = %s)" % (self.name, self.version, self.enabled)
