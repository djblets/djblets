"""Utility functions for working with memory caching backends.

These functions are designed to integrate with a cache backend using
Django's cache framework. They handle creating caching keys unique to the
install and caching more complex data efficiently (such as the results of
iterators and large data normally too big for the cache).
"""

import hashlib
import hmac
import io
import logging
import pickle
import re
import zlib

from django.conf import settings
from django.core.cache import cache
from django.contrib.sites.models import Site
from django.utils.encoding import force_bytes

from djblets.cache.errors import MissingChunkError
from djblets.secrets.crypto import (aes_decrypt,
                                    aes_decrypt_iter,
                                    aes_encrypt,
                                    aes_encrypt_iter,
                                    get_default_aes_encryption_key)


logger = logging.getLogger(__name__)


DEFAULT_EXPIRATION_TIME = 60 * 60 * 24 * 30  # 1 month
CACHE_CHUNK_SIZE = 2 ** 20 - 1024  # almost 1M (memcached's slab limit)

# memcached key size constraint (typically 250, but leave a few bytes for the
# large data handling)
MAX_KEY_SIZE = 240

_INVALID_KEY_CHARS_RE = re.compile(r'[\x00-\x20\x7f]')

_NO_RESULTS = object()

_default_expiration = getattr(settings, 'CACHE_EXPIRATION_TIME',
                              DEFAULT_EXPIRATION_TIME)


