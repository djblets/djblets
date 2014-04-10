from __future__ import unicode_literals

from django.contrib.auth.models import User, Group
from django.db.models.query import QuerySet

from djblets.util.serializers import DjbletsJSONEncoder
from djblets.webapi.core import WebAPIEncoder


class BasicAPIEncoder(WebAPIEncoder):
    """
    A basic encoder that encodes dates, times, QuerySets, Users, and Groups.
    """
    def encode(self, o, *args, **kwargs):
        if isinstance(o, QuerySet):
            return list(o)
        elif isinstance(o, User):
            return {
                'id': o.id,
                'username': o.username,
                'first_name': o.first_name,
                'last_name': o.last_name,
                'fullname': o.get_full_name(),
                'email': o.email,
                'url': o.get_absolute_url(),
            }
        elif isinstance(o, Group):
            return {
                'id': o.id,
                'name': o.name,
            }
        else:
            try:
                return DjbletsJSONEncoder().default(o)
            except TypeError:
                return None


class ResourceAPIEncoder(WebAPIEncoder):
    """An encoder that encodes objects based on registered resources."""
    def encode(self, o, *args, **kwargs):
        if isinstance(o, QuerySet):
            return list(o)
        else:
            calling_resource = kwargs.pop('calling_resource', None)

            if calling_resource:
                serializer = calling_resource.get_serializer_for_object(o)
            else:
                from djblets.webapi.resources import get_resource_for_object

                serializer = get_resource_for_object(o)

            if serializer:
                return serializer.serialize_object(o, *args, **kwargs)
            else:
                try:
                    return DjbletsJSONEncoder().default(o)
                except TypeError:
                    return None
