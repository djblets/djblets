"""A cache backend that forwards to other dynamically-configured backends."""

DEFAULT_FORWARD_CACHE_ALIAS = 'forwarded_backend'


class ForwardingCacheBackend(object):
    """Forwards requests to another cache backend.

    This is used to allow for dynamic configuration of caches that can be
    swapped in and out. By setting this cache backend as the default backend,
    the consumer can easily switch between other cache backends without
    modifying :file:`settings.py` and restarting the app.

    This by default looks for another cache backend in
    ``settings.CACHES['forwarded_backend']``. This can be changed with the
    ``LOCATION`` setting for this cache backend. All requests and attribute
    lookups will be forwarded there.

    If a consumer switches the real cache backend, it can call
    :py:meth:`reset_backend`, and all future cache requests will go to the
    newly computed backend.
    """

    def __init__(self, cache_name=DEFAULT_FORWARD_CACHE_ALIAS,
                 *args, **kwargs):
        self._cache_name = cache_name

    @property
    def backend(self):
        """Return the forwarded cache backend."""
        from django.core.cache import caches

        return caches[self._cache_name]

    def reset_backend(self):
        """Reset the forwarded cache backend.

        This must be called after modifying
        ``settings.CACHES['forwarded_backend']`` in order for the new
        backend to be picked up.
        """
        from django.core.cache import caches

        try:
            del caches[self._cache_name]
        except Exception:
            # We don't really care if this fails. It probably means the
            # configuration was already deleted. The next access will recreate
            # it.
            pass

    def __contains__(self, key):
        return key in self.backend

    def __getattribute__(self, name):
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            return self.backend.__getattribute__(name)