class _CacheContext:
    """State and functions for performing a cache-related operation.

    This is created internally by :py:func:`cache_memoize` and
    :py:func:`cache_memoize_iter`, and ensures consistency in cache key
    names, timeouts, and state storage, simplifying the operations
    responsible for loading and saving complex cache data.

    Version Added:
        3.0
    """

    def __init__(self, cache, base_cache_key, expiration, compress_large_data,
                 use_encryption, encryption_key):
        """Initialize the context.

        Args:
            cache (object):
                The Django cache connection that all operations will work
                on. This is considered opaque.

            base_cache_key (str):
                The base cache key for caching operations.

                This is the value passed in to ::py:func:`cache_memoize` or
                 :py:func:`cache_memoize_iter`, and will be used when
                 constructing related cache keys.

            expiration (int):
                The expiration time in seconds for all data cached using
                this context.

            compress_large_data (bool):
                Whether large data will be compressed.

            use_encryption (bool):
                Whether to use encryption when storing or reading data.

                This defaults to ``False``, but can be forced on for all
                cached data by setting
                ``settings.DJBLETS_CACHE_FORCE_ENCRYPTION=True``.

            encryption_key (bytes or str):
                An explicit AES encryption key to use when passing
                ``use_encryption=True``.

                This defaults to the value in
                ``settings.DJBLETS_CACHE_DEFAULT_ENCRYPTION_KEY``, if set, or
                to the default AES encryption key for the server as provided by
                :py:func:`djblets.secrets.crypto.
                get_default_aes_encryption_key`.
        """
        if use_encryption is None:
            use_encryption = _get_default_use_encryption()

        if use_encryption:
            if encryption_key:
                assert isinstance(encryption_key, bytes)
            else:
                encryption_key = _get_default_encryption_key()
        else:
            encryption_key = None

        self.cache = cache
        self.expiration = expiration
        self.full_cache_key = None
        self.base_cache_key = base_cache_key
        self.use_encryption = use_encryption
        self.encryption_key = encryption_key
        self.compress_large_data = compress_large_data

        self.full_cache_key = self.make_key(base_cache_key)

    def make_key(self, key):
        """Return a full cache key from the provided base key.

        Args:
            key (str):
                The base cache key to make a full key from.

        Returns:
            str:
            The full cache key.
        """
        if key == self.base_cache_key and self.full_cache_key:
            return self.full_cache_key

        return make_cache_key(key,
                              use_encryption=self.use_encryption,
                              encryption_key=self.encryption_key)

    def make_subkey(self, suffix):
        """Return a full cache key combining the main key and a suffix.

        The key will be built in the form of :samp:`{mainkey}-{suffix}`, and
        will then be converted into a full cache key.

        Args:
            suffix (int or str):
                The suffix to append to the cache key.

        Returns:
            str:
            The full cache key in the form of ``<mainkey>-<suffix>``.
        """
        return self.make_key('%s-%s' % (self.base_cache_key, suffix))

    def prepare_value(self, full_cache_key, value):
        """Prepare a value for storage in cache.

        If using encryption, this will serialize and encrypt the value.
        Otherwise this returns the value as-is.

        Args:
            full_cache_key (str):
                The full cache key where this value will be stored.

            value (object):
                The value to cache.

        Returns:
            object:
            The prepared value.

        Raises:
            Exception:
                An error occurred pickling or encrypting the value. The
                The exception is logged and then raised as-is.
        """
        if self.use_encryption:
            # Normally Django's cache backends will handle pickling of data,
            # so what we set is what we get. That doesn't work when we encrypt
            # data, though, since the type information will be lost. Plus,
            # we need to be able to give a bytestring representation to
            # aes_encrypt().
            #
            # So we instead pickle the data before encrypting it, and then we
            # unpickle after we decrypt it later.
            try:
                value = pickle.dumps(value, protocol=0)
            except Exception as e:
                logger.error('Failed to serialize data for cache key "%s": %s',
                             full_cache_key, e)
                raise

            try:
                value = aes_encrypt(value, key=self.encryption_key)
            except Exception as e:
                logger.error('Failed to encrypt data for cache for key '
                             '%s: %s.',
                             full_cache_key, e)
                raise

        return value

    def load_value(self, key=None):
        """Load a value from cache.

        This will take care of converting the provided key to a full cache
        key, and decrypting and deserializing the value if needed.

        Args:
            key (str):
                The full cache key to load from cache.

                If not provided, the full main cache key will be used.

        Returns:
            object:
            The value from the cache, or :py:data:`_NO_RESULTS` if not found.

        Raises:
            Exception:
                An error occurred reading from cache or processing results.
                The exception is raised as-is.
        """
        if key is None:
            key = self.full_cache_key

        value = self.cache.get(key, _NO_RESULTS)

        if value is not _NO_RESULTS and self.use_encryption:
            try:
                value = aes_decrypt(value, key=self.encryption_key)
            except Exception as e:
                logger.error('Failed to decrypt data from cache for '
                             'key %s: %s.',
                             key, e)
                raise

            try:
                value = pickle.loads(value)
            except Exception as e:
                logger.warning('Failed to deserialize data from cache for '
                               'key %s: %s.',
                               key, e)
                raise

        return value

    def store_value(self, value, *, key=None, raw=False):
        """Store a value in cache.

        This will take care of preparing any values to be stored, if needed.

        Args:
            value (object):
                The value to store in cache.

            key (str, optional):
                The full cache key to save to cache.

                If not provided, the full main cache key will be used.

            raw (bool, optional):
                Whether to store the value directly without modifications.

        Raises:
            Exception:
                An error occurred preparing the value or writing to cache.
                The exception is raised as-is.
        """
        if key is None:
            key = self.full_cache_key

        if not raw:
            value = self.prepare_value(key, value)

        self.cache.set(key, value,
                       timeout=self.expiration)

    def store_many(self, items):
        """Store many items directly to cache.

        All keys should be full cache keys, and all values should be prepared
        already.

        Args:
            items (dict):
                A dictionary of base cache keys to raw values to store.

        Raises:
            Exception:
                An error occurred preparing the value or writing to cache.
                The exception is raised as-is.
        """
        self.cache.set_many(items,
                            timeout=self.expiration)


