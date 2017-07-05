"""Mixin for class-based views that support ETags."""

from __future__ import unicode_literals

from django.http import HttpResponseNotModified

from djblets.util.http import encode_etag, set_etag, etag_if_none_match


class ETagViewMixin(object):
    """Mixin to handle ETag generation for a page.

    This enables ETag support in the view for HTTP GET requests. On a request,
    :py:meth:`get_etag_data` will be called, which will calculate an ETag for
    the content. If the client already knows this ETag, it will receive a
    :http:`304`. Otherwise, it will return a response with that ETag attached.

    This currently only supports ETags for HTTP GET and HEAD methods.
    """

    def dispatch(self, request, *args, **kwargs):
        """Handle a HTTP request and dispatch to a handler.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple):
                Positional arguments passed to the handler.

            **kwargs (dict):
                Keyword arguments passed to the handler.

        Returns:
            django.http.HttpResponse:
            The resulting HTTP response from the handler.
        """
        handle_etag = request.method.upper() in ('GET', 'HEAD')

        if handle_etag:
            etag = self.get_etag_data(request, *args, **kwargs)

            if etag:
                etag = encode_etag(etag)

                if etag_if_none_match(request, etag):
                    return HttpResponseNotModified()

        response = super(ETagViewMixin, self).dispatch(request, *args,
                                                       **kwargs)

        if handle_etag and etag and 200 <= response.status_code < 300:
            set_etag(response, etag)

        return response
