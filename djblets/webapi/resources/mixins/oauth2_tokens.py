"""Web API resource support for OAuth2 token access."""

from __future__ import unicode_literals

from django.contrib import auth
from django.core.exceptions import ImproperlyConfigured

from djblets.db.query import get_object_or_none
from djblets.webapi.errors import (LOGIN_FAILED,
                                   NOT_LOGGED_IN,
                                   OAUTH_ACCESS_DENIED_ERROR,
                                   OAUTH_MISSING_SCOPE_ERROR)


class ResourceOAuth2TokenMixin(object):
    """Augments a WebAPIResource to support OAuth2 tokens.

    Any WebAPIResource subclass making use of this mixin can accept requests
    backed by an OAuth2 token and will restrict the request to that token's
    allowed scopes.

    It is recommended that all resources in a project inherit from a base
    resource that inherits both from this mixin and from WebAPIResource.
    """

    #: Whether or not this resource is accessible when using an OAuth2 token.
    oauth2_token_access_allowed = True

    #: A mapping of HTTP methods to the type of scope required.
    #:
    #: These will be used with :py:attr:`scope_name` to generate the full
    #: required scope, e.g. :samp:`{scope_name}:read`.
    HTTP_SCOPE_METHOD_MAP = {
        'DELETE': 'destroy',
        'GET': 'read',
        'HEAD': 'read',
        'OPTIONS': 'read',
        'POST': 'write',
        'PUT': 'write',
    }

    @property
    def scope_name(self):
        """The ID used for required scopes.

        This defaults to the name of the resource, but can be overridden
        in case the name is not specific enough or there's a conflict.

        If the resource allows WebAPI tokens in addition to OAuth2 tokens, this
        will default to the resource's policy ID (which defaults to its name).
        """
        if hasattr(self, 'policy_id'):
            return self.policy_id

        return self.name

    def call_method_view(self, request, method, view, *args, **kwargs):
        """Check token scopes and call the API method handler.

        Args:
            request (django.http.HttpRequest):
                The current HTTP request.

            method (unicode):
                The HTTP method of the request.

            view (callable):
                The view function to call.

            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            object:
            One of the following:

            * An error (:py:class:`djblets.webapi.errors.WebAPIError`).
            * A web API response
              (:py:class:`djblets.webapi.responces.WebAPIResponse`).
            * A tuple containing an HTTP status code and a body to serialize
              (:py:class:`tuple`).
        """
        token, from_session = self.__get_oauth2_token_for_request(request)

        if token is not None:
            if token.is_expired():
                if from_session:
                    return NOT_LOGGED_IN
                else:
                    return LOGIN_FAILED

            elif not self.oauth2_token_access_allowed:
                return OAUTH_ACCESS_DENIED_ERROR

            elif not self.__is_resource_method_allowed(method, token):
                return OAUTH_MISSING_SCOPE_ERROR

        return super(ResourceOAuth2TokenMixin, self).call_method_view(
            request, method, view, *args, **kwargs)

    def __get_oauth2_token_for_request(self, request):
        """Return the OAuth2 token for the request.

        Args:
            request (django.http.HttpRequest):
                The current HTTP request.

        Returns:
            tuple:
            A 2-tuple of the following:

            * the access token, if it exists
              (:py:class:`~oauth2_provider.models.AccessToken`); and
            * whether or not the token was retrieved from the session
              (:py:class:`bool`).
        """
        try:
            from oauth2_provider.models import AccessToken
        except ImportError:
            raise ImproperlyConfigured(
                'WebAPIOAuth2TokenAuthBackend requires django-oauth-toolkit'
                '>=0.9,<0.9.999.'
            )

        token = getattr(request, '_oauth2_token', None)
        from_session = False

        if not token:
            token_pk = request.session.get('oauth2_token_id')

            if token_pk:
                from_session = True
                token = get_object_or_none(AccessToken, pk=token_pk)

                if not token or token.is_expired():
                    # Either the token no longer exists or has expired, so we
                    # must log the user out.
                    auth.logout(request)

                request._oauth2_token = token

        return token, from_session

    def __is_resource_method_allowed(self, method, token):
        """Determine if the given method is allowed by the token.

        Args:
            method (unicode):
                The HTTP method.

            token (oauth2_provider.models.AccessToken):
                The token to check for permission.

        Returns:
            bool:
            Whether or not the token has the required scopes to perform the
            given method against this resource.
        """
        suffix = self.HTTP_SCOPE_METHOD_MAP.get(method)

        if not suffix:
            return False

        required_scope = '%s:%s' % (self.scope_name, suffix)
        return token.allow_scopes([required_scope])
