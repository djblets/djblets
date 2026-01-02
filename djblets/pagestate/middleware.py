"""Middleware for page states.

Version Added:
    5.3
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from djblets.pagestate.state import PageState
from djblets.util.http import encode_etag

if TYPE_CHECKING:
    from typing import Callable

    from django.http import HttpRequest, HttpResponseBase


def PageStateMiddleware(
    get_response: Callable[[HttpRequest], HttpResponseBase],
) -> Callable[[HttpRequest], HttpResponseBase]:
    """Middleware for updating ETags with those from page state injections.

    Version Added:
        5.3

    Args:
        get_response (callable):
            The function for getting a response from a request.

    Returns:
        callable:
        The middleware callable for processing the request.
    """
    def _middleware(
        request: HttpRequest,
    ) -> HttpResponseBase:
        """Process the HTTP response.

        If the response contains an ETag, any injected ETag data in the
        page state will be merged into it.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

        Returns:
            django.http.HttpResponseBase:
            The resulting HTTP response.
        """
        response = get_response(request)

        if ((old_etag := response.headers.get('ETag')) and
            (page_state := PageState.for_request(request,
                                                 only_if_exists=True)) and
            (injected_etag := page_state.get_etag())):
            # Merge the existing ETag and new one together.
            new_etag = encode_etag(''.join([
                old_etag,
                injected_etag,
            ]).encode('utf-8'))

            response['ETag'] = new_etag

        return response

    return _middleware
