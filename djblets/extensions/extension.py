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
import locale
import logging
import os
import warnings
from email.parser import FeedParser

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import get_mod_func
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext as _

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

    encodings = ['utf-8', locale.getpreferredencoding(False), 'latin1']

    @classmethod
    def create_from_entrypoint(cls, entrypoint, ext_class):
        """Create a new ExtensionInfo from a Python EntryPoint.

        This will pull out information from the EntryPoint and return a new
        ExtensionInfo from it.

        It handles pulling out metadata from the older :file:`PKG-INFO` files
        and the newer :file:`METADATA` files.

        Args:
            entrypoint (pkg_resources.EntryPoint):
                The EntryPoint pointing to the extension class.

            ext_class (type):
                The extension class (subclass of :py:class:`Extension`).

        Returns:
            ExtensionInfo:
            An ExtensionInfo instance, populated with metadata from the
            package.
        """
        metadata = cls._get_metadata_from_entrypoint(entrypoint, ext_class.id)

        return cls(ext_class=ext_class,
                   package_name=metadata.get('Name'),
                   metadata=metadata)

    @classmethod
    def _get_metadata_from_entrypoint(cls, entrypoint, extension_id):
        """Return metadata information from an entrypoint.

        This is used internally to parse and validate package information from
        an entrypoint for use in ExtensionInfo.

        Args:
            entrypoint (pkg_resources.EntryPoint):
                The EntryPoint pointing to the extension class.

            extension_id (unicode):
                The extension's ID.

        Returns:
            dict:
            The resulting metadata dictionary.
        """
        dist = entrypoint.dist

        try:
            # Wheel, or other modern package.
            lines = dist.get_metadata_lines('METADATA')
        except IOError:
            try:
                # Egg, or other legacy package.
                lines = dist.get_metadata_lines('PKG-INFO')
            except IOError:
                lines = []
                logging.error('No METADATA or PKG-INFO found for the package '
                              'containing the %s extension. Information on '
                              'the extension may be missing.',
                              extension_id)

        data = '\n'.join(lines)

        # Try to decode the PKG-INFO content. If no decoding method is
        # successful then the PKG-INFO content will remain unchanged and
        # processing will continue with the parsing.
        for enc in cls.encodings:
            try:
                data = data.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            logging.warning(
                'Failed decoding PKG-INFO content for extension %s',
                entrypoint.name)

        p = FeedParser()
        p.feed(data)
        pkg_info = p.close()

        return dict(pkg_info.items())

    def __init__(self, ext_class, package_name, metadata={}):
        """Instantiate the ExtensionInfo using metadata and an extension class.

        This will set information about the extension based on the metadata
        provided by the caller and the extension class itself.

        Args:
            ext_class (type):
                The extension class (subclass of :py:class:`Extension`).

            package_name (unicode):
                The package name owning the extension.

            metadata (dict, optional):
                Optional metadata for the extension. If the extension provides
                its own metadata, that will take precedence.

        Raises:
            TypeError:
                The parameters passed were invalid (they weren't a new-style
                call or a legacy entrypoint-related call).
        """
        try:
            issubclass(ext_class, Extension)
        except TypeError:
            try:
                is_entrypoint = (hasattr(ext_class, 'dist') and
                                 issubclass(package_name, Extension))
            except TypeError:
                is_entrypoint = False

            if is_entrypoint:
                # These are really (probably) an entrypoint and class,
                # respectively. Fix up the variables.
                entrypoint, ext_class = ext_class, package_name

                metadata = self._get_metadata_from_entrypoint(entrypoint,
                                                              ext_class.id)
                package_name = metadata.get('Name')

                # Warn after the above. Something about the above calls cause
                # warnings to be reset.
                warnings.warn(
                    'ExtensionInfo.__init__() no longer accepts an '
                    'EntryPoint. Please update your code to call '
                    'ExtensionInfo.create_from_entrypoint() instead.',
                    DeprecationWarning)
            else:
                logging.error('Unexpected parameters passed to '
                              'ExtensionInfo.__init__: ext_class=%r, '
                              'package_name=%r, metadata=%r',
                              ext_class, package_name, metadata)

                raise TypeError(
                    _('Invalid parameters passed to ExtensionInfo.__init__'))

        # Set the base information from the extension and the package.
        self.package_name = package_name
        self.app_name = '.'.join(ext_class.__module__.split('.')[:-1])
        self.is_configurable = ext_class.is_configurable
        self.has_admin_site = ext_class.has_admin_site
        self.installed_htdocs_path = \
            os.path.join(settings.MEDIA_ROOT, 'ext', self.package_name)
        self.installed_static_path = \
            os.path.join(settings.STATIC_ROOT, 'ext', ext_class.id)

        # State set by ExtensionManager.
        self.enabled = False
        self.installed = False
        self.requirements = []

        # Set information from the provided metadata.
        if ext_class.metadata is not None:
            metadata.update(ext_class.metadata)

        self.metadata = metadata
        self.name = metadata.get('Name', package_name)
        self.version = metadata.get('Version')
        self.summary = metadata.get('Summary')
        self.description = metadata.get('Description')
        self.author = metadata.get('Author')
        self.author_email = metadata.get('Author-email')
        self.license = metadata.get('License')
        self.url = metadata.get('Home-page')
        self.author_url = metadata.get('Author-home-page', self.url)

    def __str__(self):
        return "%s %s (enabled = %s)" % (self.name, self.version, self.enabled)