def _get_default_use_encryption():
    """Return whether encryption should be enabled by default.

    This will dynamically check whether encryption should be allowed, based
    on the ``settings.DJBLETS_CACHE_FORCE_ENCRYPTION`` setting. If not set,
    this defaults to ``False``.

    Returns:
        bool:
        Whether encryption should be used by default.
    """
    return getattr(settings, 'DJBLETS_CACHE_FORCE_ENCRYPTION', False)


def _get_default_encryption_key():
    """Return the default AES encryption key for caching.

    This will return the default encryption key used for caching, using
    ``settings.DJBLETS_CACHE_DEFAULT_ENCRYPTION_KEY`` if set to a valid
    AES encryption key, and falling back to
    :py:func:`djblets.secrets.crypto.get_default_aes_encryption_key`.

    Returns:
        bytes:
        The default encryption key.
    """
    key = getattr(settings, 'DJBLETS_CACHE_DEFAULT_ENCRYPTION_KEY', None)

    if key:
        if not isinstance(key, bytes):
            key = key.encode('utf-8')
            settings.DJBLETS_CACHE_DEFAULT_ENCRYPTION_KEY = key
    else:
        key = get_default_aes_encryption_key()

    return key


def _cache_fetch_large_data(cache_context, chunk_count):
    """Fetch large data from the cache.

    The main cache key indicating the number of chunks will be read, followed
    by each of the chunks. If any chunks are missing, a
    :py:class:`~djblets.cache.errors.MissingChunkError` will be immediately
    raised.

    The data is then combined and optionally uncompressed, and returned to
    the caller. The caller should iterate through the results using
    :py:func:`_cache_iter_large_data`.

    Version Changed:
        3.0:
        * Updated to take ``cache_context`` instead of additional arguments,
          and ``chunk_count`` to save a cache hit.
        * Added support for key/value encryption.

    Args:
        cache_context (_CacheContext):
            The caching operation context.

        chunk_count (int):
            The number of chunks to fetch.

    Returns:
        bytes:
        The complete fetched data, ready for deserializing.

    Raises:
        djblets.cache.errors.MissingChunkError:
            A chunk of data was missing. All cached data for the key is
            invalid.

        Exception:
            An error occurred reading from cache or processing data. The
            exception is raised as-is.
    """
    # Fetch all the chunks at once.
    chunk_keys = [
        cache_context.make_subkey(i)
        for i in range(chunk_count)
    ]
    chunks = cache_context.cache.get_many(chunk_keys)

    # Check that we have all the keys we expect, before we begin generating
    # values. We don't want to waste effort loading anything, and we want to
    # pass an error about missing keys to the caller up-front before we
    # generate anything.
    if len(chunks) != chunk_count:
        missing_keys = sorted(set(chunk_keys) - set(chunks.keys()))
        missing_keys_str = ', '.join(missing_keys)
        logger.debug('Cache miss for key(s): %s.',
                     missing_keys_str)

        raise MissingChunkError

    # Process all the chunks.
    data = (
        chunks[chunk_key][0]
        for chunk_key in chunk_keys
    )

    if cache_context.use_encryption:
        # We can iteratively decrypt these and build the results into a
        # single string below for optional decompression.
        data = aes_decrypt_iter(data, key=cache_context.encryption_key)

    data = b''.join(data)

    # Decompress them all at once, instead of streaming the results. It's
    # faster for any reasonably-sized data in cache. We'll stream depickles
    # instead.
    if cache_context.compress_large_data:
        data = zlib.decompress(data)

    return data


