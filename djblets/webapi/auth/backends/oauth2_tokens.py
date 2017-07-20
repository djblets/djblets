"""Web API support for OAuth2 authentication."""

from __future__ import unicode_literals

import logging
from importlib import import_module

from django.core.exceptions import ImproperlyConfigured

from djblets.webapi.auth.backends.base import WebAPIAuthBackend


logger = logging.getLogger(__name__)


class OAuth2TokenBackendMixin(object):
    """A authentication backend mixin for OAuth2 tokens.

    This is similar to :py:class:`oauth2_provider.backends.OAuth2Backend`
    except it adds an extension point (:py:meth:`verify_request`) for
    sub-classes using this mixin to add additional verification.

    .. seealso:: :py:class:`oauth2_provider.backends.OAuth2Backend`, which this
                 implementation is based off of.
    """

    def authenticate(self, **credentials):
        """Attempt to authenticate a request.

        Args:
            **credentials (dict):
                The credentials for authentication.

        Returns:
            django.contrib.auth.models.User:
            If authentication succeeds, the user that authenticated, otherwise
            ``None``.
        """
        request = credentials.get('request')

        if request is None:
            return None

        try:
            from oauth2_provider.oauth2_backends import get_oauthlib_core
        except ImportError:
            raise ImproperlyConfigured(
                'WebAPIOAuth2TokenAuthBackend requires django-oauth-toolkit'
                '>=0.9,<0.9.999.'
            )

        oauthlib_core = get_oauthlib_core()
        valid, r = oauthlib_core.verify_request(request, scopes=[])

        if valid and self.verify_request(request, r.access_token, r.user):
            request._oauth2_token = r.access_token
            request.session['oauth2_token_id'] = r.access_token.pk
            return r.user

        return None

    def verify_request(self, request, token, user):
        """Perform additional request verification.

        This method can be overrided by subclasses to perform additional
        verification (e.g., against a custom Application model that can be
        enabled or disabled).

        Args:
            request (django.http.HttpRequest):
                The current HTTP request.

            token (oauth2_provider.models.AccessToken):
                The access token being used.

            user (django.contrib.auth.models.User):
                The user who is authenticating.
        """
        return True


class WebAPIOAuth2TokenAuthBackend(WebAPIAuthBackend):
    """A WebAPI auth backend for handling OAuth2 tokens."""

    def get_credentials(self, request):
        """Return the credentials for authorization.

        This will parse the :mailheader:`Authorization` header and retrieve the
        OAuth2 token code.

        This ensures that we only accept OAuth2 tokens provided in the headers
        and not in the request body.

        Args:
            request (django.htttp.HttpRequest):
                The current HTTP request.

        Returns:
            dict:
            Either the OAuth2 token code, or ``None`` if it could not be parsed
            or was not present.
        """
        try:
            import_module('oauth2_provider')
        except ImportError:
            raise ImproperlyConfigured(
                'WebAPIOAuth2TokenAuthBackend requires django-oauth-toolkit'
                '>=0.9,<0.9.999.'
            )

        http_auth = request.META['HTTP_AUTHORIZATION']
        parts = http_auth.split(' ')

        if parts[0] != 'Bearer':
            return None
        elif len(parts) != 2:
            logger.error('Invalid HTTP Authorization header: %s', http_auth)
            return None

        return {}
