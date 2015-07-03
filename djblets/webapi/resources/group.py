"""Built-in resource representing the Group model."""

from __future__ import unicode_literals

from django.contrib.auth.models import Group

from djblets.webapi.resources.base import WebAPIResource
from djblets.webapi.resources.registry import register_resource_for_model


class GroupResource(WebAPIResource):
    """A default resource for representing a Django Group model."""

    model = Group
    fields = ('id', 'name')

    uri_object_key = 'group_name'
    uri_object_key_regex = r'[A-Za-z0-9_\-]+'
    model_object_key = 'name'
    autogenerate_etags = True

    allowed_methods = ('GET',)


group_resource = GroupResource()
register_resource_for_model(Group, group_resource)