def _cache_iter_large_data(cache_context, data):
    """Iterate through large data that was fetched from the cache.

    This will unpickle the large data previously fetched through
    :py:func:`_cache_fetch_large_data`, and yield each object to the caller.

    Version Changed:
        3.0:
        * Updated to take ``cache_context`` instead of additional arguments.
        * Added support for key/value encryption.

    Args:
        cache_context (_CacheContext):
            The caching operation context.

        data (bytes):
            The combined data fetched from cache.

    Yields:
        object:
        Each value from cache.

    Raises:
        Exception:
            An error occurred processing data. The exception is logged and
            then raised as-is.
    """
    fp = io.BytesIO(data)

    try:
        # Unpickle all the items we're expecting from the cached data.
        #
        # There will only be one item in the case of old-style cache data.
        while True:
            try:
                yield pickle.load(fp)
            except EOFError:
                return
    except Exception as e:
        logger.warning('Unpickle error for cache key "%s": %s.',
                       cache_context.full_cache_key, e)
        raise


def _cache_compress_pickled_data(items):
    """Compress lists of items for storage in the cache.

    This works with generators, and will take each item in the list or
    generator of items, zlib-compress the data, and store it in a buffer.The
    item and a blob of compressed data will be yielded to the caller.

    Args:
        items (generator of tuple):
            The generator of item tuples prepared in
            :py:func:`_cache_store_items`.

            Each is in the form of:

            1. Byte string to compress
            2. Boolean indicating if the raw data represents valid data to
               ultimately yield to the caller in :py:func:`cache_memoize_iter`
            3. Raw data to yield back to the caller

    Yields:
        tuple:
        An item tuple, but with the first entry containing compressed data.

        Each is in the form of:

        1. Byte string containing compressed data
        2. Boolean indicating if the raw data represents valid data to
           ultimately yield to the caller in :py:func:`cache_memoize_iter`
        3. Raw data to yield back to the caller
    """
    compressor = zlib.compressobj()

    for data, has_item, item in items:
        yield compressor.compress(data), has_item, item

    remaining = compressor.flush()

    if remaining:
        yield remaining, False, None


def _cache_encrypt_data(items, encryption_key):
    """Iteratively encrypt data from items tuples.

    Version Added:
        3.0

    Args:
        items (generator of tuple):
            The generator of item tuples prepared in
            :py:func:`_cache_store_items`.

            Each is in the form of:

            1. Byte string to encrypt
            2. Boolean indicating if the raw data represents valid data to
               ultimately yield to the caller in :py:func:`cache_memoize_iter`
            3. Raw data to yield back to the caller

        encryption_key (bytes, optional):
            The AES encryption key to use.

    Yields:
        tuple:
        Each is in the form of:

        1. Byte string containing encrypted data
        2. Boolean indicating if the raw data represents valid data to
           ultimately yield to the caller in :py:func:`cache_memoize_iter`
        3. Raw data to yield back to the caller
    """
    # We're working with a generator yielding tuples containing items.
    # The first entry in each tuple is a piece of the data we want to
    # encrypt. We want to encrypt iteratively, and we don't want to have
    # to load the entire results of the generator into memory at once.
    #
    # So we have to feed the first index of each tuple iteratively into
    # aes_encrypt_iter as a generator, but we also want to retain the other
    # data in each tuple and yield it along with the encrypted results.
    #
    # There isn't a one-to-one mapping between what goes in and what comes
    # out, particularly when dealing with compression.
    #
    # So here's the plan of attack:
    #
    # 1. We feed data into aes_encrypt_iter(), and keep a queue of the item
    #    data (has_item and item).
    #
    # 2. As we receive results, we pull off the front of the queue and yield
    #    it along with the data.
    #
    #    We then go through anything else in the queue (one item coming
    #    in could result in multiple coming out). Those yield those
    #    values, but without any data scheduled for storage, just scheduled
    #    to yield as results.
    #
    # 3. If there was nothing in the queue when we get data, then yield the
    #    data but with has_item=False, so it'll be stored but not yielded as
    #    results.
    item_queue = []

    def _gen_data():
        for data, has_item, item in items:
            item_queue.append((has_item, item))
            yield data

    for data in aes_encrypt_iter(_gen_data(),
                                 key=encryption_key):
        if item_queue:
            # There were items in the queue. Yield the first with the data,
            # and anything else without (those will be returned as results
            # but won't be stored in cache).
            yield (data,) + item_queue[0]

            for item in item_queue[1:]:
                yield (None,) + item
        else:
            # The queue is empty. Yield what data we have for caching, but
            # don't yield for results.
            yield data, False, None

        item_queue.clear()


