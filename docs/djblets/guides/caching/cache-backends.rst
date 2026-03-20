.. _cache-backends:

==============
Cache Backends
==============

Forwarding Backend
==================

.. py:currentmodule:: djblets.cache.forwarding_backend

If your application needs to swap the active cache backend at runtime (for
example, when offering configuration to change the cache server list or to
switch between Memcached and Redis), you can make use of
:py:class:`ForwardingCacheBackend` to send cache requests to another backend.

Any operations on this backend will be forwarded to another configured
backend. This backend can then be swapped out at runtime, without restarting
the server.


Configuration
-------------

To configure this backend, place the following in :file:`settings.py`:

.. code-block:: python

   CACHES = {
       'default': {
           'BACKEND': 'djblets.cache.forwarding_backend.ForwardingCacheBackend',
       },
       'forwarded_backend': {
           'BACKEND': 'django.core.cache.backends.memcache.PyMemcacheCache',
           'LOCATION': '127.0.0.1:11211',
       },
   }

You'll typically set this as the ``default`` cache, and will forward to
``forwarded_backend``.

You can place :py:class:`ForwardingCacheBackend` under any name, and change
the backend it forwards to by setting its ``LOCATION`` option. For example:

.. code-block:: python

   CACHES = {
       'special_backend': {
           'BACKEND': 'djblets.cache.forwarding_backend.ForwardingCacheBackend',
           'LOCATION': 'other_backend',
       },
       'other_backend': {
           'BACKEND': 'django.core.cache.backends.memcache.PyMemcacheCache',
           'LOCATION': '127.0.0.1:11211',
       },
   }


Forwarding to a New Backend
---------------------------

If the application updates the ``forwarded_backend`` cache backend, it must
then call :py:meth:`~ForwardingCacheBackend.reset_backend` to ensure the
forwarding backend will pick up the new configuration.

For example:

.. code-block:: python

   from django.conf import settings
   from django.core.cache import cache


   # Set a new forwarded cache backend.
   settings.CACHES['forwarded_backend'] = {
       'BACKEND': 'django.core.cache.backends.redis.RedisCache',
       'LOCATION': 'redis://127.0.0.1:6379',
   }

   # Force the forwarding backend to update its settings.
   cache.reset_backend()
