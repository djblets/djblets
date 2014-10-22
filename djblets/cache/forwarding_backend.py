from __future__ import unicode_literals

from django.core.signals import request_finished


DEFAULT_FORWARD_CACHE_ALIAS = 'forwarded_backend'


class ForwardingCacheBackend(object):
    """Forwards requests to another cache backend.

    This is used to allow for dynamic configuration of caches that can be
    swapped in and out. By setting this cache backend as the default backend,
    the consumer can easily switch between other cache backends without
    modifying settings.py and restarting the app.

    This by default looks for another cache backend in
    ``settings.CACHES['forwarded_backend']``. This can be changed with the
    ``LOCATION`` setting for this cache backend. All requests and attribute
    lookups will be forwarded there.

    If a consumer switches the real cache backend, it can call
    ``reset_backend()``, and all future cache requests will go to the
    newly computed backend.
    """
    def __init__(self, cache_name=DEFAULT_FORWARD_CACHE_ALIAS,
                 *args, **kwargs):
        self._cache_name = cache_name
        self._backend = None

    @property
    def backend(self):
        """Returns the forwarded cache backend."""
        if not self._backend:
            from django.core.cache import get_cache

            self._backend = get_cache(self._cache_name)

            # get_cache will attempt to connect to 'close', which we don't
            # want. Instead, go and disconnect this.
            request_finished.disconnect(self._backend.close)

        return self._backend

    def reset_backend(self):
        """Resets the forwarded cache backend.

        This must be called after modifying
        ``settings.CACHES['forwarded_backend']`` in order for the new
        backend to be picked up.
        """
        if self._backend:
            self._backend.close()
            self._backend = None

    def close(self, *args, **kwargs):
        """Closes the cache backend."""
        if self._backend:
            self._backend.close(*args, **kwargs)

    def __contains__(self, key):
        return key in self.backend

    def __getattribute__(self, name):
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            return self.backend.__getattribute__(name)
