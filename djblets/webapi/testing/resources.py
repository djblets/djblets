"""Utilities for generating resource trees for testing."""

from collections import namedtuple

from djblets.extensions.resources import (
    ExtensionResource as BaseExtensionResource)
from djblets.webapi.resources import WebAPIResource
from djblets.webapi.resources.root import RootResource as BaseRootResource


ResourceTree = namedtuple('ResourceTree',
                          ('base_resource', 'root_resource', 'resources'))


def make_resource_tree(mixins=None, extension_manager=None,
                       allow_anonymous_access=True):
    """Create and return a generated resource tree.

    Args:
        mixins (list of type):
            A list of mixin classes for the resources.

        extension_manager (djblets.extensions.manager.ExtensionManager,
                           optional):
            An optional extension manager. If this is provided, the generated
            tree will have an extension resource.

        allow_anonymous_access (bool, optional):
            Whether or not anonymous access should be allowed.

    Returns:
        ResourceTree:
        The generated resource tree.
    """
    if mixins is None:
        mixins = []

    bases = tuple(mixins + [WebAPIResource])

    def has_access_permissions(self, request, *args, **kwargs):
        return allow_anonymous_access or request.user.is_authenticated()

    base_resource = type('BaseResource', bases, {
        'has_access_permissions': has_access_permissions,
    })

    resources = []

    if extension_manager:
        class ExtensionResource(base_resource, BaseExtensionResource):
            pass

        resources.append(ExtensionResource(extension_manager))

    class ItemChildResource(base_resource):
        """An item child resource."""

        name = 'item-child'
        allowed_methods = ('GET', 'POST', 'PUT')

    class ForbiddenResource(base_resource):
        """A resource that cannot be accessed via OAuth2 or API tokens."""

        name = 'forbidden'
        singleton = True
        allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
        oauth2_token_access_allowed = False
        api_token_access_allowed = False

    class ListChildResource(base_resource):
        """A list child resource."""

        name = 'list-child'
        allowed_methods = ('GET', 'DELETE')

    class ParentResource(base_resource):
        """A resource with two children."""

        name = 'parent'
        allowed_methods = ('GET',)

        item_child_resources = [ItemChildResource()]
        list_child_resources = [ListChildResource()]

    resources.extend([
        ParentResource(),
        ForbiddenResource(),
    ])

    class RootResource(base_resource, BaseRootResource):
        """The root of the resource tree."""

        def __init__(self, *args, **kwargs):
            super(RootResource, self).__init__(resources, *args, **kwargs)

    return ResourceTree(
        base_resource=base_resource,
        root_resource=RootResource(resources),
        resources=resources,
    )
