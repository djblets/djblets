"""Middleware for extensions."""

import threading

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

from djblets.extensions.manager import get_extension_managers


class ExtensionsMiddleware(MiddlewareMixin):
    """Middleware to manage extension lifecycles and data."""

    def __init__(self, *args, **kwargs):
        """Initialize the middleware.

        Args:
            *args (tuple):
                Positional arguments to pass through to the superclass.

            **kwargs (dict):
                Keyword arguments to pass through to the superclass.
        """
        super(ExtensionsMiddleware, self).__init__(*args, **kwargs)

        self.do_expiration_checks = not getattr(settings, 'RUNNING_TEST',
                                                False)
        self._lock = threading.Lock()

    def process_request(self, request):
        if self.do_expiration_checks:
            self._check_expired()

    def process_view(self, request, view, args, kwargs):
        request._djblets_extensions_kwargs = kwargs

    def _check_expired(self):
        """Checks each ExtensionManager for expired extension state.

        When the list of extensions on an ExtensionManager changes, or when
        the configuration of an extension changes, any other threads/processes
        holding onto extensions and configuration will go stale. This function
        will check each of those to see if they need to re-load their
        state.

        This is meant to be called before every HTTP request.
        """
        for extension_manager in get_extension_managers():
            # We're going to check the expiration, and then only lock if it's
            # expired. Following that, we'll check again.
            #
            # We do this in order to prevent locking unnecessarily, which could
            # impact performance or cause a problem if a thread is stuck.
            #
            # We're checking the expiration twice to prevent every blocked
            # thread from making its own attempt to reload the extensions once
            # the first thread holding the lock finishes the reload.
            if extension_manager.is_expired():
                with self._lock:
                    # Check again, since another thread may have already
                    # reloaded.
                    if extension_manager.is_expired():
                        extension_manager.load(full_reload=True)


class ExtensionsMiddlewareRunner(MiddlewareMixin):
    """Middleware to execute middleware from extensions.

    The process_*() methods iterate over all extensions' middleware, calling
    the given method if it exists. The semantics of how Django executes each
    method are preserved.

    This middleware should be loaded after the main extension middleware
    (djblets.extensions.middleware.ExtensionsMiddleware). It's probably
    a good idea to have it be at the very end so that everything else in the
    core that needs to be initialized is done before any extension's
    middleware is run.
    """

    def process_view(self, request, view_func, view_args, view_kwargs):
        """Process a view through extension middleware.

        Args:
            request (django.http.HttpRequest):
                The request object.

            view_func (callable):
                The view callable.

            view_args (list):
                Positional arguments to pass to the view.

            view_kwargs (dict):
                Keyword arguments to pass to the view.

        Returns:
            django.http.HttpResponse or None:
            Either a response object (in which case other middleware will not
            be run), or None.
        """
        for cls in self._middleware_classes:
            middleware = cls(self.get_response)

            if hasattr(middleware, 'process_view'):
                result = middleware.process_view(request, view_func, view_args,
                                                 view_kwargs)

                if result:
                    return result

        return None

    def process_template_response(self, request, response):
        """Process a template response through extension middleware.

        Args:
            request (django.http.HttpRequest):
                The request object.

            response (django.http.HttpResponse):
                The response from the view.

        Returns:
            django.template.response.TemplateResponse:
            A new template response to execute.
        """
        for cls in self._middleware_classes:
            middleware = cls(self.get_response)

            if hasattr(middleware, 'process_template_response'):
                response = middleware.process_template_response(
                    request, response)

        return response

    def process_exception(self, request, exception):
        """Process an exception through extension middleware.

        Args:
            request (django.http.HttpRequest):
                The request object.

            exception (Exception):
                The exception to process.

        Returns:
            django.http.HttpResponse or None:
            Either a response object (in which case other middleware will not
            be run), or None.
        """
        for cls in self._middleware_classes:
            middleware = cls(self.get_response)

            if hasattr(middleware, 'process_exception'):
                result = middleware.process_exception(request, exception)

                if result:
                    return result

        return None

    def __call__(self, request):
        """Run extension middleware.

        Args:
            request (django.http.HttpRequest):
                The HTTP request object.

        Returns:
            django.http.HttpResponse:
            The HTTP response.
        """
        middleware = list(self._middleware_classes)
        middleware.reverse()

        def _get_response_iter(request, middleware=middleware):
            try:
                next_method = middleware.pop(0)(_get_response_iter)
            except IndexError:
                next_method = self.get_response

            return next_method(request)

        return _get_response_iter(request)

    @property
    def _middleware_classes(self):
        """All extension-provided middleware.

        Yields:
            callable:
            Extension-provided middleware (either class or function).
        """
        for mgr in get_extension_managers():
            for middleware in mgr.middleware_classes:
                yield middleware
