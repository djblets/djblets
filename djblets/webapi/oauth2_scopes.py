"""OAuth2 scope generation for WebAPI resources."""

from __future__ import unicode_literals

import logging
import threading
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

_enable_lock = threading.Lock()
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

        _scopes = scopes_cls(root_resource)

    return _scopes


class WebAPIScopeDictionary(object):
    """A Web API scope dictionary.

    This class knows how to build a list of available scopes from the WebAPI
    resource tree at runtime.

    By default, it will only have to walk the API tree once, after which the
    value can be cached.
    """

    def __init__(self, root_resource):
        """Initialize the scope dictionary.

        Args:
            root_resource (djblets.webapi.resources.base.WebAPIResource):
                The root resource to walk in order to build scopes.
        """
        self.resource_trees = {root_resource}
        self._update_lock = threading.Lock()
        self._scope_dict = {}

    @property
    def scope_dict(self):
        """The dictionary of scopes defined by this dictionary.

        The value is cached so that it will only be recomputed when the
        dictionary is updated.
        """
        if not self._scope_dict:
            with self._update_lock:
                if not self._scope_dict:
                    self._walk_resources(self.resource_trees)

                    assert self._scope_dict

        return self._scope_dict

    def iterkeys(self):
        """Iterate through all keys in the dictionary.

        This is used by oauth2_provider when on Python 2.x to get the list
        of scope keys.

        Yields:
            unicode:
            The key for each scope.
        """
        return self.scope_dict.iterkeys()

    def keys(self):
        """Iterate through all keys in the dictionary.

        This is used by oauth2_provider when on Python 3.x to get the list
        of scope keys.

        Yields:
            unicode:
            The key for each scope.
        """
        return six.iterkeys(self.scope_dict)

    def clear(self):
        """Clear all scopes from the dictionary.

        The next attempt at fetching scopes will repopulate the dictionary
        from scratch.
        """
        self._scope_dict.clear()

    def _walk_resources(self, resources):
        """Traverse the given resource trees and add the appropriate scopes.

        Args:
            resources (list of djblets.webapi.resources.base.WebAPIResource):
                The resources to generate scopes for. The children of these
                resources will also be traversed.

        Returns:
            list of unicode:
            The list of scopes added by walking the given resources.
        """
        for resource in resources:
            self._walk_resources(resource.list_child_resources)
            self._walk_resources(resource.item_child_resources)

            scope_to_methods = defaultdict(list)

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

                scope_to_methods[suffix].append(method)

            for suffix, methods in six.iteritems(scope_to_methods):
                scope_name = '%s:%s' % (resource.scope_name, suffix)

                self._scope_dict[scope_name] = (
                    _('Ability to perform HTTP %(methods)s on the %(name)s '
                      'resource')
                    % {
                        'methods': ', '.join(sorted(methods)),
                        'name': resource.name,
                    }
                )

    def __getitem__(self, key):
        """Return the description of a given scope.

        Args:
            key (unicode):
                The scope's key.

        Returns:
            unicode:
            The scope's description.

        Raises:
            KeyError:
                The scope's key was not in the dictionary.
        """
        return self.scope_dict[key]

    def __contains__(self, key):
        """Return whether the dictionary has a particular scope.

        Args:
            key (unicode):
                The scope's key.

        Returns:
            bool:
            ``True`` if the scope is in the dictionary.
        """
        return key in self.scope_dict

    def __repr__(self):
        """Return a string representation of this object.

        Returns:
            unicode:
            A string representation of this object.
        """
        return '%s(%r)' % (type(self).__name__,
                           list(six.iterkeys(self.scope_dict)))


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
                Positional arguments to pass to the parent class.

            **kwargs (dict):
                Keyword arguments to pass to the the parent class.
        """
        super(ExtensionEnabledWebAPIScopeDictionary, self).__init__(*args,
                                                                    **kwargs)

        extension_enabled.connect(self._on_extension_enabled)
        extension_disabled.connect(self._on_extension_disabled)

        for manager in get_extension_managers():
            for extension in manager.get_enabled_extensions():
                self._on_extension_enabled(extension=extension)

    def _on_extension_enabled(self, extension, **kwargs):
        """Traverse an extensions resource trees when it is enabled.

        Args:
            extension (djblets.extensions.extension.Extension):
                The extension class that was enabled.

            **kwargs (dict):
                Ignored keyword arguments from the signal.
        """
        if extension.resources:
            self.resource_trees.update(extension.resources)
            self.clear()

    def _on_extension_disabled(self, extension, **kwargs):
        """Remove an extensions scopes when it is uninitialized.

        Args:
            ext_class (type):
                The extension class that was uninitialized.

            **kwargs (dict):
                Ignored keyword arguments from the signal.
        """
        if extension.resources:
            self.resource_trees.difference_update(extension.resources)
            self.clear()


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
    with _enable_lock:
        if not isinstance(settings.OAUTH2_PROVIDER['SCOPES'],
                          WebAPIScopeDictionary):
            settings.OAUTH2_PROVIDER['SCOPES'] = get_scope_dictionary()
