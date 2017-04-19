"""The base class for an API authentication backend."""

from __future__ import unicode_literals

import logging
import re

from django.contrib import auth
from django.utils import six


logger = logging.getLogger(__name__)


class WebAPIAuthBackend(object):
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
    www_auth_scheme = None

    #: A regex of sensitive entries in the credentials dictionary.
    #:
    #: By default, this excludes keys containing "api", "token", "key",
    #: "secret", "password", or "signature" anywhere in the name, in any
    #: casing.
    #:
    #: This can be extended for other sensitive information.
    SENSITIVE_CREDENTIALS_RE = \
        re.compile('api|token|key|secret|password|signature', re.I)

    def get_auth_headers(self, request):
        """Return extra authentication headers for the response.

        Args:
            request (HttpRequest): The HTTP request from the client.

        Returns:
            dict: The authentication headers (defaults to empty).
        """
        return {}

    def authenticate(self, request):
        """Authenticate a request against this auth backend.

        This will fetch the credentials and attempt an authentication against
        those credentials.

        This function must return ``None`` to indicate it should be skipped
        and another backend should be tried, or a tuple indicating the
        success/failure and additional details for the client.

        The tuple is in the form of::

            (is_successful, error_message, headers)

        The error message and headers can be None to use the default error
        message and headers from the :py:data:`LOGIN_FAILED` error. In most
        cases, they should be ``None``, unless there are more specific
        instructions needed for authenticating.

        Args:
            request (HttpRequest): The HTTP request from the client.

        Returns:
            tuple or None
        """
        credentials = self.get_credentials(request)

        if not credentials:
            return None

        if isinstance(credentials, dict):
            result = self.login_with_credentials(request, **credentials)
        else:
            assert isinstance(credentials, tuple)
            result = credentials

        return result

    def get_credentials(self, request):
        """Return credentials provided in the request.

        This returns a dictionary of all credentials necessary for this
        auth backend. By default, this expects ``username`` and ``password``,
        though more specialized auth backends may provide other information.
        These credentials will be passed to :py:meth:`login_with_credentials`.

        This function must be implemented by the subclass.

        Args:
            request (HttpRequest): The HTTP request from the client.
        """
        raise NotImplementedError

    def login_with_credentials(self, request, **credentials):
        """Log in against the main authentication backends.

        This takes the provided credentials from the request (as returned by
        :py:meth:`get_credentials`) and attempts a login against the main
        authentication backends used by Django.

        Args:
            request (HttpRequest):
                The HTTP request from the client.

            credentials:
                All credentials provided by :py:meth:`get_credentials`.

        Returns:
            tuple or None: See the return type in :py:meth:`authenticate`.
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
                for pair in six.iteritems(cleaned_credentials)
            ]),
            extra=log_extra)

        user = auth.authenticate(**credentials)

        if user and user.is_active:
            auth.login(request, user)

            return True, None, None

        logger.debug('API Login failed. No valid user found.',
                     extra=log_extra)
        auth.logout(request)

        return False, None, None

    def validate_credentials(self, request, **credentials):
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
            request (HttpRequest):
                The HTTP request from the client.

            credentials:
                All credentials provided by :py:meth:`get_credentials`.

        Returns:
            tuple or None: See the return type in :py:meth:`authenticate`.
        """
        # Don't authenticate if a user is already logged in and the
        # username matches.
        #
        # Note that this does mean that a new password will fail. However,
        # the user is already logged in, and querying the backend for every
        # request is excessive, so it's a tradeoff. The user already has
        # access to the server at this point anyway.
        if (request.user.is_authenticated() and
            request.user.username == credentials.get('username')):
            return True, None, None

        return None

    def clean_credentials_for_display(self, credentials):
        """Clean up a credentials dictionary, removing sensitive information.

        This will take a credentials dictionary and mask anything sensitive,
        preparing it for output to a log file.

        Args:
            credentials (dict):
                A dictionary of credentials provided for authentication.

        Returns:
            dict: A sanitized dictionary of credentials, for display purposes.
        """
        clean_credentials = {}

        for key, value in six.iteritems(credentials):
            if self.SENSITIVE_CREDENTIALS_RE.search(key):
                clean_credentials[key] = '************'
            else:
                clean_credentials[key] = value

        return clean_credentials
