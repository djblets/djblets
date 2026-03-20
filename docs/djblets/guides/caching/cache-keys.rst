.. _cache-keys:

=======================
Working with Cache Keys
=======================

.. py:currentmodule:: djblets.cache.backend

Django cache backends impose some constraints on keys:

* Maximum key lengths (typically 250 characters for memcached)
* Strict sets of allowed characters in keys

All call sites have to take care to meet those requirements, while avoiding
collisions with any other sites or services using the caching server, and
protecting from potentially unsafe input in cache keys.

Djblets provides :py:func:`make_cache_key`, which takes care of:

* Keeping cache keys within the length limit (turning long keys into a
  SHA256 hash)

* Normalizing unsafe characters (while avoiding collisions)

* Prefixing keys by site name and the :setting:`SITE_ROOT` setting
  (helping avoid conflicts)

* Safely building a key based on dynamic (potentially unsafe) input

* Optionally encrypting the cache key


Creating a Cache Key
====================

To create a cache key, use :py:func:`make_cache_key` and pass in the
pre-normalized key name:

.. code-block:: python

   from djblets.cache.backend import make_cache_key


   key = make_cache_key('my-key')

The resulting key will be prefixed with the current site's domain (from
:external+django:doc:`Django's Sites framework <ref/contrib/sites>`), and
optionally with the :setting:`SITE_ROOT` seting if set, so that separate
deployments sharing a cache server don't collide:

.. code-block:: text

   example.com:/:my-key

Keys containing control characters or whitespace will be safely escaped,
meeting the backend's requirements.

Keys longer than 240 characters will be converted into a SHA256 hash.

.. note::

   :py:func:`cache_memoize` and :py:func:`cache_memoize_iter` call
   :py:func:`make_cache_key` internally. You rarely need to call it yourself
   unless you are working with the cache directly (for example, if you're
   deleting cache keys).


Preventing Unsafe Input
=======================

.. versionadded:: 5.3

When any component of a key comes from dynamically-generated input (e.g.,
a username or team name), there's the potential for a cache key that might
conflict with another. This can easily be the case if the input contains
a key component separation character (such as ``:``) or a character ``%``
(such as ``%s``).

To avoid this, pass a key as a list of strings instead. Each string in the
list will be carefully escaped and joined together, resulting in a safe cache
key.

.. code-block:: python

   from djblets.cache.backend import make_cache_key


   username = 'my-user'
   namespace = 'un%safe:key'

   key = make_cache_key(['user-profile', username, namespace])

This will result in a final key that looks like:

.. code-block:: text

   example.com:/:user-profile:my-user:un%25safe%3Akey

This can be passed to any of Djblets's other cache functions, such as
:py:func:`cache_memoize` and :py:func:`cache_memoize_iter`:

.. code-block:: python

   from djblets.cache.backend import cache_memoize


   result = cache_memoize(
       ['user-profile', username],
       lambda: build_profile(username),
   )


Encrypting Keys
===============

.. versionadded:: 3.0

Storing a readable key in the cache backend can reveal information about
application internals or user data to anyone with access to the cache server.

Passing ``use_encryption=True`` replaces the key with an HMAC-SHA256 digest,
so no identifying information is visible in the backend:

.. code-block:: python

   key = make_cache_key(
       ['sensitive-resource', resource_id],
       use_encryption=True,
   )

The HMAC is computed using the server's AES encryption key (see
:py:func:`~djblets.secrets.crypto.get_default_aes_encryption_key`), or an
explicit key supplied via ``encryption_key``.

To enable this globally for all Djblets-controlled cache keys, set
:setting:`DJBLETS_CACHE_FORCE_ENCRYPTION` to ``True``.
