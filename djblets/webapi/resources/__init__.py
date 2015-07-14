"""Deprecated module for Web API resource classes and registration.

.. deprecated:: 0.9

See the following for the new function/class locations:

* :py:class:`djblets.webapi.resources.base.WebAPIResource`
* :py:class:`djblets.webapi.resources.group.GroupResource`
* :py:data:`djblets.webapi.resources.group.group_resource`
* :py:class:`djblets.webapi.resources.root.RootResource`
* :py:class:`djblets.webapi.resources.user.UserResource`
* :py:data:`djblets.webapi.resources.user.user_resource`
* :py:func:`djblets.webapi.resources.registry.get_resource_from_class`
* :py:func:`djblets.webapi.resources.registry.get_resource_from_name`
* :py:func:`djblets.webapi.resources.registry.get_resource_for_object`
* :py:func:`djblets.webapi.resources.registry.register_resource_for_model`
* :py:func:`djblets.webapi.resources.registry.unregister_resource`
* :py:func:`djblets.webapi.resources.registry.unregister_resource_for_model`
"""

from __future__ import unicode_literals

from djblets.webapi.resources.base import WebAPIResource
from djblets.webapi.resources.group import GroupResource, group_resource
from djblets.webapi.resources.registry import (get_resource_from_class,
                                               get_resource_from_name,
                                               get_resource_for_object,
                                               register_resource_for_model,
                                               unregister_resource,
                                               unregister_resource_for_model)
from djblets.webapi.resources.root import RootResource
from djblets.webapi.resources.user import UserResource, user_resource


__all__ = [
    'GroupResource',
    'RootResource',
    'UserResource',
    'WebAPIResource',
    'get_resource_from_class',
    'get_resource_from_name',
    'get_resource_for_object',
    'register_resource_for_model',
    'unregister_resource',
    'unregister_resource_for_model',
    'group_resource',
    'user_resource',
]

__deprecated__ = __all__
