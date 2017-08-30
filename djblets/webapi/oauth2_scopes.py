"""OAuth2 scope generation for WebAPI resources."""

from __future__ import unicode_literals

import logging
from collections import defaultdict, deque
from importlib import import_module

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import six
from django.utils.translation import ugettext as _

from djblets.extensions.manager import get_extension_managers
from djblets.extensions.signals import (extension_enabled,
                                        extension_disabled)
from djblets.webapi.resources.mixins.oauth2_tokens import (
    ResourceOAuth2TokenMixin)


logger = logging.getLogger(__name__)

_scopes = None


def get_scope_dictionary():
    """Return the scope dictionary.

    This method requires :setting:`WEB_API_ROOT_RESOURCE` setting to point to
    an instance of the root resource for your WebAPI. Optionally, the
    :setting:`WEB_API_SCOPE_DICT_CLASS` (defaulting to
    :py:class:`djblets.webapi.oauth2_scopes.WebAPIScopeDictionary`) can be set
    to specialize scope generation.

    If the :py:mod:`djblets.extensions` app is being used, then the
    :setting:`WEB_API_SCOPE_DICT_CLASS` setting should be set to
    :py:class:`djblets.webapi.oauth2_scopes.ExtensionEnabledWebAPIScopeDictionary`.

    Returns:
        WebAPIScopeDictionary:
        The scope dictionary.
    """
    global _scopes

    if _scopes is None:
        scopes_cls_name = getattr(
            settings, 'WEB_API_SCOPE_DICT_CLASS',
            'djblets.webapi.oauth2_scopes.WebAPIScopeDictionary')

        scopes_cls_mod, scopes_cls_attr = scopes_cls_name.rsplit('.', 1)

        try:
            scopes_cls = getattr(import_module(scopes_cls_mod),
                                 scopes_cls_attr)
        except (AttributeError, ImportError) as e:
            raise ImproperlyConfigured(
                'settings.WEB_API_SCOPE_DICT_CLASS %r could not be imported: '
                '%s'
                % (scopes_cls_name, e)
            )

        try:
            root_resource_path = getattr(settings, 'WEB_API_ROOT_RESOURCE')
        except AttributeError:
            raise ImproperlyConfigured(
                'settings.WEB_API_ROOT_RESOURCE is required.'
            )

        root_resource_mod, root_resource_attr = root_resource_path.rsplit('.',
                                                                          1)

        try:
            root_resource = getattr(import_module(root_resource_mod),
                                    root_resource_attr)
        except (AttributeError, ImportError) as e:
            raise ImproperlyConfigured(
                'settings.WEB_API_ROOT_RESOURCE %r could not be imported: %s'
                % (root_resource_path, e)
            )

        _scopes = scopes_cls.from_root(root_resource)

    return _scopes


class WebAPIScopeDictionary(dict):
    """A Web API scope dictionary.

    This class knows how to build a list of available scopes from the WebAPI
    resource tree at runtime.

    By default, it will only have to walk the API tree once, after which the
    value can be cached.
    """

    @property
    def scope_list(self):
        """The list of scopes defined by this dictionary.

        The value is cached so that it will only be recomputed when the
        dictionary is updated.
        """
        if self._dirty:
            self._scope_list = list(self)
            self._dirty = False

        return self._scope_list

    def __init__(self, *args, **kwargs):
        """Initialize the scope dictionary.

        Args:
            *args (tuple):
                Positional arguments to pass to the :py:class:`dict`
                initializer.

            **kwargs (dict):
                Keyword arguments to pass to the :py:class:`dict` initializer.
        """
        super(WebAPIScopeDictionary, self).__init__(*args, **kwargs)

        self._dirty = True
        self._scope_list = None

    def __setitem__(self, key, value):
        super(WebAPIScopeDictionary, self).__setitem__(key, value)
        self._dirty = True

    def __delitem__(self, key):
        super(WebAPIScopeDictionary, self).__delitem__(key)
        self._dirty = True

    @classmethod
    def from_root(cls, root_resource):
        """Build the scope dictionary from the given resource tree.

        Args:
            root_resource (djblets.webapi.resources.root.RootResource):
                The root of the resource tree.

        Returns:
            WebAPIScopeDictionary:
            The generated scope dictionary.
        """
        scopes = cls()
        scopes.walk_resources([root_resource])
        return scopes

    def walk_resources(self, resources):
        """Traverse the given resource trees and add the appropriate scopes.

        Args:
            resources (list of djblets.webapi.resources.base.WebAPIResource):
                The resources to generate scopes for. The children of these
                resources will also be traversed.

        Returns:
            list of unicode:
            The list of scopes added by walking the given resources.
        """
        to_walk = deque(resources)
        scopes_added = []

        while to_walk:
            resource = to_walk.popleft()

            to_walk.extend(resource.list_child_resources)
            to_walk.extend(resource.item_child_resources)

            scope_to_methods = defaultdict(set)

            if not isinstance(resource, ResourceOAuth2TokenMixin):
                logging.warning(
                    'Resource %r does not inherit from '
                    'djblets.webapi.resources.mixins.oauth2_tokens.'
                    'ResourceOAuth2TokenMixin: it will not be accessible with '
                    'OAuth2 tokens. It is recommended that all your resources '
                    'inherit from a base class that includes this mixin.',
                    type(resource),
                )
                continue

            if not resource.oauth2_token_access_allowed:
                continue

            for method in resource.allowed_methods:
                try:
                    suffix = resource.HTTP_SCOPE_METHOD_MAP[method]
                except KeyError:
                    logger.error('Unknown HTTP method %s not present in '
                                 'HTTP_SCOPE_METHOD_MAP: a scope will not be '
                                 'generated for this method.',
                                 method)
                    continue

                scope_to_methods[suffix].add(method)

            for suffix, methods in six.iteritems(scope_to_methods):
                scope_name = '%s:%s' % (resource.scope_name, suffix)

                super(WebAPIScopeDictionary, self).__setitem__(
                    scope_name,
                    _('Ability to perform HTTP %(methods)s on the %(name)s '
                      'resource')
                    % {
                        'methods': ', '.join(methods),
                        'name': resource.name,
                    }
                )
                scopes_added.append(scope_name)

        if scopes_added:
            self._dirty = True

        return scopes_added

    def __repr__(self):
        """Return a string representation of this object.

        Returns:
            unicode:
            A string representation of this object.
        """
        return '%s(%r)' % (type(self).__name__,
                           super(WebAPIScopeDictionary, self).__repr__())


