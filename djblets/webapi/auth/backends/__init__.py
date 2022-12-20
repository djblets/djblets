"""Base support for managing API authentication backends.

These functions allow for fetching the list of available API authentication
backend classes, and using them to perform an authentication based on an HTTP
request.
"""

from __future__ import annotations

from importlib import import_module
from typing import List, Optional, Type

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest

from djblets.webapi.auth.backends.base import (WebAPIAuthBackend,
                                               WebAPIAuthenticateResult)


_auth_backends: List[Type[WebAPIAuthBackend]] = []


def get_auth_backends() -> List[Type[WebAPIAuthBackend]]:
    """Return the list of web API authentication backends.

    This defaults to :py:class:`~djblets.webapi.auth.backends.basic.
    WebAPIBasicAuthBackend`, for HTTP Basic Auth, but can be overridden by
    setting ``settings.WEB_API_AUTH_BACKENDS`` to a list of class paths.

    Returns:
        list:
        A list of all usable authentication backend classes.
    """
    global _auth_backends

    if not _auth_backends:
        class_paths = getattr(
            settings, 'WEB_API_AUTH_BACKENDS', [
                'djblets.webapi.auth.backends.basic.WebAPIBasicAuthBackend',
            ])

        _auth_backends = []

        for class_path in class_paths:
            class_path = str(class_path)

            i = class_path.rfind(str('.'))
            module, attr = class_path[:i], class_path[i + 1:]

            try:
                mod = import_module(module)
            except ImportError as e:
                raise ImproperlyConfigured(
                    'Error importing web API auth backend %s: %s'
                    % (module, e))

            try:
                _auth_backends.append(getattr(mod, attr))
            except AttributeError:
                raise ImproperlyConfigured(
                    'Module "%s" does not define a "%s" class for the web API '
                    'auth backend'
                    % (module, attr))

    return _auth_backends


def reset_auth_backends():
    """Reset the list of authentication backends.

    The list will be recomputed the next time an authentication backend needs
    to be used.
    """
    global _auth_backends

    _auth_backends = []


def check_login(
    request: HttpRequest,
) -> Optional[WebAPIAuthenticateResult]:
    """Check if a login request was made.

    If the client specifies a ``HTTP_AUTHORIZATION`` header, this will attempt
    to authenticate using a supported authentication method.

    Args:
        request (HttpRequest): The HTTP request from the client.

    Returns:
        tuple:
        The result of the authentication, if successful, or ``None`` otherwise.

        See :py:class:`~djblets.webapi.auth.backends.base.
        WebAPIAuthenticateResult` for details on the format for the returned
        type value.
    """
    if 'HTTP_AUTHORIZATION' in request.META:
        for auth_backend_cls in get_auth_backends():
            result = auth_backend_cls().authenticate(request)

            if result is not None:
                return result

    return None
