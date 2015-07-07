"""Built-in resource representing the User model."""

from __future__ import unicode_literals

from django.contrib.auth.models import User

from djblets.util.decorators import augment_method_from
from djblets.webapi.resources.base import WebAPIResource
from djblets.webapi.resources.registry import register_resource_for_model


class UserResource(WebAPIResource):
    """A default resource for representing a Django User model."""

    model = User
    fields = {
        'id': {
            'type': int,
            'description': 'The numeric ID of the user.',
        },
        'username': {
            'type': str,
            'description': "The user's username.",
        },
        'first_name': {
            'type': str,
            'description': "The user's first name.",
        },
        'last_name': {
            'type': str,
            'description': "The user's last name.",
        },
        'fullname': {
            'type': str,
            'description': "The user's full name (first and last).",
        },
        'email': {
            'type': str,
            'description': "The user's e-mail address",
        },
        'url': {
            'type': str,
            'description': "The URL to the user's page on the site. "
                           "This is deprecated and will be removed in a "
                           "future version.",
        },
    }

    uri_object_key = 'username'
    uri_object_key_regex = r'[A-Za-z0-9@\._\-\'\+]+'
    model_object_key = 'username'
    autogenerate_etags = True

    allowed_methods = ('GET',)

    def serialize_fullname_field(self, user, **kwargs):
        return user.get_full_name()

    def serialize_url_field(self, user, **kwargs):
        return user.get_absolute_url()

    def has_modify_permissions(self, request, user, *args, **kwargs):
        """Return whether or not the user can modify this object."""
        return request.user.is_authenticated() and user.pk == request.user.pk

    @augment_method_from(WebAPIResource)
    def get_list(self, *args, **kwargs):
        """Retrieve the list of users on the site."""
        pass


user_resource = UserResource()
register_resource_for_model(User, user_resource)
