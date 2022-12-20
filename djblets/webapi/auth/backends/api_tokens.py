"""Authentication support for using API tokens.

This provides two classes needed for integrating API token support.

:py:class:`TokenAuthBackendMixin` must be subclassed or mixed into an
authentication backend and registered in
:django:setting:`AUTHENTICATION_BACKENDS`.

:py:class:`WebAPITokenAuthBackend` must then be added to the API authentication
list at ``settings.WEB_API_AUTH_BACKENDS``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Type

from django.contrib.auth import get_backends
from django.http import HttpRequest
from django.utils import timezone
from django.utils.formats import localize
from django.utils.translation import gettext as _
from typing_extensions import Protocol, TypedDict, runtime_checkable

from djblets.webapi.auth.backends.base import (WebAPIAuthenticateResult,
                                               WebAPIAuthBackend,
                                               WebAPIGetCredentialsResult)
from djblets.webapi.errors import LOGIN_FAILED
from djblets.webapi.models import BaseWebAPIToken
from djblets.webapi.responses import WebAPIResponseHeaders
from djblets.webapi.signals import webapi_token_expired


logger = logging.getLogger(__name__)


class TokenAuthValidateResult(TypedDict):
    """The result of token validation on a Django auth backend.

    Version Added:
        3.2
    """

    #: The error message to return if authentication failed.
    #:
    #: This can be ``None`` if it succeeded, or if it failed and the default
    #: error from :py:data:`~djblets.webapi.errors.LOGIN_FAILED` should be
    #: used.
    error_message: Optional[str]

    #: Any HTTP headers to return in the response.
    #:
    #: This can be ``None`` if no headers need to be returned, or if it
    #: failed and default headers from
    #: :py:data:`~djblets.webapi.errors.LOGIN_FAILED` should be used.
    headers: Optional[WebAPIResponseHeaders]


@runtime_checkable
class ValidateTokenAuthBackend(Protocol):
    """Protocol representing auth backends supporting token validation.

    Version Added:
        3.2
    """

    def validate_token(
        self,
        request: HttpRequest,
        token: str,
    ) -> Optional[TokenAuthValidateResult]:
        """Validate a token for authentication.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            token (str):
                The token to validate. This may be ``None``.
        """
        ...


class TokenAuthBackendMixin:
    """Mixin for a standard auth backend for API token authentication.

    This will handle authenticating users and their API tokens for API
    requests. It's only used for API requests that specify a username and a
    token.

    This class is meant to be subclassed and mixed in to another Django
    auth backend (note: not a
    :py:class:`~djblets.webapi.auth.backends.base.WebAPIAuthBackend`).

    Subclasses must define :py:attr:`api_token_model`.
    """

    #: The API token model to use for any token lookups.
    #:
    #: Type:
    #:     type
    api_token_model: Optional[Type[BaseWebAPIToken]] = None

    def authenticate(
        self,
        request: HttpRequest,
        token: Optional[str] = None,
        **kwargs,
    ) -> Optional[WebAPIAuthenticateResult]:
        """Authenticate a user, given a token ID.

        Args:
            request (django.http.HttpRequest, unused):
                The request object.

            token (unicode, optional):
                The API token ID to authenticate with.

            **kwargs (dict, unused):
                Keyword arguments for future expansion.

        Returns:
            django.contrib.auth.models.User:
            The resulting user, if a token matched, or ``None`` otherwise.
        """
        api_token_model = self.api_token_model
        assert api_token_model is not None

        if not token:
            return None

        # Find the WebAPIToken matching the token parameter passed in.
        # Once we have it, we'll need to perform some additional checks on
        # the user.
        queryset = (
            api_token_model.objects
            .filter(token=token)
            .select_related('user')
        )

        try:
            webapi_token = queryset.get()
        except api_token_model.DoesNotExist:
            return None

        user = webapi_token.user

        if not user.is_active:
            return None

        # Store this temporarily. We'll be using it to store some session
        # state.
        user._webapi_token = webapi_token

        return user

    def validate_token(
        self,
        request: HttpRequest,
        token: str,
    ) -> Optional[TokenAuthValidateResult]:
        """Check that the token is valid to use for authentication.

        This will check if the token is invalid or expired. If so it will
        return a dictionary containing an error message with details on whether
        the token is invalid or expired and any appropriate HTTP headers to
        send to the client. If the token is valid to use for authentication
        this will return ``None``.

        Version Added:
            3.0

        Args:
            request (django.http.HttpRequest):
                The request object.

            token (str):
                The API token ID to validate.

        Returns:
            dict or None:
            A dictionary containing the following keys:

            Keys:
                error_message (str):
                    An error message explaining why the token cannot be used
                    for authentication.

                headers (dict):
                    A dictionary of HTTP headers to send to the client.

            These are meant to be used as the ``error_message`` and ``header``
            values in the return type of :py:meth:`djblets.webapi.auth.
            backends.base.WebAPIAuthBackend.authenticate`.

            If the token is valid to use for authentication this will return
            ``None``.
        """
        api_token_model = self.api_token_model
        assert api_token_model is not None

        queryset = api_token_model.objects.filter(token=token)

        log_extra: Dict[str, Any] = {
            'request': request,
        }

        try:
            webapi_token = queryset.get()
        except api_token_model.DoesNotExist:
            logger.debug('API Login failed. Token not found.',
                         extra=log_extra)

            return {
                'error_message': None,
                'headers': None,
            }

        if not webapi_token.valid:
            logger.debug('API Login failed for %s. The token is invalid.',
                         webapi_token.user.username,
                         extra=log_extra)

            if webapi_token.invalid_reason:
                error_message = (
                    _('This API token became invalid on %s: %s')
                    % (localize(webapi_token.invalid_date),
                       webapi_token.invalid_reason)
                )
            else:
                error_message = (
                    _('This API token became invalid on %s.')
                    % localize(webapi_token.invalid_date)
                )

            return {
                'error_message': error_message,
                'headers': LOGIN_FAILED.headers(request).copy(),
            }
        elif webapi_token.is_expired():
            logger.debug('API Login failed for %s. The token is expired.',
                         webapi_token.user.username,
                         extra=log_extra)

            webapi_token_expired.send(instance=webapi_token,
                                      sender=type(webapi_token))

            return {
                'error_message': (
                    _('This API token expired on %s.')
                    % localize(webapi_token.expires)
                ),
                'headers': LOGIN_FAILED.headers(request).copy(),
            }

        return None


class WebAPITokenAuthBackend(WebAPIAuthBackend):
    """Authenticates users using their generated API token.

    This will check the ``HTTP_AUTHORIZATION`` header for a ``token <token>``
    value. If found, it will attempt to find the user that owns the
    token, and authenticate that user.
    """

    def get_credentials(
        self,
        request: HttpRequest,
    ) -> WebAPIGetCredentialsResult:
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

    def login_with_credentials(
        self,
        request: HttpRequest,
        **credentials,
    ) -> WebAPIAuthenticateResult:
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
            See the return type in :py:meth:`djblets.webapi.auth.backends.
            base.WebAPIAuthBackend.authenticate`.
        """
        result = super().login_with_credentials(request, **credentials)

        if result[0]:
            user = request.user
            webapi_token = getattr(user, '_webapi_token', None)
            assert isinstance(webapi_token, BaseWebAPIToken)

            delattr(user, '_webapi_token')

            webapi_token.last_used = timezone.now()
            webapi_token.save_base(update_fields=('last_used',))

            request.session['webapi_token_id'] = webapi_token.pk
            setattr(request, '_webapi_token', webapi_token)

            if webapi_token.is_deprecated():
                deprecation_header = {
                    'X-API-Token-Deprecated': (
                        'This token uses a deprecated format. The token can '
                        'still be used, but you should remove it and '
                        'generate a new one to take advantage of security '
                        'improvements.'
                    )
                }

                # Keep any headers that were already set.
                headers = result[2] or {}
                headers.update(deprecation_header)

                result = (result[0], result[1], headers)

        return result

    def validate_credentials(
        self,
        request: HttpRequest,
        **credentials,
    ) -> Optional[WebAPIAuthenticateResult]:
        """Validate that credentials are valid.

        This will run through authentication backends to check whether
        the API token is valid to use. If the token is not valid to use this
        will stop the authentication process and return a message and headers
        on why it cannot be used.

        Version Added:
            3.0

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            credentials (dict):
                All credentials provided by :py:meth:`get_credentials`.

        Returns:
            tuple or None:
            See the return type in :py:meth:`WebAPIAuthBackend.authenticate()
            <djblets.webapi.auth.backends.base.WebAPIAuthBackend
            .authenticate>`.
        """
        result = super().validate_credentials(request, **credentials)

        if result is not None:
            return result

        token = credentials.get('token')

        if token is not None:
            assert isinstance(token, str)

            for backend in get_backends():
                if isinstance(backend, ValidateTokenAuthBackend):
                    validate_result = backend.validate_token(request, token)

                    if validate_result is not None:
                        return (False,
                                validate_result.get('error_message'),
                                validate_result.get('headers'))

        return None