def _cache_store_chunks(cache_context, items):
    """Store a list of items as chunks in the cache.

    The list of items will be combined into chunks and stored in the
    cache as efficiently as possible. Each item in the list will be
    yielded to the caller as it's fetched from the list or generator.

    Version Changed:
        3.0:
        * Updated to take ``cache_context`` instead of additional arguments.
        * Added support for encrypting keys and data through the
          ``use_encryption`` and ``encryption_key`` arguments.

    Args:
        cache_context (_CacheContext):
            The caching operation context.

        items (generator of tuple):
            The generator of item tuples prepared in
            :py:func:`_cache_store_items`.

            Each is in the form of:

            1. Byte string to store in cache
            2. Boolean indicating if the raw data represents valid data to
               ultimately yield to the caller in :py:func:`cache_memoize_iter`
            3. Raw data to yield back to the caller

    Yields:
        object:
        Each chunk of original, unmodified item data being cached.
    """
    chunks_data = io.BytesIO()
    chunks_data_len = 0
    read_start = 0
    i = 0

    for data, has_item, item in items:
        if has_item:
            yield item

        if not data:
            continue

        chunks_data.write(data)
        chunks_data_len += len(data)

        if chunks_data_len > CACHE_CHUNK_SIZE:
            # We have enough data to fill a chunk now. Start processing
            # what we've stored and create cache keys for each chunk.
            # Anything remaining will be stored for the next round.
            chunks_data.seek(read_start)
            cached_data = {}

            while chunks_data_len > CACHE_CHUNK_SIZE:
                chunk = chunks_data.read(CACHE_CHUNK_SIZE)
                chunk_len = len(chunk)
                chunks_data_len -= chunk_len
                read_start += chunk_len

                # Note that we wrap the chunk in a list so that the cache
                # backend won't try to perform any conversion on the string.
                cached_data[cache_context.make_subkey(i)] = [chunk]
                i += 1

            # Store the keys in the cache in a single request.
            cache_context.store_many(cached_data)

            # Reposition back at the end of the stream.
            chunks_data.seek(0, io.SEEK_END)

    if chunks_data_len > 0:
        # There's one last bit of data to store. Note that this should be
        # less than the size of a chunk,
        assert chunks_data_len <= CACHE_CHUNK_SIZE

        chunks_data.seek(read_start)
        chunk = chunks_data.read()
        cache_context.store_value([chunk],
                                  key=cache_context.make_subkey(i),
                                  raw=True)
        i += 1

    # Store the final count.
    cache_context.store_value('%d' % i)


def _cache_store_items(cache_context, items):
    """Store items in the cache.

    The items will be individually pickled and combined into a binary blob,
    which can then optionally be compressed. The resulting data is then
    cached over one or more keys, each representing a chunk about 1MB in size.

    A main cache key will be set that contains information on the other keys.

    Version Changed:
        3.0:
        * Updated to take ``cache_context`` instead of additional arguments.
        * Added support for encrypting keys and data through the
          ``use_encryption`` and ``encryption_key`` arguments.

    Args:
        cache_context (_CacheContext):
            The caching operation context.

        items (generator):
            The generator of data to store.

    Yields:
        tuple:
        Each is in the form of:

        1. Byte string to store in the cache
        2. Boolean indicating if the raw data represents valid data to
           ultimately yield to the caller in :py:func:`cache_memoize_iter`
        3. Raw data to yield back to the caller
    """
    # Note that we want to use pickle protocol 0 in order to be compatible
    # across both Python 2 and 3. On Python 2, 0 is the default.
    results = (
        (pickle.dumps(item, protocol=0), True, item)
        for item in items
    )

    if cache_context.compress_large_data:
        results = _cache_compress_pickled_data(results)

    if cache_context.use_encryption:
        # Note that the order of operations here is important. We must
        # compress and *then* encrypt. Encrypted AES data cannot be
        # compressed.
        results = _cache_encrypt_data(
            results,
            encryption_key=cache_context.encryption_key)

    yield from _cache_store_chunks(cache_context=cache_context,
                                   items=results)


