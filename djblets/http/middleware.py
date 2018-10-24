"""Middleware for HTTP-related processing."""

from __future__ import unicode_literals

import django


_uses_relative_redirects = (django.VERSION >= (1, 9))


class AbsoluteURLRedirectMiddleware(object):
    """Middleware that turns all relative URL redirects to absolute.

    Django 1.9 changed URL redirects to be relative by default (so long as
    they're redirecting to the same host). For compatibility across Django
    versions (and to theoretically work around some broken HTTP implementations
    out in the wild), this middleware will turn those relative URLs back into
    absolute URLs.
    """

    def process_response(self, request, response):
        """Process the HTTP response.

        If a relative redirect was returned, this will make it absolute.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            response (django.http.HttpResponse):
                The HTTP response to check.

        Returns:
            django.http.HttpResponse:
            The resulting HTTP response.
        """
        if (_uses_relative_redirects and
            'Location' in response and
            request.get_host()):
            # Convert the relative URL into an absolute one.
            response['Location'] = \
                request.build_absolute_uri(response['Location'])

        return response
