from __future__ import unicode_literals

import datetime

from django.contrib.auth.models import User, Group
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.query import QuerySet

from djblets.webapi.core import WebAPIEncoder


def encode_datetime(o):
    """Encode datetime objects.

    Like DjangoJSONEncoder's datetime encoding implementation, but filters out
    milliseconds in addition to microseconds.
    """
    r = o.isoformat()
    if o.microsecond:
        r = r[:19] + r[26:]
    if r.endswith('+00:00'):
        r = r[:-6] + 'Z'
    return r


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
        elif isinstance(o, datetime.datetime):
            return encode_datetime(o)
        else:
            try:
                return DjangoJSONEncoder().default(o)
            except TypeError:
                return None


class ResourceAPIEncoder(WebAPIEncoder):
    """An encoder that encodes objects based on registered resources."""
    def encode(self, o, *args, **kwargs):
        from djblets.webapi.resources import get_resource_for_object

        resource = get_resource_for_object(o)

        if isinstance(o, QuerySet):
            return list(o)
        elif resource:
            return resource.serialize_object(o, *args, **kwargs)
        elif isinstance(o, datetime.datetime):
            return encode_datetime(o)
        else:
            try:
                return DjangoJSONEncoder().default(o)
            except TypeError:
                return None