def cache_memoize_iter(key, items_or_callable,
                       expiration=_default_expiration,
                       force_overwrite=False,
                       compress_large_data=True,
                       use_encryption=None,
                       encryption_key=None):
    """Memoize an iterable list of items inside the configured cache.

    If the provided list of items is a function, the function must return a
    an iterable object, such as a list or a generator.

    If a generator is provided, directly or through a function, then each
    item will be immediately yielded to the caller as they're retrieved, and
    the cached entries will be built up as the items are processed.

    The data is assumed to be big enough that it must be pickled,
    optionally compressed, and stored as chunks in the cache.

    Data can be encrypted using AES encryption, for safe storage of potentially
    sensitive information or state. This adds to the processing time slightly,
    but can be important for cache keys containing sensitive information or
    that impact access control, particularly in the event that the cache is
    compromised or shared between services.

    The result from this function is always a generator. Note that it's
    important that the generator be allowed to continue until completion, or
    the data won't be retrievable from the cache.

    Version Changed:
        3.0:
        Added support for encrypting keys and data through the
        ``use_encryption`` and ``encryption_key`` arguments.

    Args:
        key (unicode):
            The key to use in the cache.

        items_or_callable (list or callable):
            A list of items or callable returning a list of items to cache,
            if the key is not already found in cache.

        expiration (int):
            The expiration time for the key, in seconds.

        force_overwrite (bool):
            If ``True``, the value will always be computed and stored
            regardless of whether it exists in the cache already.

        compress_large_data (bool):
            If ``True``, the data will be zlib-compressed.

        use_encryption (bool, optional):
            Whether to use encryption when storing or reading data.

            If reading data, and if the data cannot be decrypted with the
            given key, then the data will be considered to have fallen out
            of cache.

            This defaults to ``False``, but can be forced on for all cached
            data by setting ``settings.DJBLETS_CACHE_FORCE_ENCRYPTION=True``.

            Version Added:
                3.0

        encryption_key (bytes or str, optional):
            An explicit AES encryption key to use when passing
            ``use_encryption=True``.

            This defaults the value in
            ``settings.DJBLETS_CACHE_DEFAULT_ENCRYPTION_KEY``, if set, or to
            the default AES encryption key for the server as provided by
            :py:func:`djblets.secrets.crypto.get_default_aes_encryption_key`.

            Version Added:
                3.0

    Yields:
        object:
        The list of items from the cache or from ``items_or_callable`` if
        uncached.
    """
    cache_context = _CacheContext(
        cache=cache,
        base_cache_key=key,
        expiration=expiration,
        compress_large_data=compress_large_data,
        use_encryption=use_encryption,
        encryption_key=encryption_key)
    full_cache_key = cache_context.full_cache_key

    results = _NO_RESULTS

    if not force_overwrite:
        chunk_count = cache_context.load_value()

        if chunk_count is not _NO_RESULTS:
            try:
                results = _cache_iter_large_data(
                    cache_context=cache_context,
                    data=_cache_fetch_large_data(
                        cache_context=cache_context,
                        chunk_count=int(chunk_count)))
            except Exception as e:
                logger.warning('Failed to fetch large data from cache for '
                               'key "%s": %s',
                               full_cache_key, e)
                results = _NO_RESULTS
        else:
            logger.debug('Cache miss for key "%s"' % full_cache_key)

    if results is _NO_RESULTS:
        if callable(items_or_callable):
            items = items_or_callable()
        else:
            items = items_or_callable

        results = _cache_store_items(cache_context=cache_context,
                                     items=items)

    yield from results


