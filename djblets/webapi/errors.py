"""Error classes and codes for WebAPI."""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from django.http import HttpRequest
    from djblets.webapi.responses import WebAPIResponseHeaders
    from typing_extensions import Self, TypeAlias

    #: A mapping of HTTP headers to values, or a callable returning headers.
    #:
    #: Version Added:
    #:     4.0
    _HTTPHeadersOrCallable: TypeAlias = Union[
        WebAPIResponseHeaders,
        Callable[[HttpRequest], WebAPIResponseHeaders]
    ]


class WebAPIError:
    """An API error, containing an error code and human readable message.

    Version Changed:
        4.0:
        * Added Python type hints.
    """

    ######################
    # Instance variables #
    ######################

    #: The numeric code for the error.
    #:
    #: Type:
    #:     int
    code: int

    #: Extra HTTP headers included in the error's HTTP response.
    #:
    #: This may also be a callable that returns HTTP headers, given an HTTP
    #: request.
    #:
    #: Type:
    #:     dict or callable
    headers: _HTTPHeadersOrCallable

    #: The HTTP status code of the error.
    #:
    #: Type:
    #:     int
    http_status: int

    #: The error message shown to the caller.
    #:
    #: Type:
    #:     str
    msg: str

    def __init__(
        self,
        code: int,
        msg: str,
        http_status: int = 400,
        headers: _HTTPHeadersOrCallable = {},
    ) -> None:
        """Initialize the error.

        Args:
            code (int):
                The numeric code for the error.

            msg (str):
                The error message shown to the caller.

            http_status (int, optional):
                The HTTP status code for the error.

                This defaults to :http:`400`.

            headers (dict or callable, optional):
                Extra HTTP headers to include in the error's HTTP response.

                This may also be a callable that returns HTTP headers, given
                an HTTP request.
        """
        self.code = code
        self.msg = msg
        self.http_status = http_status
        self.headers = headers

    def __repr__(self) -> str:
        """Return a string representation of the error.

        Returns:
            str:
            The string representation.
        """
        return '<API Error %d, HTTP %d: %s>' % (self.code, self.http_status,
                                                self.msg)

    def with_overrides(
        self,
        msg: Optional[str] = None,
        headers: Optional[_HTTPHeadersOrCallable] = None,
    ) -> Self:
        """Return an error with overridden values.

        The returned error will be based on this error, but with a custom
        message or headers.

        Args:
            msg (str, optional):
                The custom error message.

            headers (dict or callable, optional):
                Custom HTTP headers to include in the error's HTTP response.

                This may also be a callable that returns HTTP headers, given
                an HTTP request.

                These will override the default HTTP headers for the error.

        Returns:
            WebAPIError:
            The new error instance.
        """
        if headers is None:
            headers = self.headers

        return type(self)(code=self.code,
                          msg=msg or self.msg,
                          http_status=self.http_status,
                          headers=headers)

    def with_message(
        self,
        msg: str,
    ) -> Self:
        """Return an error with an overridden error message.

        The returned error will be based on this error, but with a custom
        message.

        Args:
            msg (str):
                The custom error message.

        Returns:
            WebAPIError:
            The new error instance.
        """
        return self.with_overrides(msg)


class WebAPITokenGenerationError(Exception):
    """An error generating a Web API token."""


def _get_auth_headers(
    request: HttpRequest,
) -> WebAPIResponseHeaders:
    """Return HTTP headers for an authentication error.

    The result will include any headers from the authentication backend,
    along with a :mailheader:`WWW-Authenticate` header containing a
    comma-separated list of schemes set by auth backends (see
    :py:attr:`WebAPIAuthBackend.www_auth_scheme
    <djblets.webapi.auth.backends.base.WebAPIAuthBackend.www_auth_scheme>`.

    Args:
        request (django.http.HttpRequest):
            The HTTP request from the client.

    Returns:
        dict:
        The mapping of HTTP authentication headers to values.
    """
    from djblets.webapi.auth.backends import get_auth_backends

    headers: Dict[str, str] = {}
    www_auth_schemes: List[str] = []

    for auth_backend_cls in get_auth_backends():
        auth_backend = auth_backend_cls()

        if auth_backend.www_auth_scheme:
            www_auth_schemes.append(auth_backend.www_auth_scheme)

        headers.update(auth_backend.get_auth_headers(request))

    if www_auth_schemes:
        headers['WWW-Authenticate'] = ', '.join(www_auth_schemes)

    return headers


#
# Standard error messages
#
NO_ERROR = WebAPIError(
    0,
    "If you see this, yell at the developers")

SERVICE_NOT_CONFIGURED = WebAPIError(
    1,
    "The web service has not yet been configured",
    http_status=503)

DOES_NOT_EXIST = WebAPIError(
    100,
    "Object does not exist",
    http_status=404)

PERMISSION_DENIED = WebAPIError(
    101,
    "You don't have permission for this",
    http_status=403)

INVALID_ATTRIBUTE = WebAPIError(
    102,
    "Invalid attribute",
    http_status=400)

NOT_LOGGED_IN = WebAPIError(
    103,
    "You are not logged in",
    http_status=401,
    headers=_get_auth_headers)

LOGIN_FAILED = WebAPIError(
    104,
    "The username or password was not correct",
    http_status=401,
    headers=_get_auth_headers)

INVALID_FORM_DATA = WebAPIError(
    105,
    "One or more fields had errors",
    http_status=400)

MISSING_ATTRIBUTE = WebAPIError(
    106,
    "Missing value for the attribute",
    http_status=400)

ENABLE_EXTENSION_FAILED = WebAPIError(
    107,
    "There was a problem enabling the extension",
    http_status=500)  # 500 Internal Server Error

DISABLE_EXTENSION_FAILED = WebAPIError(
    108,
    "There was a problem disabling the extension",
    http_status=500)  # 500 Internal Server Error

EXTENSION_INSTALLED = WebAPIError(
    109,
    "This extension has already been installed.",
    http_status=409)

INSTALL_EXTENSION_FAILED = WebAPIError(
    110,
    "An error occurred while installing the extension",
    http_status=409)

DUPLICATE_ITEM = WebAPIError(
    111,
    "An entry for this item or its unique key(s) already exists",
    http_status=409)

OAUTH_MISSING_SCOPE_ERROR = WebAPIError(
    112,
    'Your OAuth2 token lacks the necessary scopes for this request.',
    http_status=403,  # 403 Forbidden
)

OAUTH_ACCESS_DENIED_ERROR = WebAPIError(
    113,
    'OAuth2 token access for this resource is prohibited.',
    http_status=403,  # 403 Forbidden
)

RATE_LIMIT_EXCEEDED = WebAPIError(
    114,
    'API rate limit has been exceeded.',
    http_status=429,  # 429 Too Many Requests
)
