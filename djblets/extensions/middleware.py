class ExtensionsMiddleware(object):
    """Middleware that takes the kwargs dict passed to a view, and
    stashes it into the request.
    """
    def process_view(self, request, view, args, kwargs):
        request._djblets_extensions_kwargs = kwargs