def cache_memoize(key,
                  lookup_callable,
                  expiration=_default_expiration,
                  force_overwrite=False,
                  large_data=False,
                  compress_large_data=True,
                  use_generator=False,
                  use_encryption=None,
                  encryption_key=None):
    """Memoize the results of a callable inside the configured cache.

    Data can be encrypted using AES encryption, for safe storage of potentially
    sensitive information or state. This adds to the processing time slightly,
    but can be important for cache keys containing sensitive information or
    that impact access control, particularly in the event that the cache is
    compromised or shared between services.

    Version Changed:
        3.0:
        Added support for encrypting keys and data through the
        ``use_encryption`` and ``encryption_key`` arguments.

    Version Changed:
        2.2.4:
        Added support for non-iterable value types.

    Args:
        key (unicode):
            The key to use in the cache.

        lookup_callable (callable):
            A callable to execute in the case where the data did not exist in
            the cache.

        expiration (int):
            The expiration time for the key, in seconds.

        force_overwrite (bool):
            If ``True``, the value will always be computed and stored
            regardless of whether it exists in the cache already.

        large_data (bool):
            If ``True``, the resulting data will be pickled, gzipped, and
            (potentially) split up into megabyte-sized chunks. This is useful
            for very large, computationally intensive hunks of data which we
            don't want to store in a database due to the way things are
            accessed.

        compress_large_data (bool):
            Compresses the data with zlib compression when ``large_data``
            is ``True``.

        use_generator (bool, deprecated):
            This parameter is no longer used and will be removed in Djblets
            3.0.

        use_encryption (bool, optional):
            Whether to use encryption when storing or reading data.

            If reading data, and if the data cannot be decrypted with the
            given key, then the data will be considered to have fallen out
            of cache.

            This defaults to ``False``, but can be forced on for all cached
            data by setting ``settings.DJBLETS_CACHE_FORCE_ENCRYPTION=True``.

            Version Added:
                3.0

        encryption_key (bytes or str, optional):
            An explicit AES encryption key to use when passing
            ``use_encryption=True``.

            This defaults the value in
            ``settings.DJBLETS_CACHE_DEFAULT_ENCRYPTION_KEY``, if set, or to
            the default AES encryption key for the server as provided by
            :py:func:`djblets.secrets.crypto.get_default_aes_encryption_key`.

            Version Added:
                3.0

    Returns:
        object:
        The cached data, or the result of ``lookup_callable`` if uncached.
    """
    if large_data:
        results = list(cache_memoize_iter(
            key,
            lambda: [lookup_callable()],
            expiration=expiration,
            force_overwrite=force_overwrite,
            compress_large_data=compress_large_data,
            use_encryption=use_encryption,
            encryption_key=encryption_key))

        assert len(results) == 1

        return results[0]
    else:
        cache_context = _CacheContext(
            cache=cache,
            base_cache_key=key,
            expiration=expiration,
            compress_large_data=compress_large_data,
            use_encryption=use_encryption,
            encryption_key=encryption_key)
        full_cache_key = cache_context.full_cache_key

        if not force_overwrite:
            try:
                result = cache_context.load_value(full_cache_key)
            except Exception:
                # We've already logged this. Proceed to generate new data.
                pass

            if result is not _NO_RESULTS:
                return result
            else:
                logger.debug('Cache miss for key "%s"' % full_cache_key)

        data = lookup_callable()

        # Most people will be using memcached, and memcached has a limit of
        # 1MB. Data this big should be broken up somehow, so let's warn
        # about this. Users should hopefully be using large_data=True which
        # will handle this appropriately.
        #
        # If we do get here, we try to do some sanity checking.
        # python-memcached will return a result in the case where the data
        # exceeds the value size, which Django will then silently use to clear
        # out the key. We won't know at all whether we had success unless we
        # come back and try to verify the value.
        #
        # This check handles the common case of large string data being stored
        # in cache. It's still possible to attempt to store large data
        # structures (where len(data) might be something like '6' but the
        # serialized value is huge), where this can still fail.
        if (isinstance(data, str) and
            len(data) >= CACHE_CHUNK_SIZE):
            logger.warning('Cache data for key "%s" (length %s) may be too '
                           'big for the cache.',
                           full_cache_key, len(data))

        try:
            cache_context.store_value(data, key=full_cache_key)
        except Exception as e:
            logger.error('Unable to store cached data in key "%s": %s',
                         full_cache_key, e)

        return data