class ExtensionEnabledWebAPIScopeDictionary(WebAPIScopeDictionary):
    """A Web API scopes dictionary that supports extensions.

    This scope dictionary is only required if your app is using the
    :py:mod:`djblets.extensions` app.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the scope dictionary.

        This adds signal handlers to ensure the dictionary stays up to date
         when extensions are initialized and uninitialized.

        Args:
            *args (tuple):
                Positional arguments to pass to the :py:class:`dict`
                initializer.

            **kwargs (dict):
                Keyword arguments to pass to the :py:class:`dict` initializer.
        """
        super(ExtensionEnabledWebAPIScopeDictionary, self).__init__(*args,
                                                                    **kwargs)

        self._scopes_by_ext_cls = {}

        extension_enabled.connect(self._on_extension_enabled)
        extension_disabled.connect(self._on_extension_disabled)

        for manager in get_extension_managers():
            for extension in manager.get_enabled_extensions():
                self._on_extension_enabled(extension=extension)

    def __del__(self):
        """Remove all active signal handlers."""
        extension_enabled.disconnect(self._on_extension_enabled)
        extension_disabled.disconnect(self._on_extension_disabled)

    def _on_extension_enabled(self, extension, **kwargs):
        """Traverse an extensions resource trees when it is enabled.

        Args:
            extension (djblets.extensions.extension.Extension):
                The extension class that was enabled.

            **kwargs (dict):
                Ignored keyword arguments from the signal.
        """
        scopes_added = self.walk_resources(extension.resources)

        if scopes_added:
            self._scopes_by_ext_cls[type(extension)] = scopes_added

    def _on_extension_disabled(self, extension, **kwargs):
        """Remove an extensions scopes when it is uninitialized.

        Args:
            ext_class (type):
                The extension class that was uninitialized.

            **kwargs (dict):
                Ignored keyword arguments from the signal.
        """
        try:
            scopes = self._scopes_by_ext_cls.pop(type(extension))
        except KeyError:
            return

        for scope in scopes:
            # This is intentionally referencing the dict.__delitem__ method.
            super(WebAPIScopeDictionary, self).__delitem__(scope)

        self._dirty = True


_old_oauth2_methods = {}


def enable_web_api_scopes(*args, **kwargs):
    """Enable WebAPI scopes.

    The ``oauth2_provider.settings.oauth2_settings`` object will be patched so
    that scopes are correctly cached. The cache will be lazily updated after
    the scopes are updated.

    Args:
        *args (tuple):
            Ignored positional arguments.

        **kwargs (dict):
            Ignored keyword arguments.
    """
    if '__getattr__' in _old_oauth2_methods:
        return

    scopes = settings.OAUTH2_PROVIDER['SCOPES'] = get_scope_dictionary()

    from oauth2_provider.settings import OAuth2ProviderSettings

    _old_oauth2_methods['__getattr__'] = old__getattr__ = \
        OAuth2ProviderSettings.__getattr__

    def __getattr__(self, key):
        """Get an attribute from the OAuth2 settings.

        This method handles caching the ``_SCOPES`` setting. When the
        underlying scopes dictionary is marked as dirty, we will regenerate
        the list of scopes on-demand and cache it. The cached value will be
        returned in future calls until the scopes dictionary becomes dirty
        again.

        Args:
            key (unicode):
                The key to look up.

        Returns:
            object:
            The attribute value.

        Raises:
            AttributeError:
                The attribute is not defined on the settings object.
        """
        if key == '_SCOPES':
            return scopes.scope_list
        else:
            return old__getattr__(self, key)

    OAuth2ProviderSettings.__getattr__ = __getattr__


def disable_web_api_scopes(*args, **kwargs):
    from oauth2_provider.settings import OAuth2ProviderSettings

    try:
        OAuth2ProviderSettings.__getattr__ = _old_oauth2_methods.pop(
            '__getattr__')
    except KeyError:
        pass
