import logging

from django.core.cache import DEFAULT_CACHE_ALIAS, parse_backend_uri, \
                              InvalidCacheBackendError


BACKEND_CLASSES = {
    'db': 'db.DatabaseCache',
    'dummy': 'dummy.DummyCache',
    'file': 'filebased.FileBasedCache',
    'locmem': 'locmem.LocMemCache',
    'memcached': 'memcached.CacheClass',
}


def normalize_cache_backend(cache_backend):
    """Returns a new-style CACHES dictionary from any given cache_backend.

    Django has supported two formats for a cache backend. The old-style
    CACHE_BACKEND string, and the new-style CACHES dictionary.

    This function will accept either as input and return a cahe backend in the
    form of a CACHES dictionary as a result. The result won't be a full-on
    CACHES, with named cache entries inside. Rather, it will be a cache entry.

    If a CACHES dictionary is passed, the "default" cache will be the result.
    """
    if not cache_backend:
        return {}

    if isinstance(cache_backend, dict):
        if DEFAULT_CACHE_ALIAS in cache_backend:
            return cache_backend[DEFAULT_CACHE_ALIAS]

        return {}

    try:
        engine, host, params = parse_backend_uri(cache_backend)
    except InvalidCacheBackendError, e:
        logging.error('Invalid cache backend (%s) found while loading '
                      'siteconfig: %s' % (cache_backend, e))
        return {}

    if engine in BACKEND_CLASSES:
        engine = 'django.core.cache.backends.%s' % BACKEND_CLASSES[engine]
    else:
        engine = '%s.CacheClass' % engine

    defaults = {
        'BACKEND': engine,
        'LOCATION': host,
    }
    defaults.update(params)

    return defaults
