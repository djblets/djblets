"""Error classes and codes for WebAPI."""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, TYPE_CHECKING, Union

from housekeeping import deprecate_non_keyword_only_args

from djblets.deprecation import RemovedInDjblets60Warning

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
        * Added :py:attr:`detail`, :py:attr:`error_type`, and
          :py:attr:`error_subtype`, and :py:attr:`trace_id` attributes.
    """

    ######################
    # Instance variables #
    ######################

    #: The numeric code for the error.
    #:
    #: This may be used along with :py:attr:`error_type`, depending on the
    #: consumer's API requirements. This was the original error type indicator
    #: prior to Djblets 4.
    #:
    #: Type:
    #:     int
    code: int

    #: A message used to convey additional detail on this error.
    #:
    #: Version Added:
    #:     4.0
    detail: Optional[str]

    #: A string indicating the subtype of the error.
    #:
    #: This can provide additional context beyond :py:attr:`code` or
    #: :py:attr:`error_type`.
    #:
    #: Version Added:
    #:     4.0
    error_subtype: Optional[str]

    #: A string indicating the type of the error.
    #:
    #: This is a string equivalent to ``code``, and is used to allow callers
    #: to differentiate between errors. It may be accompanied by a
    #: :py:attr:`error_subtype``.
    #:
    #: Version Added:
    #:     4.0
    error_type: Optional[str]

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

    #: An ID shown in the error that's associated with logs.
    #:
    #: This can be supplied using :py:meth:`with_overrides` in order to
    #: associate the error with logged output containing more detail.
    #:
    #: Version Added:
    #:     4.0
    trace_id: Optional[str]

    @deprecate_non_keyword_only_args(RemovedInDjblets60Warning)
    def __init__(
        self,
        code: int,
        msg: str,
        *,
        http_status: int = 400,
        headers: _HTTPHeadersOrCallable = {},
        error_type: Optional[str] = None,
        error_subtype: Optional[str] = None,
        detail: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> None:
        """Initialize the error.

        Version Changed:
            4.0:
            * Added ``error_type``, ``error_subtype``, ``detail``, and
              ``trace_id`` attributes.
            * ``http_status`` and ``headers`` must be provided as a keyword.
              Passing as positional arguments is deprecated and will be removed
              in Djblets 6.

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

            error_type (str, optional):
                A string indicating the type of the error.

                This is a string equivalent to ``code``, and is used to allow
                callers to differentiate between errors. It may be accompanied
                by ``error_subtype``.

                Third-party errors (such as those provided by extensions)
                should be in the form of :samp:`x-{vendor}-{type}`.

                Version Added:
                    4.0

            error_subtype (str, optional):
                A string indicating the subtype of the error.

                This can provide additional context beyond :py:attr:`code` or
                :py:attr:`error_type`.

                Third-party errors (such as those provided by extensions)
                should be in the form of :samp:`x-{vendor}-{type}`.

                Version Added:
                    4.0

            detail (str, optional):
                An message used to convey additional details on this error.

                Version Added:
                    4.0

            trace_id (str, optional):
                An ID shown in the error that's associated with logs.

                This can be supplied using :py:meth:`with_overrides` in order
                to associate the error with logged output containing more
                detail.

                Version Added:
                    4.0
        """
        self.code = code
        self.msg = msg
        self.http_status = http_status
        self.headers = headers
        self.error_type = error_type
        self.error_subtype = error_subtype
        self.detail = detail
        self.trace_id = trace_id

    def __repr__(self) -> str:
        """Return a string representation of the error.

        Returns:
            str:
            The string representation.
        """
        return '<API Error %d, HTTP %d: %s>' % (self.code, self.http_status,
                                                self.msg)

    @deprecate_non_keyword_only_args(RemovedInDjblets60Warning)
    def with_overrides(
        self,
        msg: Optional[str] = None,
        *,
        headers: Optional[_HTTPHeadersOrCallable] = None,
        error_subtype: Optional[str] = None,
        detail: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> Self:
        """Return an error with overridden values.

        The returned error will be based on this error, but with a custom
        message or headers.

        Version Changed:
            4.0:
            * Added ``error_subtype``, ``detail``, and ``trace_id`` attributes.
            * ``headers`` must be provided as a keyword. Passing as a
              positional argument is deprecated and will be removed in
              Djblets 6.

        Args:
            msg (str, optional):
                The custom error message.

            headers (dict or callable, optional):
                Custom HTTP headers to include in the error's HTTP response.

                This may also be a callable that returns HTTP headers, given
                an HTTP request.

                These will override the default HTTP headers for the error.

            error_subtype (str, optional):
                A string indicating the subtype of the error.

                This can provide additional context beyond :py:attr:`code` or
                :py:attr:`error_type`.

                Third-party errors (such as those provided by extensions)
                should be in the form of :samp:`x-{vendor}-{type}`.

                Version Added:
                    4.0

            detail (str, optional):
                An message used to convey additional details on this error.

                Version Added:
                    4.0

            trace_id (str, optional):
                An ID shown in the error that's associated with logs.

                This can be supplied using :py:meth:`with_overrides` in order
                to associate the error with logged output containing more
                detail.

                Version Added:
                    4.0

        Returns:
            WebAPIError:
            The new error instance.
        """
        if headers is None:
            headers = self.headers

        return type(self)(code=self.code,
                          msg=msg or self.msg,
                          http_status=self.http_status,
                          headers=headers,
                          error_type=self.error_type,
                          error_subtype=error_subtype or self.error_subtype,
                          detail=detail or self.detail,
                          trace_id=trace_id or self.trace_id)

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


#: An error indicating no error occurred.
#:
#: This should never be encountered.
NO_ERROR = WebAPIError(
    code=0,
    msg='If you see this, yell at the developers',
    error_type='no-error')


#: An error indicating the web service is not configured.
SERVICE_NOT_CONFIGURED = WebAPIError(
    code=1,
    msg='The web service has not yet been configured',
    error_type='server-not-configured',
    http_status=503)


#: An error indicating a requested resource does not exist.
DOES_NOT_EXIST = WebAPIError(
    code=100,
    msg='Object does not exist',
    error_type='resource-does-not-exist',
    http_status=404)


#: An error indicating the user doesn't have permission for a resource.
#:
#: The user may not have read access or write access to the resource.
PERMISSION_DENIED = WebAPIError(
    code=101,
    msg="You don't have permission for this",
    error_type='resource-permission-denied',
    http_status=403)


#: An error indicating a resource doesn't support an attribute for the request.
#:
#: This should be used when performing a request to a resource that's dependent
#: on some attribute (such as a capability flag, setting, or associated
#: resource) on the requested resource being available or set to an expected
#: value, or when the request is missing the attribute.
#:
#: This response payload should contain a top-level ``reason`` field with an
#: error message.
#:
#: For invalid request fields, see :py:data:`INVALID_FORM_DATA`.
INVALID_ATTRIBUTE = WebAPIError(
    code=102,
    msg='Invalid attribute',
    error_type='resource-attribute-invalid',
    http_status=400)


#: An error indicating that the user is not logged in.
#:
#: This can be used to require authenticating to the API before making the
#: request.
NOT_LOGGED_IN = WebAPIError(
    code=103,
    msg='You are not logged in',
    error_type='auth-not-logged-in',
    http_status=401,
    headers=_get_auth_headers)


#: An error indicating that authentication failed.
LOGIN_FAILED = WebAPIError(
    code=104,
    msg='The username or password was not correct',
    error_type='auth-login-failed',
    http_status=401,
    headers=_get_auth_headers)


#: An error indicating data submitted in the request is invalid.
#:
#: Callers should set ``fields`` at the top of the payload to a dictionary
#: mapping field names to lists of error mesages.
INVALID_FORM_DATA = WebAPIError(
    code=105,
    msg='One or more fields had errors',
    error_type='request-field-error',
    http_status=400)


#: An error indicating a required attribute in a request is missing.
#:
#: This is usually a missing attribute in the request data provided for a
#: resource.
MISSING_ATTRIBUTE = WebAPIError(
    code=106,
    msg='Missing value for the attribute',
    error_type='request-attribute-missing',
    http_status=400)


#: An error indicating an extension couldn't be enabled.
ENABLE_EXTENSION_FAILED = WebAPIError(
    code=107,
    msg='There was a problem enabling the extension',
    error_type='extension-enable-error',
    http_status=500)  # 500 Internal Server Error


#: An error indicating an extension couldn't be disabled.
DISABLE_EXTENSION_FAILED = WebAPIError(
    code=108,
    msg='There was a problem disabling the extension',
    error_type='extension-disable-error',
    http_status=500)  # 500 Internal Server Error


#: An error indicating an extension is already installed.
#:
#: This is used when trying to install an extension that is already installed.
EXTENSION_INSTALLED = WebAPIError(
    code=109,
    msg='This extension has already been installed.',
    error_type='extension-already-installed',
    http_status=409)


#: An error indicating an extension installation failed.
INSTALL_EXTENSION_FAILED = WebAPIError(
    code=110,
    msg='An error occurred while installing the extension',
    error_type='extension-install-error',
    http_status=409)


#: An error indicating an item conflicts with another.
#:
#: This is used when attempting to perform a request that would result in a
#: conflict between resources on the server.
DUPLICATE_ITEM = WebAPIError(
    code=111,
    msg='An entry for this item or its unique key(s) already exists',
    error_type='resource-conflict',
    http_status=409)


#: An error indicating an OAuth2 token lacks a required scope.
OAUTH_MISSING_SCOPE_ERROR = WebAPIError(
    code=112,
    msg='Your OAuth2 token lacks the necessary scopes for this request.',
    error_type='auth-oauth2-missing-scope',
    http_status=403,  # 403 Forbidden
)


#: An error indicating an OAuth2 token cannot be used to access the resource.
OAUTH_ACCESS_DENIED_ERROR = WebAPIError(
    code=113,
    msg='OAuth2 token access for this resource is prohibited.',
    error_type='auth-oauth2-access-denied',
    http_status=403,  # 403 Forbidden
)


#: An error indicating the API rate limit has been exceeded.
RATE_LIMIT_EXCEEDED = WebAPIError(
    code=114,
    msg='API rate limit has been exceeded.',
    error_type='request-rate-limit-exceeded',
    http_status=429,  # 429 Too Many Requests
)
