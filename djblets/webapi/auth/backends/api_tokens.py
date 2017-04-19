"""Authentication support for using API tokens.

This provides two classes needed for integrating API token support.

:py:class:`TokenAuthBackendMixin` must be subclassed or mixed into an
authentication backend and registered in
:django:setting:`AUTHENTICATION_BACKENDS`.

:py:class:`WebAPITokenAuthBackend` must then be added to the API authentication
list at ``settings.WEB_API_AUTH_BACKENDS``.
"""

from __future__ import unicode_literals

import logging

from djblets.webapi.auth import WebAPIAuthBackend


logger = logging.getLogger(__name__)


class TokenAuthBackendMixin(object):
    """Mixin for a standard auth backend for API token authentication.

    This will handle authenticating users and their API tokens for API
    requests. It's only used for API requests that specify a username and a
    token.

    This class is meant to be subclassed and mixed in to another auth backend.
    Subclasses must define :py:attr:`api_token_model`.
    """

    #: The API token model to use for any token lookups.
    api_token_model = None

    def authenticate(self, token=None, **kwargs):
        """Authenticate a user, given a token ID.

        Args:
            token (unicode): The API token ID to authenticate with.

        Returns:
            User:
            The resulting user, if a token matched, or ``None`` otherwise.
        """
        if not token:
            return None

        # Find the WebAPIToken matching the token parameter passed in.
        # Once we have it, we'll need to perform some additional checks on
        # the user.
        q = self.api_token_model.objects.filter(token=token)
        q = q.select_related('user')

        try:
            webapi_token = q.get()
        except self.api_token_model.DoesNotExist:
            return None

        user = webapi_token.user

        if not user.is_active:
            return None

        # Store this temporarily. We'll be using it to store some session
        # state.
        user._webapi_token = webapi_token

        return user


class WebAPITokenAuthBackend(WebAPIAuthBackend):
    """Authenticates users using their generated API token.

    This will check the ``HTTP_AUTHORIZATION`` header for a ``token <token>``
    value. If found, it will attempt to find the user that owns the
    token, and authenticate that user.
    """

    def get_credentials(self, request):
        """Return credentials for the token.

        If the request is attempting to authenticate with a token, this
        will return a dictionary containing the token in a ``token`` key.

        Args:
            request (HttpRequest): The HTTP request from the client.

        Returns:
            dict:
            A dictionary containing the token in a ``token`` key, if the
            client requested a token for authentication.
        """
        http_auth = request.META['HTTP_AUTHORIZATION']
        parts = http_auth.split(' ')

        if parts[0] != 'token':
            return None

        if len(parts) != 2:
            logger.warning('WebAPITokenAuthBackend: Missing token in '
                           'HTTP_AUTHORIZATION header %s',
                           http_auth, extra={'request': request})
            return None

        return {
            'token': parts[1],
        }

    def login_with_credentials(self, request, **credentials):
        """Log the user in with the given credentials.

        This performs the standard authentication operations, and then
        stores some session state for any restrictions specified by the
        token.

        Args:
            request (HttpRequest):
                The HTTP request from the client.

            credentials (dict):
                The credentials data from the request.

        Returns:
            tuple or None:
            See the return type in :py:meth:`WebAPIAuthBackend.authenticate`.
        """
        result = super(WebAPITokenAuthBackend, self).\
            login_with_credentials(request, **credentials)

        if result[0]:
            user = request.user
            webapi_token = user._webapi_token
            del user._webapi_token

            request.session['webapi_token_id'] = webapi_token.pk
            request._webapi_token = webapi_token

        return result
