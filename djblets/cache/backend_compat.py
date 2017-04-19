"""Compatibility functions for older Django cache backend configuration.

These functions are used to maintain compatibility or transition settings from
older versions of Django.
"""

from __future__ import unicode_literals

import logging

from django.core.cache import DEFAULT_CACHE_ALIAS, InvalidCacheBackendError

try:
    from django.core.cache import parse_backend_uri
except ImportError:
    from djblets.util.compat.django.core.cache import parse_backend_uri


logger = logging.getLogger(__name__)


BACKEND_CLASSES = {
    'db': 'db.DatabaseCache',
    'dummy': 'dummy.DummyCache',
    'file': 'filebased.FileBasedCache',
    'locmem': 'locmem.LocMemCache',
    'memcached': 'memcached.MemcachedCache',
}

RENAMED_BACKENDS = {
    'django.core.cache.backends.memcached.CacheClass':
        'django.core.cache.backends.memcached.MemcachedCache',
}


def normalize_cache_backend(cache_backend, cache_name=DEFAULT_CACHE_ALIAS):
    """Return a new-style ``CACHES`` dictionary from any given cache_backend.

    Over time, Django has had support for two formats for a cache backend. The
    old-style :django:setting:`CACHE_BACKEND` string, and the new-style
    :django:setting:`CACHES` dictionary.

    This function will accept either as input and return a dictionary
    containing a single normalized entry for the given cache backend. This can
    be merged into the existing :django:setting:`CACHES` setting.

    If a :django:setting:`CACHES` dictionary is passed, the "default" cache
    will be the result.

    Args:
        cache_backend (dict or str):
            The new-style or old-style cache backend dictionary or str to
            normalize.

        cache_name (str):
            The name of the cache backend to look up in ``cache_backend``, if
            a new-style dictionary is provided.

    Returns:
        A new-style cache backend dictionary containing the single cache
        backend referenced. If there were any parsing issues, an empty
        dictionary will be returned.
    """
    if not cache_backend:
        return {}

    if isinstance(cache_backend, dict):
        backend_info = cache_backend.get(cache_name, {})
        backend_name = backend_info.get('BACKEND')

        if backend_name in RENAMED_BACKENDS:
            backend_info['BACKEND'] = RENAMED_BACKENDS[backend_name]

        return backend_info

    try:
        engine, host, params = parse_backend_uri(cache_backend)
    except InvalidCacheBackendError as e:
        logger.error('Invalid cache backend (%s) found while loading '
                     'siteconfig: %s',
                     cache_backend, e)
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
