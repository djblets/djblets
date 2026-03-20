.. _caching-data:

============
Caching Data
============

.. py:currentmodule:: djblets.cache.backend

Djblets provides a pair of utility functions on top of
:external+django:doc:`Django's cache framework <topics/cache>`
for storing computed values and large datasets:

* :py:func:`cache_memoize`
* :py:func:`cache_memoize_iter`

These build upon what's provided in Django to help handle a variety of
cache needs in more advanced applications, covering:

* Key normalization (including namespacing across Django sites, protection
  against unsafe input, and workarounds for cache key size constraints)

* Chunking and compression of large data

* Storage and retrieval of iterable sets of data

* Optional encryption of cache keys and data

* Optional locking of cache operations across processes/servers


Caching a Single Value
======================

:py:func:`cache_memoize` takes a pre-normalized cache key and a function
that generates the data to store.

If the key already exists in cache, it will return the value as-is. Otherwise
it'll call the function, take the result, and store it in cache.

.. code-block:: python

   from djblets.cache.backend import cache_memoize


   def get_expensive_value() -> str:
       return cache_memoize(
           'my-expensive-value',
           lambda: some_slow_computation(),
       )


The function argument can be any zero-argument callable, including a plain
lambda, a bound method, or :py:func:`functools.partial`.

By default, values are cached for 30 days. This can be changed per-call with
``expiration``:

.. code-block:: python

   result = cache_memoize(
       'my-value',
       compute_value_func,
       expiration=60 * 60,  # 1 hour
   )


The global default expiration can also be changed by setting
:setting:`CACHE_EXPIRATION_TIME` to a number of seconds.


Caching Iterables and Generators
================================

:py:func:`cache_memoize_iter` is designed for caching the output of a
generator or any iterable. It always stores data in chunked form, making it
well suited for large result sets.

This function takes all the same options that :py:func:`cache_memoize` does,
allowing for key normalization, encryption, compression, and more.

The second argument can be an iterable (list, queryset, generator) or a
callable that returns one:

.. code-block:: python

   from typing import Iterator

   from djblets.cache.backend import cache_memoize_iter


   def get_all_items() -> Iterator[Item]:
       return cache_memoize_iter(
           'all-items',
           lambda: Item.objects.all(),
       )

The return value is always a generator.

.. important::

   Always consume the generator completely, or later data from the
   generator won't be stored in the cache. This **will** lead to corruption
   when next retrieving the data.

If the callable itself is a generator function, items are yielded to the
caller as they are produced, and cached in the background:

.. code-block:: python

   def fetch_items_generator() -> Iterator[Item]:
       ...


   def process_items() -> None:
       for item in cache_memoize_iter('all-items', fetch_items_generator):
           handle(item)


Caching Capabilities
====================

Both :py:func:`cache_memoize` and :py:func:`cache_memoize_iter` provide a
number of capabilities to control how data is cached.


Force-Refreshing a Value
------------------------

To bypass the cache and always recompute a fresh value, pass
``force_overwrite=True``. The result will be stored over any existing cached
entry:

.. code-block:: python

   result = cache_memoize(
       'my-key',
       compute_value_func,
       force_overwrite=True,
   )

   result = cache_memoize_iter(
       'my-iter-key',
       compute_value_iter,
       force_overwrite=True,
   )


Storing Large Data
------------------

Django's default cache backends (including memcached) have a per-entry size
limit of around 1MB. This can cause failures when trying to cache large data.

When storing data that may be larger than this, pass ``large_data=True`` to
:py:func:`cache_memoize` (this is always enabled for
:py:func:`cache_memoize_iter`).

Djblets will serialize and compress the value and automatically split it
across as multiple cache entries:

.. code-block:: python

   result = cache_memoize(
       'big-report',
       build_report,
       large_data=True,
   )

Compression is enabled by default and can be turned off using
``compress_large_data=False``, though this is rarely useful since compression
typically reduces both cache consumption and retrieval time for large data.


Coordinating Writes with a Cache Lock
-------------------------------------

.. versionadded:: 5.3

In multi-process or multi-threaded deployments, multiple workers may
simultaneously detect a cache miss and attempt to recompute the same value.

Passing a :py:class:`~djblets.protect.locks.CacheLock` prevents this stampede
by letting only the first worker compute and populate the value while others
wait and then read the freshly cached result:

.. code-block:: python

   from djblets.cache.backend import cache_memoize
   from djblets.protect.locks import CacheLock


   result = cache_memoize(
       'my-key',
       compute_value_func,
       lock=CacheLock('my-key-lock'),
   )

   result = cache_memoize_iter(
       'my-iter-key',
       compute_value_iter,
       lock=CacheLock('my-iter-key-lock'),
   )

.. note::

   This is a soft lock, which makes a best-attempt at locking. It uses the
   cache backend to manage the lock, which memcached is not designed for.

   Because of this, there is still a possibility that under heavy load,
   multiple processes/servers may end up computing and caching the same state
   at the same time. Even in this case, most callers will still wait for
   the lock to be released, and will then retrieve the cached value.


.. _caching-data-encryption:

Encrypting Cached Keys and Values
---------------------------------

.. versionadded:: 3.0

Both functions support optional AES encryption of stored keys and values.
This is useful when the cache may be shared between services or when the
cached data is sensitive.

To enable encryption for a specific call, pass ``use_encryption=True``:

.. code-block:: python

   result = cache_memoize(
       'my-key',
       fetch_sensitive_data,
       use_encryption=True,
   )

   result = cache_memoize_iter(
       'my-iter-key',
       fetch_sensitive_data_iter,
       use_encryption=True,
   )

Neither the cache key nor the data will be readable or guessable without
access to the encryption key.

The default encryption key comes from
:setting:`DJBLETS_CACHE_DEFAULT_ENCRYPTION_KEY` if set, and otherwise falls
back to the server's default AES key (see
:py:func:`~djblets.secrets.crypto.get_default_aes_encryption_key`).

You can also supply an explicit key:

.. code-block:: python

   result = cache_memoize(
       'my-key',
       fetch_sensitive_data,
       use_encryption=True,
       encryption_key=b'my-32-byte-aes-key-here.........',
   )

   result = cache_memoize_iter(
       'my-iter-key',
       fetch_sensitive_data_iter,
       use_encryption=True,
       encryption_key=b'my-32-byte-aes-key-here.........',
   )

To enforce encryption for *all* cache operations across the entire
application, set :setting:`DJBLETS_CACHE_FORCE_ENCRYPTION` to ``True``. No
per-call changes are needed.
