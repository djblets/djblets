"""Deprecated views for handling authentication.

These allow for logging a user in through an HTTP POST request supplying
a username and password, and logging out through a POST or GET request.

This support is deprecated. Instead, your application should make use of
one of our authentication backends, such as
:py:class:`djblets.webapi.auth.backends.basic.WebAPIBasicAuthBackend`.
"""

from __future__ import unicode_literals

from django.contrib import auth
from django.views.decorators.http import require_POST

from djblets.webapi.decorators import webapi
from djblets.webapi.errors import LOGIN_FAILED
from djblets.webapi.responses import WebAPIResponse, WebAPIResponseError


@require_POST
@webapi
def account_login(request, *args, **kwargs):
    """Log the user in through a provided login and password.

    .. deprecated: 0.9

    Rather than using this view, you should be authenticating using API
    auth backends instead.

    Args:
        request (HttpRequest): The HTTP request from the client.

    Returns:
        WebAPIResponseE:
        A blank response if logging in succeeded, or a :py:data:`LOGIN_FAILED`
        if it failed.
    """
    username = request.POST.get('username', None)
    password = request.POST.get('password', None)

    user = auth.authenticate(username=username, password=password)

    if not user or not user.is_active:
        return WebAPIResponseError(request, LOGIN_FAILED)

    auth.login(request, user)

    return WebAPIResponse(request)


@webapi
def account_logout(request, *args, **kwargs):
    """Log the user out, and send an API response.

    .. deprecated: 0.9

    Args:
        request (HttpRequest): The HTTP request from the client.

    Returns:
        WebAPIResponse: The API response indicating a successful logout.
    """
    auth.logout(request)
    return WebAPIResponse(request)