def make_cache_key(key, use_encryption=None, encryption_key=None):
    """Create a cache key guaranteed to avoid conflicts and size limits.

    The cache key will be prefixed by the site's domain, and will be
    changed to an SHA256 hash if it's larger than the maximum key size or
    contains characters not compatible with the cache backend.

    Version Changed:
        3.0:
        * Added support for encrypting keys through the
          ``use_encryption`` and ``encryption_key`` arguments.
        * Changed the hash format for keys to use SHA256 instead of MD5.
          This will invalidate all old keys in cache, but reduces chances
          of collision.
        * Keys will automatically use the hash format if they contain
          characters unsupported by the cache backend.
        * The return type is now :py:class:`str`, to generate keys that are
          more suitable for modern versions of Django.

    Args:
        key (str):
            The base key to generate a cache key from.

        use_encryption (bool, optional):
            Whether to generate an encrypted key.

            This will generate a HMAC digest of the key. There will be no
            identifying information in the resulting key.

            This defaults to ``False``, but can be forced on for all cached
            data by setting ``settings.DJBLETS_CACHE_FORCE_ENCRYPTION=True``.

            Version Added:
                3.0

        encryption_key (bytes, optional):
            An explicit AES encryption key to use when passing
            ``use_encryption=True``.

            This defaults the value in
            ``settings.DJBLETS_CACHE_DEFAULT_ENCRYPTION_KEY``, if set, or to
            the default AES encryption key for the server as provided by
            :py:func:`djblets.secrets.crypto.get_default_aes_encryption_key`.

            Version Added:
                3.0

    Returns:
        str:
        A cache key suitable for use with the cache backend.
    """
    if use_encryption is None:
        use_encryption = _get_default_use_encryption()

    try:
        site = Site.objects.get_current()

        # The install has a Site app, so prefix the domain to the key.
        # If a SITE_ROOT is defined, also include that, to allow for multiple
        # instances on the same host.
        site_root = getattr(settings, 'SITE_ROOT', None)

        if site_root:
            key = '%s:%s:%s' % (site.domain, site_root, key)
        else:
            key = '%s:%s' % (site.domain, key)
    except Exception:
        # The install doesn't have a Site app, so use the key as-is.
        pass

    if use_encryption:
        if encryption_key:
            assert isinstance(encryption_key, bytes)
        else:
            encryption_key = _get_default_encryption_key()

        # Construct a HMAC digest of the key using the encryption key.
        # The result will be a SHA256 hash.
        key = hmac.new(
            encryption_key,
            msg=force_bytes(key),
            digestmod=hashlib.sha256).hexdigest()
    else:
        # Normalize any invalid characters in the key.
        key = _INVALID_KEY_CHARS_RE.sub(lambda m: '\\x%02x' % ord(m.group(0)),
                                        key)

        if len(key) > MAX_KEY_SIZE:
            digest = hashlib.sha256(key.encode('utf-8')).hexdigest()

            # Replace the excess part of the key with a digest of the key
            key = key[:MAX_KEY_SIZE - len(digest)] + digest

    return key
