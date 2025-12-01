"""Utilities for working with HTTP requests.

Version Added:
    5.3
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.http import HttpRequest


def get_http_request_ip(
    request: HttpRequest,
) -> str:
    """Return the IP address from a client for a given HTTP request.

    This will check the following headers for a suitable IP address:

    * :mailheader:`X-Real-IP`
    * :mailheader:`X-Forwarded-For`

    If not found, it will fall back to the IP address the request originated
    from, which may be a public address or an internal address within the
    service's network.

    Version Added:
        5.3

    Args:
        request (django.http.HttpRequest):
            The HTTP request from the client.

    Returns:
        str:
        The IP address for the request.
    """
    try:
        return request.META['HTTP_X_REAL_IP']
    except KeyError:
        try:
            return request.META['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()
        except KeyError:
            return request.META['REMOTE_ADDR']
