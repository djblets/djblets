"""The base class for an API authentication backend."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional, Tuple, Union

from django.contrib import auth
from django.http import HttpRequest
from django.utils.translation import gettext as _
from typing_extensions import TypeAlias

from djblets.auth.ratelimit import is_ratelimited
from djblets.webapi.responses import WebAPIResponseHeaders


#: A type alias for authentication results.
#:
#: This was the only return value supported prior to Djblets 3.2.
#:
#: Contents are in the form of:
#:
#: Tuple:
#:     0 (bool):
#:         Whether the authentication request was successful.
#:
#:     1 (str):
#:         The error message to return if authentication failed.
#:
#:         This can be ``None`` if it succeeded, or if it failed
#:         and the default error from
#:         :py:data:`~djblets.webapi.errors.LOGIN_FAILED` should be used.
#:
#:     2 (dict):
#:         Any HTTP headers to return in the response.
#:
#:         This can be ``None`` if no headers need to be returned,
#:         or if it failed and default headers from
#:         :py:data:`~djblets.webapi.errors.LOGIN_FAILED` should be used.
#:
#: Version Added:
#:     3.2
WebAPIAuthenticateResult: TypeAlias = Tuple[bool,
                                            Optional[str],
                                            Optional[WebAPIResponseHeaders]]


#: A type alias for credentials passed to or from auth handlers.
#:
#: Version Added:
#:     3.2
WebAPICredentials: TypeAlias = Dict[str, Any]


#: A type alias for the result of a get_credentials response.
#:
#: Version Added:
#:     3.2
WebAPIGetCredentialsResult: TypeAlias = \
    Optional[Union[WebAPIAuthenticateResult,
                   WebAPICredentials]]


logger = logging.getLogger(__name__)


class WebAPIAuthBackend:
    """Handles a form of authentication for the web API.

    This can be overridden to provide custom forms of authentication, or to
    support multiple types of authentication.

    More than one authentication backend can be used with the web API. In that
    case, the client can make the determination about which to use.

    Auth backends generally need to only override the
    :py:meth:`get_credentials` method, though more specialized ones may
    override other methods as well.

    They must also provide :py:attr:`www_auth_scheme` which is a
    ``WWW-Authenticate`` scheme value.
    """

    #: The auth scheme used in the ``WWW-Authenticate`` header.
    #:
    #: Type:
    #:     str
    www_auth_scheme: Optional[str] = None

    #: A regex of sensitive entries in the credentials dictionary.
    #:
    #: By default, this excludes keys containing "api", "token", "key",
    #: "secret", "password", or "signature" anywhere in the name, in any
    #: casing.
    #:
    #: This can be extended for other sensitive information.
    SENSITIVE_CREDENTIALS_RE = \
        re.compile('api|token|key|secret|password|signature', re.I)

    def get_auth_headers(
        self,
        request: HttpRequest
    ) -> Dict[str, Any]:
        """Return extra authentication headers for the response.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

        Returns:
            dict:
            The authentication headers (defaults to empty).
        """
        return {}

    def authenticate(
        self,
        request: HttpRequest,
        **kwargs,
    ) -> Optional[WebAPIAuthenticateResult]:
        """Authenticate a request against this auth backend.

        This will fetch the credentials and attempt an authentication against
        those credentials.

        This function must return ``None`` to indicate it should be skipped
        and another backend should be tried, or a tuple indicating the
        success/failure and additional details for the client.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

        Returns:
            tuple or None:
            See :py:class:`WebAPIAuthenticateResult` for details on the format
            for the returned type value.

            If the backend should be skipped, this will return ``None``.
        """
        result: WebAPIAuthenticateResult

        # Check if number of failed login attempts already exceeded
        # before authenticating.
        if is_ratelimited(request, increment=False):
            return False, _('Maximum number of login attempts exceeded.'), None

        credentials = self.get_credentials(request)

        if credentials is None:
            return None

        if isinstance(credentials, dict):
            result = self.login_with_credentials(request, **credentials)
        else:
            assert isinstance(credentials, tuple)
            result = credentials

        if not result[0]:
            # Automatically increment when login with credentials is not
            # successful.
            is_ratelimited(request, increment=True)

        return result

    def get_credentials(
        self,
        request: HttpRequest,
    ) -> WebAPIGetCredentialsResult:
        """Return credentials provided in the request.

        This returns a dictionary of all credentials necessary for this
        auth backend. By default, this expects ``username`` and ``password``,
        though more specialized auth backends may provide other information.
        These credentials will be passed to :py:meth:`login_with_credentials`.

        This function must be implemented by the subclass.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

        Returns:
            dict:
            A dictionary of credential information.
        """
        raise NotImplementedError

    def login_with_credentials(
        self,
        request: HttpRequest,
        **credentials,
    ) -> WebAPIAuthenticateResult:
        """Log in against the main authentication backends.

        This takes the provided credentials from the request (as returned by
        :py:meth:`get_credentials`) and attempts a login against the main
        authentication backends used by Django.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            credentials (dict):
                All credentials provided by :py:meth:`get_credentials`.

        Returns:
            tuple or None:
            See the return type in :py:meth:`authenticate`.
        """
        result = self.validate_credentials(request, **credentials)

        if result is not None:
            return result

        log_extra = {
            'request': request,
        }

        cleaned_credentials = self.clean_credentials_for_display(credentials)
        logger.debug(
            'Attempting authentication on API: %s',
            ', '.join([
                '%s=%s' % pair
                for pair in cleaned_credentials.items()
            ]),
            extra=log_extra)

        user = auth.authenticate(request=request, **credentials)

        if user and user.is_active:
            auth.login(request, user)

            return True, None, None

        logger.debug('API Login failed. No valid user found.',
                     extra=log_extra)
        auth.logout(request)

        return False, None, None

    def validate_credentials(
        self,
        request: HttpRequest,
        **credentials,
    ) -> Optional[WebAPIAuthenticateResult]:
        """Validate that credentials are valid.

        This is called before we attempt to authenticate with the credentials,
        and can short-circuit the rest of the authentication process,
        returning a result tuple if desired. If ``None`` is returned,
        authentication proceeds as normal.

        By default, this will attempt to bypass authentication if the
        current user is already logged in and matches the authenticated
        user (if and only if ``username`` appears in the credentials).

        Subclasses can override this to provide more specific behavior for
        their sets of credentials, or to disable this entirely.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            credentials (dict):
                All credentials provided by :py:meth:`get_credentials`.

        Returns:
            tuple or None:
            See the return type in :py:meth:`authenticate`.
        """
        # Don't authenticate if a user is already logged in and the
        # username matches.
        #
        # Note that this does mean that a new password will fail. However,
        # the user is already logged in, and querying the backend for every
        # request is excessive, so it's a tradeoff. The user already has
        # access to the server at this point anyway.
        if (request.user.is_authenticated and
            request.user.get_username() == credentials.get('username')):
            return True, None, None

        return None

    def clean_credentials_for_display(
        self,
        credentials: WebAPICredentials,
    ) -> WebAPICredentials:
        """Clean up a credentials dictionary, removing sensitive information.

        This will take a credentials dictionary and mask anything sensitive,
        preparing it for output to a log file.

        Args:
            credentials (dict):
                A dictionary of credentials provided for authentication.

        Returns:
            dict:
            A sanitized dictionary of credentials, for display purposes.
        """
        clean_credentials = {}

        for key, value in credentials.items():
            if self.SENSITIVE_CREDENTIALS_RE.search(key):
                clean_credentials[key] = '************'
            else:
                clean_credentials[key] = value

        return clean_credentials
