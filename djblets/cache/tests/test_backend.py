"""Unit tests for djblets.cache.backend."""

from __future__ import annotations

import inspect
import pickle
import re
import time
import zlib
from typing import TYPE_CHECKING

import kgb
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.cache.backends.base import memcache_key_warnings
from django.test.utils import override_settings

from djblets.cache.backend import (CACHE_CHUNK_SIZE,
                                   MAX_KEY_SIZE,
                                   cache_memoize,
                                   cache_memoize_iter,
                                   make_cache_key,
                                   _get_default_encryption_key)
from djblets.protect.locks import CacheLock
from djblets.secrets.crypto import AES_BLOCK_SIZE, aes_decrypt, aes_encrypt
from djblets.testing.testcases import TestCase

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence


class BaseCacheTestCase(kgb.SpyAgency, TestCase):
    """Base class for cache-related unit tests."""

    CUSTOM_ENCRYPTION_KEY = b'0123456789abcdef'

    def tearDown(self):
        super().tearDown()

        cache.clear()

    def build_test_chunk_data(
        self,
        *,
        data_char: str = 'x',
        num_chunks: int,
        extra_len: int = 0,
        use_compression: bool = False,
        use_encryption: bool = False,
        encryption_key: (bytes | None) = None,
    ) -> tuple[str, bytes]:
        """Build enough test data to fill up the specified number of chunks.

        This takes into account the size of the pickle data, and will
        get us to exactly the specified number of chunks of data in the cache.

        Version Changed:
            5.3:
            * Made all arguments keyword-only.
            * Added the ``data_char`` argumnet.

        Args:
            data_char (str, optional):
                The character to use for the test value.

                Version Added:
                    5.3

            num_chunks (int):
                The number of chunks to build.

            extra_len (int, optional):
                Extra length to add to the data size.

            use_compression (bool, optional):
                Whether to compress the payload.

            use_encryption (bool, optional):
                Whether to generate a payload suitable for encryption.

            encryption_key (bytes, optional):
                An optional non-default encryption key.

        Returns:
            tuple:
            A 2-tuple containing:

            Tuple:
                0 (str):
                    The raw generated data.

                1 (bytes):
                    The resulting chunk data to store.
        """
        data_len = CACHE_CHUNK_SIZE * num_chunks - 3 * num_chunks + extra_len

        if use_encryption:
            data_len -= AES_BLOCK_SIZE

        data = data_char * data_len

        chunk_data = pickle.dumps(data, protocol=0)
        self.assertTrue(chunk_data.startswith(
            b'V%s' % (data_char.encode('utf-8') * 8)))

        if use_compression:
            chunk_data = zlib.compress(chunk_data)

        if use_encryption:
            chunk_data = aes_encrypt(
                chunk_data,
                key=encryption_key or _get_default_encryption_key())

        if not use_compression:
            self.assertEqual(len(chunk_data),
                             CACHE_CHUNK_SIZE * num_chunks + extra_len)

        return data, chunk_data


class CacheMemoizeTests(BaseCacheTestCase):
    """Unit tests for cache_memoize."""

    def test_with_string(self):
        """Testing cache_memoize with string"""
        cache_key = 'abc123'
        test_str = 'Test 123'

        def cache_func():
            return test_str

        self.spy_on(cache_func)

        result = cache_memoize(cache_key, cache_func)
        self.assertEqual(result, test_str)
        self.assertSpyCallCount(cache_func, 1)

        # Call a second time. We should only call cache_func once.
        result = cache_memoize(cache_key, cache_func)
        self.assertEqual(result, test_str)
        self.assertSpyCallCount(cache_func, 1)

    def test_with_unicode_data(self):
        """Testing cache_memoize with Unicode data"""
        cache_key = 'abc123'
        test_str = '🙃' * 5

        def cache_func():
            return test_str

        self.spy_on(cache_func)

        result = cache_memoize(cache_key, cache_func)
        self.assertEqual(result, test_str)
        self.assertSpyCallCount(cache_func, 1)

        # Call a second time. We should only call cache_func once.
        result = cache_memoize(cache_key, cache_func)
        self.assertEqual(result, test_str)
        self.assertSpyCallCount(cache_func, 1)

    def test_with_non_sequence(self):
        """Testing cache_memoize with non-sequence type data"""
        cache_key = 'abc123'
        data = True

        def cache_func():
            return data

        self.spy_on(cache_func)

        result = cache_memoize(cache_key, cache_func)
        self.assertEqual(result, data)
        self.assertSpyCallCount(cache_func, 1)

        # Call a second time. We should only call cache_func once.
        result = cache_memoize(cache_key, cache_func)
        self.assertEqual(result, data)
        self.assertSpyCallCount(cache_func, 1)

    def test_with_cache_get_error(self) -> None:
        """Testing cache_memoize with cache.get() error"""
        cache_key = 'abc123'
        test_str = 'Test 123'

        self.spy_on(cache.get, op=kgb.SpyOpRaise(Exception('Oh no')))

        with self.assertLogs() as logs:
            result = cache_memoize(cache_key, lambda: test_str)

        self.assertEqual(len(logs.output), 1)
        self.assertRegex(
            logs.output[0],
            re.compile(
                r'^ERROR:djblets\.cache\.backend:Error fetching data from '
                r'cache for key "example.com:abc123": Oh no\n'
                r'Traceback.*Exception: Oh no',
                re.S))

        self.assertEqual(result, test_str)

    def test_with_cache_set_error(self) -> None:
        """Testing cache_memoize with cache.set() error"""
        cache_key = 'abc123'
        test_str = 'Test 123'

        self.spy_on(cache.set, op=kgb.SpyOpRaise(Exception('Oh no')))

        with self.assertLogs() as logs:
            result = cache_memoize(cache_key, lambda: test_str)

        self.assertEqual(len(logs.output), 1)
        self.assertRegex(
            logs.output[0],
            re.compile(
                r'^ERROR:djblets\.cache\.backend:Error setting data in cache '
                r'for key "example.com:abc123": Oh no\n'
                r'Traceback.*Exception: Oh no',
                re.S))

        self.assertEqual(result, test_str)

    def test_with_large_files_uncompressed(self):
        """Testing cache_memoize with large files without compression"""
        cache_key = 'abc123'

        # This takes into account the size of the pickle data, and will
        # get us to exactly 2 chunks of data in cache.
        data, pickled_data = self.build_test_chunk_data(num_chunks=2)

        def cache_func():
            return data

        self.spy_on(cache_func)

        result = cache_memoize(cache_key, cache_func, large_data=True,
                               compress_large_data=False)
        self.assertEqual(result, data)
        self.assertSpyCallCount(cache_func, 1)

        cache_key_0 = make_cache_key('%s-0' % cache_key)
        cache_key_1 = make_cache_key('%s-1' % cache_key)

        self.assertIn(make_cache_key(cache_key), cache)
        self.assertIn(cache_key_0, cache)
        self.assertIn(cache_key_1, cache)
        self.assertNotIn(make_cache_key('%s-2' % cache_key), cache)

        # Verify the contents of the stored data.
        stored_data = b''.join(cache.get(cache_key_0) + cache.get(cache_key_1))
        self.assertEqual(stored_data, pickled_data)

        # Try fetching the data we stored.
        result = cache_memoize(cache_key, cache_func, large_data=True,
                               compress_large_data=False)
        self.assertEqual(result, data)
        self.assertSpyCallCount(cache_func, 1)

    def test_with_large_files_uncompressed_off_by_one(self):
        """Testing cache_memoize with large files without compression and
        one byte larger than an even chunk size
        """
        cache_key = 'abc123'

        # This takes into account the size of the pickle data, and will
        # get us to just barely 3 chunks of data in cache.
        data, pickled_data = self.build_test_chunk_data(num_chunks=2,
                                                        extra_len=1)

        def cache_func():
            return data

        self.spy_on(cache_func)

        result = cache_memoize(cache_key, cache_func, large_data=True,
                               compress_large_data=False)
        self.assertEqual(result, data)
        self.assertSpyCallCount(cache_func, 1)

        cache_key_0 = make_cache_key('%s-0' % cache_key)
        cache_key_1 = make_cache_key('%s-1' % cache_key)
        cache_key_2 = make_cache_key('%s-2' % cache_key)

        self.assertIn(make_cache_key(cache_key), cache)
        self.assertIn(cache_key_0, cache)
        self.assertIn(cache_key_1, cache)
        self.assertIn(cache_key_2, cache)
        self.assertNotIn(make_cache_key('%s-3' % cache_key), cache)

        # Verify the contents of the stored data.
        stored_data = b''.join(cache.get(cache_key_0) +
                               cache.get(cache_key_1) +
                               cache.get(cache_key_2))
        self.assertEqual(stored_data, pickled_data)

        # Try fetching the data we stored.
        result = cache_memoize(cache_key, cache_func, large_data=True,
                               compress_large_data=False)
        self.assertEqual(result, data)
        self.assertSpyCallCount(cache_func, 1)

    def test_with_large_files_compressed(self):
        """Testing cache_memoize with large files with compression"""
        cache_key = 'abc123'

        data, pickled_data = self.build_test_chunk_data(num_chunks=2)

        def cache_func():
            return data

        self.spy_on(cache_func)

        result = cache_memoize(cache_key, cache_func, large_data=True,
                               compress_large_data=True)
        self.assertSpyCallCount(cache_func, 1)

        cache_key_0 = make_cache_key('%s-0' % cache_key)

        self.assertIn(make_cache_key(cache_key), cache)
        self.assertIn(cache_key_0, cache)
        self.assertNotIn(make_cache_key('%s-1' % cache_key), cache)
        self.assertNotIn(make_cache_key('%s-2' % cache_key), cache)

        # Verify the contents of the stored data.
        stored_data = cache.get(cache_key_0)[0]
        self.assertEqual(stored_data, zlib.compress(pickled_data))

        # Try fetching the data we stored.
        result = cache_memoize(cache_key, cache_func, large_data=True,
                               compress_large_data=True)
        self.assertEqual(result, data)
        self.assertSpyCallCount(cache_func, 1)

    def test_with_large_files_load_uncompressed(self):
        """Testing cache_memoize with large files without compression and
        loading data
        """
        cache_key = 'abc123'

        # This takes into account the size of the pickle data, and will
        # get us to exactly 2 chunks of data in cache.
        data, pickled_data = self.build_test_chunk_data(num_chunks=2)

        cache.set(make_cache_key(cache_key), '2')
        cache.set(make_cache_key('%s-0' % cache_key),
                  [pickled_data[:CACHE_CHUNK_SIZE]])
        cache.set(make_cache_key('%s-1' % cache_key),
                  [pickled_data[CACHE_CHUNK_SIZE:]])

        def cache_func():
            return ''

        self.spy_on(cache_func)

        result = cache_memoize(cache_key, cache_func, large_data=True,
                               compress_large_data=False)
        self.assertEqual(result, data)
        self.assertSpyNotCalled(cache_func)

    def test_with_large_files_load_compressed(self):
        """Testing cache_memoize with large files with compression and
        loading cached data
        """
        cache_key = 'abc123'

        data, stored_data = self.build_test_chunk_data(
            num_chunks=2,
            use_compression=True)
        self.assertLess(len(stored_data), CACHE_CHUNK_SIZE)

        cache.set(make_cache_key(cache_key), '1')
        cache.set(make_cache_key('%s-0' % cache_key), [stored_data])

        def cache_func():
            return ''

        self.spy_on(cache_func)

        result = cache_memoize(cache_key, cache_func, large_data=True,
                               compress_large_data=True)
        self.assertEqual(result, data)
        self.assertSpyNotCalled(cache_func)

    def test_with_large_files_missing_chunk(self):
        """Testing cache_memoize with loading large files with missing chunks
        """
        cache_key = 'abc123'

        # This takes into account the size of the pickle data, and will
        # get us to exactly 2 chunks of data in cache.
        data, pickled_data = self.build_test_chunk_data(num_chunks=2)

        cache.set(make_cache_key(cache_key), '2')
        cache.set(make_cache_key('%s-0' % cache_key),
                  [pickled_data[:CACHE_CHUNK_SIZE]])

        def cache_func():
            return data

        self.spy_on(cache_func)

        result = cache_memoize(cache_key, cache_func, large_data=True,
                               compress_large_data=False)
        self.assertEqual(result, data)
        self.assertSpyCallCount(cache_func, 1)

    def test_with_large_files_cache_get_error(self) -> None:
        """Testing cache_memoize with loading large files and cache.get()
        error
        """
        cache_key = 'abc123'

        # This takes into account the size of the pickle data, and will
        # get us to exactly 2 chunks of data in cache.
        data, pickled_data = self.build_test_chunk_data(num_chunks=2)

        cache.set(make_cache_key(cache_key), '2')
        cache.set(make_cache_key('%s-0' % cache_key),
                  [pickled_data[:CACHE_CHUNK_SIZE]])

        self.spy_on(cache.get, op=kgb.SpyOpRaise(Exception('Oh no')))

        with self.assertLogs() as logs:
            result = cache_memoize(cache_key,
                                   lambda: data,
                                   large_data=True,
                                   compress_large_data=False)

        self.assertEqual(len(logs.output), 2)
        self.assertRegex(
            logs.output[0],
            re.compile(
                r'^ERROR:djblets\.cache\.backend:Error fetching data from '
                r'cache for key "example\.com:abc123": Oh no\n'
                r'Traceback.*Exception: Oh no',
                re.S))
        self.assertEqual(
            logs.output[1],
            'ERROR:djblets.cache.backend:Failed to fetch large or iterable '
            'data entry count from cache for key "example.com:abc123". '
            'Rebuilding data. Error = Oh no')

        self.assertEqual(result, data)

    def test_with_use_encryption(self):
        """Testing cache_memoize with use_encryption=True"""
        cache_key = 'abc123'
        test_str = 'Test 123'

        def cache_func():
            return test_str

        self.spy_on(cache_func)

        result = cache_memoize(cache_key,
                               cache_func,
                               use_encryption=True)
        self.assertEqual(result, test_str)
        self.assertSpyCallCount(cache_func, 1)

        # Check what we put into cache.
        encrypted_key = \
            '0a3195ea908f9bd178ab3c67a257ea4e7954e4b67ac240d1c86953953cde3a0b'
        self.assertIn(encrypted_key, cache)

        cache_value = cache.get(encrypted_key)
        self.assertNotEqual(cache_value, test_str)
        self.assertEqual(pickle.loads(aes_decrypt(cache_value)),
                         test_str)

        # Call a second time. We should only call cache_func once.
        result = cache_memoize(cache_key,
                               cache_func,
                               use_encryption=True)
        self.assertEqual(result, test_str)
        self.assertSpyCallCount(cache_func, 1)

    def test_with_use_encryption_and_custom_encryption_key(self):
        """Testing cache_memoize with use_encryption=True and custom
        encryption_key
        """
        cache_key = 'abc123'
        test_str = 'Test 123'

        def cache_func():
            return test_str

        self.spy_on(cache_func)

        result = cache_memoize(cache_key,
                               cache_func,
                               use_encryption=True,
                               encryption_key=self.CUSTOM_ENCRYPTION_KEY)
        self.assertEqual(result, test_str)
        self.assertSpyCallCount(cache_func, 1)

        # Check what we put into cache.
        encrypted_key = \
            '10c4714f5c6c49045ed25c8da7d04a4be2254fa275fc3b63bdeebe887aee52f9'
        self.assertIn(encrypted_key, cache)

        cache_value = cache.get(encrypted_key)
        self.assertNotEqual(cache_value, test_str)
        self.assertEqual(
            pickle.loads(aes_decrypt(cache_value,
                                     key=self.CUSTOM_ENCRYPTION_KEY)),
            test_str)

        # Call a second time. We should only call cache_func once.
        result = cache_memoize(cache_key,
                               cache_func,
                               use_encryption=True,
                               encryption_key=self.CUSTOM_ENCRYPTION_KEY)
        self.assertEqual(result, test_str)
        self.assertSpyCallCount(cache_func, 1)

    def test_with_use_encryption_and_key_changed(self):
        """Testing cache_memoize with use_encryption=True and encryption
        key changed
        """
        cache_key = 'abc123'
        test_str = 'Test 123'

        def cache_func():
            return test_str

        self.spy_on(cache_func)

        result = cache_memoize(cache_key,
                               cache_func,
                               use_encryption=True)
        self.assertEqual(result, test_str)
        self.assertSpyCallCount(cache_func, 1)

        # Check what we put into cache.
        encrypted_key = \
            '0a3195ea908f9bd178ab3c67a257ea4e7954e4b67ac240d1c86953953cde3a0b'
        self.assertIn(encrypted_key, cache)

        cache_value = cache.get(encrypted_key)
        self.assertNotEqual(cache_value, test_str)
        self.assertEqual(
            pickle.loads(aes_decrypt(cache_value)),
            test_str)

        # Call a second time. We should only call cache_func once.
        result = cache_memoize(cache_key,
                               cache_func,
                               use_encryption=True,
                               encryption_key=self.CUSTOM_ENCRYPTION_KEY)
        self.assertEqual(result, test_str)
        self.assertSpyCallCount(cache_func, 2)

        encrypted_key = \
            '10c4714f5c6c49045ed25c8da7d04a4be2254fa275fc3b63bdeebe887aee52f9'
        self.assertIn(encrypted_key, cache)

        cache_value = cache.get(encrypted_key)
        self.assertNotEqual(cache_value, test_str)
        self.assertEqual(
            pickle.loads(aes_decrypt(cache_value,
                                     key=self.CUSTOM_ENCRYPTION_KEY)),
            test_str)

    @override_settings(DJBLETS_CACHE_FORCE_ENCRYPTION=True)
    def test_with_force_use_encryption(self):
        """Testing cache_memoize with
        settings.DJBLETS_CACHE_FORCE_ENCRYPTION=True
        """
        cache_key = 'abc123'
        test_str = 'Test 123'

        def cache_func():
            return test_str

        self.spy_on(cache_func)

        result = cache_memoize(cache_key, cache_func)
        self.assertEqual(result, test_str)
        self.assertSpyCallCount(cache_func, 1)

        # Check what we put into cache.
        encrypted_key = \
            '0a3195ea908f9bd178ab3c67a257ea4e7954e4b67ac240d1c86953953cde3a0b'
        self.assertIn(encrypted_key, cache)

        cache_value = cache.get(encrypted_key)
        self.assertNotEqual(cache_value, test_str)
        self.assertEqual(pickle.loads(aes_decrypt(cache_value)),
                         test_str)

        # Call a second time. We should only call cache_func once.
        result = cache_memoize(cache_key, cache_func)
        self.assertEqual(result, test_str)
        self.assertSpyCallCount(cache_func, 1)

    def test_with_use_encryption_and_non_string_data(self):
        """Testing cache_memoize with use_encryption=True and non-string
        data
        """
        cache_key = 'abc123'
        test_data = {
            'item1': True,
            'item2': {1, 2, 3},
            'item3': None,
        }

        def cache_func():
            return test_data

        self.spy_on(cache_func)

        result = cache_memoize(cache_key,
                               cache_func,
                               use_encryption=True)
        self.assertEqual(result, test_data)
        self.assertSpyCallCount(cache_func, 1)

        # Check what we put into cache.
        encrypted_key = \
            '0a3195ea908f9bd178ab3c67a257ea4e7954e4b67ac240d1c86953953cde3a0b'
        self.assertIn(encrypted_key, cache)

        cache_value = cache.get(encrypted_key)
        self.assertNotEqual(cache_value, test_data)
        self.assertEqual(pickle.loads(aes_decrypt(cache_value)),
                         test_data)

        # Call a second time. We should only call cache_func once.
        result = cache_memoize(cache_key, cache_func,
                               use_encryption=True)
        self.assertEqual(result, test_data)
        self.assertSpyCallCount(cache_func, 1)

    def test_with_use_encryption_and_large_files_uncompressed(self):
        """Testing cache_memoize with use_encryption=True and large files
        without compression
        """
        cache_key = 'abc123'

        # This takes into account the size of the encrypted pickle data, and
        # will get us to exactly 2 chunks of data in cache.
        data, encrypted_data = self.build_test_chunk_data(
            num_chunks=2,
            use_encryption=True)

        def cache_func():
            return data

        self.spy_on(cache_func)

        result = cache_memoize(cache_key,
                               cache_func,
                               large_data=True,
                               compress_large_data=False,
                               use_encryption=True)
        self.assertEqual(result, data)
        self.assertSpyCallCount(cache_func, 1)

        # Check what we put into cache.
        cache_key_main = make_cache_key(cache_key,
                                        use_encryption=True)
        cache_key_0 = make_cache_key('%s-0' % cache_key,
                                     use_encryption=True)
        cache_key_1 = make_cache_key('%s-1' % cache_key,
                                     use_encryption=True)
        cache_key_2 = make_cache_key('%s-2' % cache_key,
                                     use_encryption=True)

        self.assertIn(cache_key_main, cache)
        self.assertIn(cache_key_0, cache)
        self.assertIn(cache_key_1, cache)
        self.assertNotIn(cache_key_2, cache)

        # Verify the contents of the stored data.
        stored_data = b''.join(cache.get(cache_key_0) +
                               cache.get(cache_key_1))
        self.assertNotEqual(stored_data, data)
        self.assertEqual(pickle.loads(aes_decrypt(stored_data)),
                         data)

        # Call a second time. We should only call cache_func once.
        result = cache_memoize(cache_key,
                               cache_func,
                               large_data=True,
                               compress_large_data=False,
                               use_encryption=True)
        self.assertEqual(result, data)
        self.assertSpyCallCount(cache_func, 1)

    def test_with_use_encryption_and_large_files_uncompressed_off_by_one(self):
        """Testing cache_memoize with use_encryption=True and large files
        without compression and one byte larger than an even chunk size
        """
        cache_key = 'abc123'

        # This takes into account the size of the encrypted pickle data, and
        # will get us to just barely 3 chunks of data in cache.
        data, encrypted_data = self.build_test_chunk_data(
            num_chunks=2,
            extra_len=1,
            use_encryption=True)

        def cache_func():
            return data

        self.spy_on(cache_func)

        result = cache_memoize(cache_key,
                               cache_func,
                               large_data=True,
                               compress_large_data=False,
                               use_encryption=True)
        self.assertEqual(result, data)
        self.assertSpyCallCount(cache_func, 1)

        # Check what we put into cache.
        cache_key_main = make_cache_key(cache_key,
                                        use_encryption=True)
        cache_key_0 = make_cache_key('%s-0' % cache_key,
                                     use_encryption=True)
        cache_key_1 = make_cache_key('%s-1' % cache_key,
                                     use_encryption=True)
        cache_key_2 = make_cache_key('%s-2' % cache_key,
                                     use_encryption=True)
        cache_key_3 = make_cache_key('%s-3' % cache_key,
                                     use_encryption=True)

        self.assertIn(cache_key_main, cache)
        self.assertIn(cache_key_0, cache)
        self.assertIn(cache_key_1, cache)
        self.assertIn(cache_key_2, cache)
        self.assertNotIn(cache_key_3, cache)

        # Verify the contents of the stored data.
        stored_data = b''.join(cache.get(cache_key_0) +
                               cache.get(cache_key_1) +
                               cache.get(cache_key_2))
        self.assertNotEqual(stored_data, data)
        self.assertEqual(pickle.loads(aes_decrypt(stored_data)),
                         data)

        # Call a second time. We should only call cache_func once.
        result = cache_memoize(cache_key,
                               cache_func,
                               large_data=True,
                               compress_large_data=False,
                               use_encryption=True)
        self.assertEqual(result, data)
        self.assertSpyCallCount(cache_func, 1)

    def test_with_use_encryption_and_large_files_compressed(self):
        """Testing cache_memoize with use_encryption=True and large files
        with compression
        """
        cache_key = 'abc123'

        # This takes into account the size of the encrypted pickle data, and
        # will get us to just barely 3 chunks of data in cache.
        data, encrypted_data = self.build_test_chunk_data(
            num_chunks=2,
            use_encryption=True)

        def cache_func():
            return data

        self.spy_on(cache_func)

        result = cache_memoize(cache_key,
                               cache_func,
                               large_data=True,
                               compress_large_data=True,
                               use_encryption=True)
        self.assertEqual(result, data)
        self.assertSpyCallCount(cache_func, 1)

        # Check what we put into cache.
        cache_key_main = make_cache_key(cache_key,
                                        use_encryption=True)
        cache_key_0 = make_cache_key('%s-0' % cache_key,
                                     use_encryption=True)
        cache_key_1 = make_cache_key('%s-1' % cache_key,
                                     use_encryption=True)
        cache_key_2 = make_cache_key('%s-2' % cache_key,
                                     use_encryption=True)

        self.assertIn(cache_key_main, cache)
        self.assertIn(cache_key_0, cache)
        self.assertNotIn(cache_key_1, cache)
        self.assertNotIn(cache_key_2, cache)

        # Verify the contents of the stored data.
        stored_data = cache.get(cache_key_0)[0]
        self.assertNotEqual(stored_data, data)
        self.assertEqual(
            pickle.loads(zlib.decompress(aes_decrypt(stored_data))),
            data)

        # Call a second time. We should only call cache_func once.
        result = cache_memoize(cache_key,
                               cache_func,
                               large_data=True,
                               compress_large_data=True,
                               use_encryption=True)
        self.assertEqual(result, data)
        self.assertSpyCallCount(cache_func, 1)

    def test_with_use_encryption_and_large_files_load_uncompressed(self):
        """Testing cache_memoize with use_encryption=True and large files
        without compression and loading data
        """
        cache_key = 'abc123'

        # This takes into account the size of the encrypted pickle data, and
        # will get us to just barely 3 chunks of data in cache.
        data, encrypted_data = self.build_test_chunk_data(
            num_chunks=2,
            use_encryption=True)

        cache_key_main = make_cache_key(cache_key,
                                        use_encryption=True)
        cache_key_0 = make_cache_key('%s-0' % cache_key,
                                     use_encryption=True)
        cache_key_1 = make_cache_key('%s-1' % cache_key,
                                     use_encryption=True)

        cache.set(cache_key_main, aes_encrypt(pickle.dumps('2', protocol=0)))
        cache.set(cache_key_0, [encrypted_data[:CACHE_CHUNK_SIZE]])
        cache.set(cache_key_1, [encrypted_data[CACHE_CHUNK_SIZE:]])

        def cache_func():
            return ''

        self.spy_on(cache_func)

        result = cache_memoize(cache_key,
                               cache_func,
                               large_data=True,
                               compress_large_data=False,
                               use_encryption=True)
        self.assertEqual(result, data)
        self.assertSpyNotCalled(cache_func)

    def test_with_use_encryption_and_large_files_load_compressed(self):
        """Testing cache_memoize with use_encryption=True and large files
        with compression and loading data
        """
        cache_key = 'abc123'

        # This takes into account the size of the encrypted pickle data, and
        # will get us to just barely 3 chunks of data in cache.
        data, encrypted_data = self.build_test_chunk_data(
            num_chunks=2,
            use_compression=True,
            use_encryption=True)
        self.assertLess(len(encrypted_data), CACHE_CHUNK_SIZE)

        cache_key_main = make_cache_key(cache_key,
                                        use_encryption=True)
        cache_key_0 = make_cache_key('%s-0' % cache_key,
                                     use_encryption=True)

        cache.set(cache_key_main, aes_encrypt(pickle.dumps('1', protocol=0)))
        cache.set(cache_key_0, [encrypted_data])

        def cache_func():
            return ''

        self.spy_on(cache_func)

        result = cache_memoize(cache_key,
                               cache_func,
                               large_data=True,
                               compress_large_data=True,
                               use_encryption=True)
        self.assertEqual(result, data)
        self.assertSpyNotCalled(cache_func)

    def test_with_use_encryption_and_large_files_custom_key(self):
        """Testing cache_memoize with use_encryption=True and large files
        with custom encryption key
        """
        cache_key = 'abc123'
        encryption_key = self.CUSTOM_ENCRYPTION_KEY

        # This takes into account the size of the encrypted pickle data, and
        # will get us to just barely 3 chunks of data in cache.
        data, encrypted_data = self.build_test_chunk_data(
            num_chunks=2,
            use_encryption=True,
            encryption_key=encryption_key)

        def cache_func():
            return data

        self.spy_on(cache_func)

        result = cache_memoize(cache_key,
                               cache_func,
                               large_data=True,
                               compress_large_data=True,
                               use_encryption=True,
                               encryption_key=encryption_key)
        self.assertEqual(result, data)
        self.assertSpyCallCount(cache_func, 1)

        # Check what we put into cache.
        cache_key_main = make_cache_key(cache_key,
                                        use_encryption=True,
                                        encryption_key=encryption_key)
        cache_key_0 = make_cache_key('%s-0' % cache_key,
                                     use_encryption=True,
                                     encryption_key=encryption_key)
        cache_key_1 = make_cache_key('%s-1' % cache_key,
                                     use_encryption=True,
                                     encryption_key=encryption_key)
        cache_key_2 = make_cache_key('%s-2' % cache_key,
                                     use_encryption=True,
                                     encryption_key=encryption_key)

        self.assertIn(cache_key_main, cache)
        self.assertIn(cache_key_0, cache)
        self.assertNotIn(cache_key_1, cache)
        self.assertNotIn(cache_key_2, cache)

        # Verify the contents of the stored data.
        stored_data = cache.get(cache_key_0)[0]
        self.assertNotEqual(stored_data, data)
        self.assertEqual(
            pickle.loads(zlib.decompress(
                aes_decrypt(stored_data, key=encryption_key))),
            data)

        # Call a second time. We should only call cache_func once.
        result = cache_memoize(cache_key,
                               cache_func,
                               large_data=True,
                               compress_large_data=True,
                               use_encryption=True,
                               encryption_key=encryption_key)
        self.assertEqual(result, data)
        self.assertSpyCallCount(cache_func, 1)

    def test_with_use_encryption_and_large_files_missing_chunk(self):
        """Testing cache_memoize with use_encryption=True and large files
        with missing chunks
        """
        cache_key = 'abc123'

        # This takes into account the size of the encrypted pickle data, and
        # will get us to just barely 3 chunks of data in cache.
        data, encrypted_data = self.build_test_chunk_data(
            num_chunks=2,
            use_encryption=True)

        cache_key_main = make_cache_key(cache_key,
                                        use_encryption=True)
        cache_key_0 = make_cache_key('%s-0' % cache_key,
                                     use_encryption=True)

        cache.set(cache_key_main, aes_encrypt(pickle.dumps('2', protocol=0)))
        cache.set(cache_key_0, [encrypted_data[:CACHE_CHUNK_SIZE]])

        def cache_func():
            return data

        self.spy_on(cache_func)

        result = cache_memoize(cache_key,
                               cache_func,
                               large_data=True,
                               compress_large_data=False,
                               use_encryption=True)
        self.assertEqual(result, data)
        self.assertSpyCallCount(cache_func, 1)

    def test_with_use_encryption_and_large_files_bad_chunk(self):
        """Testing cache_memoize with use_encryption=True and large files
        with chunk failing decryption
        """
        cache_key = 'abc123'

        # This takes into account the size of the encrypted pickle data, and
        # will get us to just barely 3 chunks of data in cache.
        data, encrypted_data = self.build_test_chunk_data(
            num_chunks=2,
            use_encryption=True,
            encryption_key=self.CUSTOM_ENCRYPTION_KEY)

        cache_key_main = make_cache_key(cache_key,
                                        use_encryption=True)
        cache_key_0 = make_cache_key('%s-0' % cache_key,
                                     use_encryption=True)

        cache.set(cache_key_main, aes_encrypt(pickle.dumps('2', protocol=0)))
        cache.set(cache_key_0, [encrypted_data[:CACHE_CHUNK_SIZE]])

        def cache_func():
            return data

        self.spy_on(cache_func)

        result = cache_memoize(cache_key,
                               cache_func,
                               large_data=True,
                               compress_large_data=False,
                               use_encryption=True)
        self.assertEqual(result, data)
        self.assertSpyCallCount(cache_func, 1)

    def test_with_lock_and_in_cache(self) -> None:
        """Testing cache_memoize with lock and data in cache"""
        lock = CacheLock(timeout_secs=0.1,
                         retry_secs=0.05)

        self.spy_on(lock.acquire)
        self.spy_on(lock.release)

        cache_key = 'abc123'

        def cache_func() -> str:
            return 'new result'

        self.spy_on(cache_func)

        cache.set(make_cache_key(cache_key), 'existing result')

        result = cache_memoize(cache_key,
                               cache_func,
                               lock=lock)
        self.assertEqual(result, 'existing result')
        self.assertSpyNotCalled(cache_func)

        self.assertSpyNotCalled(lock.acquire)
        self.assertSpyNotCalled(lock.release)
        self.assertIsNone(cache.get(lock.full_cache_key))

    def test_with_lock_and_cache_miss(self) -> None:
        """Testing cache_memoize with lock and cache miss"""
        lock = CacheLock(timeout_secs=0.1,
                         retry_secs=0.05)

        self.spy_on(lock.acquire)
        self.spy_on(lock.release)

        cache_key = 'abc123'
        data = 'test123'

        def cache_func() -> str:
            self.assertEqual(cache.get(lock.full_cache_key), lock.token)

            return data

        self.spy_on(cache_func)

        result = cache_memoize(cache_key,
                               cache_func,
                               lock=lock)
        self.assertEqual(result, data)
        self.assertSpyCallCount(cache_func, 1)

        self.assertSpyCallCount(lock.acquire, 1)
        self.assertSpyCallCount(lock.release, 1)
        self.assertIsNone(cache.get(lock.full_cache_key))

    def test_with_lock_and_in_cache_after_lock(self) -> None:
        """Testing cache_memoize with lock and data in cache after lock"""
        lock = CacheLock(timeout_secs=0.1,
                         retry_secs=0.05)

        def _lock_acquire(_self, *args, **kwargs) -> bool:
            cache.set(make_cache_key(cache_key), 'existing result')

            return lock.acquire.call_original(*args, **kwargs)

        self.spy_on(lock.acquire, call_fake=_lock_acquire)
        self.spy_on(lock.release)

        cache_key = 'abc123'

        def cache_func() -> str:
            return 'new result'

        self.spy_on(cache_func)

        result = cache_memoize(cache_key,
                               cache_func,
                               lock=lock)
        self.assertEqual(result, 'existing result')
        self.assertSpyNotCalled(cache_func)

        self.assertSpyCallCount(lock.acquire, 1)
        self.assertSpyCallCount(lock.release, 1)
        self.assertIsNone(cache.get(lock.full_cache_key))

    def test_with_lock_and_wait_with_result(self) -> None:
        """Testing cache_memoize with lock and waiting with result from cache
        """
        existing_lock = CacheLock(key='lock-key')
        lock_key = existing_lock.full_cache_key

        with existing_lock as locked:
            self.assertTrue(locked)

            new_lock = CacheLock(key='lock-key',
                                 timeout_secs=0.1,
                                 retry_secs=0.05)

            def _lock_acquire(_self, *args, **kwargs) -> bool:
                # Place a value in cache and release the lock so the new
                # lock can be acquired.
                cache.set(make_cache_key(cache_key), 'existing result')
                existing_lock.release()

                return new_lock.acquire.call_original(*args, **kwargs)

            self.spy_on(new_lock.acquire, call_fake=_lock_acquire)
            self.spy_on(new_lock.release)

            cache_key = 'abc123'

            def cache_func() -> str:
                return 'new result'

            self.spy_on(cache_func)

            result = cache_memoize(cache_key,
                                   cache_func,
                                   lock=new_lock)
            self.assertEqual(result, 'existing result')
            self.assertSpyNotCalled(cache_func)

            self.assertSpyCallCount(new_lock.acquire, 1)
            self.assertSpyCallCount(new_lock.release, 1)

            self.assertIsNone(cache.get(lock_key))

        self.assertIsNone(cache.get(lock_key))

    def test_with_lock_and_wait_with_timeout(self) -> None:
        """Testing cache_memoize with lock and waiting with timeout"""
        existing_lock = CacheLock(key='lock-key')
        lock_key = existing_lock.full_cache_key

        with existing_lock as locked:
            self.assertTrue(locked)

            new_lock = CacheLock(key='lock-key',
                                 timeout_secs=0.1,
                                 retry_secs=0.05)

            self.spy_on(new_lock.acquire)
            self.spy_on(new_lock.release)

            cache_key = 'abc123'

            def cache_func() -> str:
                return 'new result'

            self.spy_on(cache_func)

            with self.assertLogs() as cm:
                result = cache_memoize(cache_key,
                                       cache_func,
                                       lock=new_lock)

            self.assertEqual(result, 'new result')
            self.assertSpyCallCount(cache_func, 1)

            self.assertSpyCallCount(new_lock.acquire, 1)
            self.assertSpyNotCalled(new_lock.release)
            self.assertSpyLastRaisedMessage(
                new_lock.acquire,
                TimeoutError,
                'Timed out waiting for lock: example.com:lock-key')

            self.assertEqual(cache.get(lock_key), existing_lock.token)

            self.assertEqual(cm.output, [
                f'WARNING:djblets.protect.locks:Timed out waiting for cache '
                f'lock "example.com:lock-key" (token "{new_lock.token}") '
                f'for 0.1 seconds',

                f'ERROR:djblets.cache.backend:Timeout waiting on distributed '
                f'cache lock {new_lock!r}',
            ])

        self.assertIsNone(cache.get(lock_key))

    def test_with_lock_and_wait_with_timeout_and_value_in_cache(self) -> None:
        """Testing cache_memoize with lock and waiting with timeout and new
        value in cache
        """
        existing_lock = CacheLock(key='lock-key')
        lock_key = existing_lock.full_cache_key

        with existing_lock as locked:
            self.assertTrue(locked)

            new_lock = CacheLock(key='lock-key',
                                 timeout_secs=0.1,
                                 retry_secs=0.05)

            def _lock_acquire(_self, *args, **kwargs) -> bool:
                cache.set(make_cache_key(cache_key), 'existing result')

                return new_lock.acquire.call_original(*args, **kwargs)

            self.spy_on(new_lock.acquire, call_fake=_lock_acquire)
            self.spy_on(new_lock.release)

            cache_key = 'abc123'

            def cache_func() -> str:
                return 'new result'

            self.spy_on(cache_func)

            result = cache_memoize(cache_key,
                                   cache_func,
                                   lock=new_lock)
            self.assertEqual(result, 'existing result')
            self.assertSpyNotCalled(cache_func)

            self.assertSpyCallCount(new_lock.acquire, 1)
            self.assertSpyNotCalled(new_lock.release)
            self.assertSpyLastRaisedMessage(
                new_lock.acquire,
                TimeoutError,
                'Timed out waiting for lock: example.com:lock-key')

            self.assertEqual(cache.get(lock_key), existing_lock.token)

        self.assertIsNone(cache.get(lock_key))

    def test_with_lock_and_wait_with_prev_lock_expired(self) -> None:
        """Testing cache_memoize with lock and waiting with previous lock
        expired
        """
        existing_lock = CacheLock(key='lock-key',
                                  lock_expiration_secs=0.01)
        lock_key = existing_lock.full_cache_key

        time.sleep(0.015)

        with existing_lock as locked:
            self.assertTrue(locked)

            new_lock = CacheLock(key='lock-key',
                                 timeout_secs=0.1,
                                 retry_secs=0.05)

            self.spy_on(new_lock.acquire)
            self.spy_on(new_lock.release)

            cache_key = 'abc123'

            def cache_func() -> str:
                return 'new result'

            self.spy_on(cache_func)

            with self.assertNoLogs():
                result = cache_memoize(cache_key,
                                       cache_func,
                                       lock=new_lock)

            self.assertEqual(result, 'new result')
            self.assertSpyCallCount(cache_func, 1)

            self.assertSpyCallCount(new_lock.acquire, 1)
            self.assertSpyCallCount(new_lock.release, 1)

            self.assertIsNone(cache.get(lock_key))

        self.assertIsNone(cache.get(lock_key))


class CacheMemoizeIterTests(BaseCacheTestCase):
    """Unit tests for cache_memoize_iter."""

    def test_without_compression(self):
        """Testing cache_memoize_iter without compression"""
        cache_key = 'abc123'
        data_yielded = []

        data1, pickled_data_1 = self.build_test_chunk_data(num_chunks=2)
        data2, pickled_data_2 = self.build_test_chunk_data(num_chunks=2)

        def cache_func():
            data_yielded.append('data1')
            yield data1

            data_yielded.append('data2')
            yield data2

        self.spy_on(cache_func)

        result = cache_memoize_iter(cache_key, cache_func,
                                    compress_large_data=False)
        self.assertTrue(inspect.isgenerator(result))
        self.assertEqual(data_yielded, [])

        self.assertEqual(next(result), data1)
        self.assertEqual(data_yielded, ['data1'])

        self.assertEqual(next(result), data2)
        self.assertEqual(data_yielded, ['data1', 'data2'])

        with self.assertRaises(StopIteration):
            next(result)

        self.assertSpyCallCount(cache_func, 1)

        cache_key_main = make_cache_key(cache_key)
        cache_key_0 = make_cache_key('%s-0' % cache_key)
        cache_key_1 = make_cache_key('%s-1' % cache_key)
        cache_key_2 = make_cache_key('%s-2' % cache_key)
        cache_key_3 = make_cache_key('%s-3' % cache_key)

        self.assertIn(cache_key_main, cache)
        self.assertIn(cache_key_0, cache)
        self.assertIn(cache_key_1, cache)
        self.assertIn(cache_key_2, cache)
        self.assertIn(cache_key_3, cache)
        self.assertNotIn(make_cache_key('%s-4' % cache_key), cache)

        # Verify the contents of the stored data.
        stored_data = b''.join(cache.get(cache_key_0) +
                               cache.get(cache_key_1) +
                               cache.get(cache_key_2) +
                               cache.get(cache_key_3))
        self.assertEqual(cache.get(cache_key_main), '4')
        self.assertEqual(stored_data, pickled_data_1 + pickled_data_2)

        # Try fetching the data we stored.
        data_yielded = []

        result = cache_memoize_iter(cache_key, cache_func,
                                    compress_large_data=False)
        self.assertTrue(inspect.isgenerator(result))

        self.assertEqual(next(result), data1)
        self.assertEqual(next(result), data2)

        with self.assertRaises(StopIteration):
            next(result)

        self.assertEqual(data_yielded, [])
        self.assertSpyCallCount(cache_func, 1)

    def test_with_compressed(self):
        """Testing cache_memoize_iter with compression"""
        cache_key = 'abc123'
        data_yielded = []

        # This takes into account the size of the pickle data, and will
        # get us to exactly 2 chunks of data in cache, each.
        data1, pickled_data_1 = self.build_test_chunk_data(num_chunks=2)
        data2, pickled_data_2 = self.build_test_chunk_data(num_chunks=2)

        def cache_func():
            data_yielded.append('data1')
            yield data1

            data_yielded.append('data2')
            yield data2

        self.spy_on(cache_func)

        result = cache_memoize_iter(cache_key, cache_func,
                                    compress_large_data=True)
        self.assertTrue(inspect.isgenerator(result))
        self.assertEqual(data_yielded, [])

        self.assertEqual(next(result), data1)
        self.assertEqual(data_yielded, ['data1'])

        self.assertEqual(next(result), data2)
        self.assertEqual(data_yielded, ['data1', 'data2'])

        with self.assertRaises(StopIteration):
            next(result)

        self.assertSpyCallCount(cache_func, 1)

        cache_key_main = make_cache_key(cache_key)
        cache_key_0 = make_cache_key('%s-0' % cache_key)

        self.assertIn(cache_key_main, cache)
        self.assertIn(cache_key_0, cache)
        self.assertNotIn(make_cache_key('%s-1' % cache_key), cache)

        # Verify the contents of the stored data.
        self.assertEqual(cache.get(cache_key_main), '1')
        self.assertEqual(cache.get(cache_key_0)[0],
                         zlib.compress(pickled_data_1 + pickled_data_2))

        # Try fetching the data we stored.
        data_yielded = []

        result = cache_memoize_iter(cache_key, cache_func,
                                    compress_large_data=True)
        self.assertTrue(inspect.isgenerator(result))
        self.assertEqual(next(result), data1)
        self.assertEqual(next(result), data2)

        with self.assertRaises(StopIteration):
            next(result)

        self.assertEqual(data_yielded, [])
        self.assertSpyCallCount(cache_func, 1)

    def test_with_cache_get_error(self) -> None:
        """Testing cache_memoize_iter with cache.get() error"""
        cache_key = 'abc123'
        data_yielded = []

        data1, pickled_data_1 = self.build_test_chunk_data(num_chunks=2)
        data2, pickled_data_2 = self.build_test_chunk_data(num_chunks=2)

        def cache_func():
            data_yielded.append('data1')
            yield data1

            data_yielded.append('data2')
            yield data2

        self.spy_on(cache_func)

        # Crash on any cache.get() calls.
        self.spy_on(cache.get, op=kgb.SpyOpRaise(Exception('Oh no')))

        # A get() error will propagate up to the caller.
        #
        # A cache.get() error will log an error and continue on as normal.
        with self.assertLogs() as logs:
            result = cache_memoize_iter(cache_key, cache_func,
                                        compress_large_data=False)

            self.assertTrue(inspect.isgenerator(result))
            self.assertEqual(data_yielded, [])

            self.assertEqual(next(result), data1)
            self.assertEqual(data_yielded, ['data1'])

            self.assertEqual(next(result), data2)
            self.assertEqual(data_yielded, ['data1', 'data2'])

            with self.assertRaises(StopIteration):
                next(result)

        self.assertEqual(len(logs.output), 2)
        self.assertRegex(
            logs.output[0],
            re.compile(
                r'^ERROR:djblets\.cache\.backend:Error fetching data from '
                r'cache for key "example\.com:abc123": Oh no\n'
                r'Traceback.*Exception: Oh no',
                re.S))
        self.assertEqual(
            logs.output[1],
            'ERROR:djblets.cache.backend:Failed to fetch large or iterable '
            'data entry count from cache for key "example.com:abc123". '
            'Rebuilding data. Error = Oh no')

        self.assertSpyCallCount(cache_func, 1)

    def test_with_cache_set_error(self) -> None:
        """Testing cache_memoize_iter with cache.set() error"""
        cache_key = 'abc123'
        data_yielded = []

        data1 = self.build_test_chunk_data(num_chunks=2)[0]
        data2 = self.build_test_chunk_data(num_chunks=2)[0]

        def cache_func():
            yield data1
            data_yielded.append('data1')

            yield data2
            data_yielded.append('data2')

        self.spy_on(cache_func)

        # Crash on any cache.set() calls.
        #
        # A cache.set() error will log an error and continue on as normal.
        @self.spy_for(cache.set)
        def _cache_set(_self, key, *args, **kwargs):
            if key == 'example.com:abc123':
                raise Exception('Oh no')

        with self.assertLogs() as logs:
            results = list(cache_memoize_iter(cache_key, cache_func,
                                              compress_large_data=False))

        self.assertEqual(len(logs.output), 2)
        self.assertRegex(
            logs.output[0],
            re.compile(
                r'^ERROR:djblets\.cache\.backend:Error setting data in cache '
                r'for key "example.com:abc123": Oh no\n'
                r'Traceback.*Exception: Oh no',
                re.S))
        self.assertEqual(
            logs.output[1],
            'ERROR:djblets.cache.backend:Failed to store or retrieve large '
            'or iterable cache data for key "example.com:abc123". '
            'Newly-generated data will be returned but not cached. '
            'Error = Oh no')

        self.assertSpyCallCount(cache_func, 1)

        self.assertEqual(data_yielded, ['data1', 'data2'])
        self.assertEqual(len(results), 2)
        self.assertEqual(results, [data1, data2])

    def test_with_cache_set_many_error(self) -> None:
        """Testing cache_memoize_iter with cache.set_many() error"""
        cache_key = 'abc123'
        data_yielded = []

        data1 = self.build_test_chunk_data(num_chunks=2)[0]
        data2 = self.build_test_chunk_data(num_chunks=2)[0]

        def cache_func():
            yield data1
            data_yielded.append('data1')

            yield data2
            data_yielded.append('data2')

        self.spy_on(cache_func)

        # Crash on any cache.set_many() calls.
        #
        # A cache.set_many() error will log an error and continue on as normal.
        self.spy_on(cache.set_many, op=kgb.SpyOpRaise(Exception('Oh no')))

        with self.assertLogs() as logs:
            results = list(cache_memoize_iter(cache_key, cache_func,
                                              compress_large_data=False))

        self.assertEqual(len(logs.output), 2)
        self.assertRegex(
            logs.output[0],
            re.compile(
                r'^ERROR:djblets\.cache\.backend:Unable to store cached data '
                r'for keys \[\'example\.com:abc123-0\']: Oh no\n'
                r'Traceback.*Exception: Oh no',
                re.S))
        self.assertEqual(
            logs.output[1],
            'ERROR:djblets.cache.backend:Failed to store or retrieve large '
            'or iterable cache data for key "example.com:abc123". '
            'Newly-generated data will be returned but not cached. '
            'Error = Oh no')

        self.assertSpyCallCount(cache_func, 1)

        self.assertEqual(data_yielded, ['data1', 'data2'])
        self.assertEqual(len(results), 2)
        self.assertEqual(results, [data1, data2])

    def test_with_lock_and_in_cache(self) -> None:
        """Testing cache_memoize_iter with lock and data in cache"""
        lock = CacheLock(timeout_secs=0.1,
                         retry_secs=0.05)

        self.spy_on(lock.acquire)
        self.spy_on(lock.release)

        cache_key = 'abc123'
        data_yielded = []

        data1 = self.build_test_chunk_data(num_chunks=2)[0]
        data2 = self.build_test_chunk_data(num_chunks=2)[0]

        def cache_func() -> Iterator[str]:
            yield data1
            data_yielded.append('data1')

            yield data2
            data_yielded.append('data2')

        self.spy_on(cache_func)

        cache.set(make_cache_key(cache_key), 'existing result')

        results = list(cache_memoize_iter(cache_key,
                                          cache_func,
                                          compress_large_data=False,
                                          lock=lock))
        self.assertEqual(data_yielded, ['data1', 'data2'])
        self.assertEqual(len(results), 2)
        self.assertEqual(results, [data1, data2])

        self.assertSpyCallCount(cache_func, 1)

        self.assertSpyNotCalled(lock.acquire)
        self.assertSpyNotCalled(lock.release)
        self.assertIsNone(cache.get(lock.full_cache_key))

    def test_with_lock_and_cache_miss(self) -> None:
        """Testing cache_memoize_iter with lock and cache miss"""
        lock = CacheLock(timeout_secs=0.1,
                         retry_secs=0.05)

        self.spy_on(lock.acquire)
        self.spy_on(lock.release)

        cache_key = 'abc123'
        data_yielded = []

        data1 = self.build_test_chunk_data(num_chunks=2)[0]
        data2 = self.build_test_chunk_data(num_chunks=2)[0]

        def cache_func() -> Iterator[str]:
            self.assertEqual(cache.get(lock.full_cache_key), lock.token)

            yield data1
            data_yielded.append('data1')

            yield data2
            data_yielded.append('data2')

        self.spy_on(cache_func)

        results = list(cache_memoize_iter(cache_key,
                                          cache_func,
                                          compress_large_data=False,
                                          lock=lock))
        self.assertEqual(data_yielded, ['data1', 'data2'])
        self.assertEqual(len(results), 2)
        self.assertEqual(results, [data1, data2])

        self.assertSpyCallCount(cache_func, 1)

        self.assertSpyCallCount(lock.acquire, 1)
        self.assertSpyCallCount(lock.release, 1)
        self.assertIsNone(cache.get(lock.full_cache_key))

    def test_with_lock_and_in_cache_after_lock(self) -> None:
        """Testing cache_memoize_iter with lock and data in cache after lock
        """
        existing1 = self.build_test_chunk_data(data_char='z',
                                               num_chunks=2)[0]
        existing2 = self.build_test_chunk_data(data_char='z',
                                               num_chunks=2)[0]

        lock = CacheLock(timeout_secs=0.1,
                         retry_secs=0.05)

        def _lock_acquire(_self, *args, **kwargs) -> bool:
            list(cache_memoize_iter(cache_key,
                                    lambda: [existing1, existing2],
                                    compress_large_data=False))

            return lock.acquire.call_original(*args, **kwargs)

        self.spy_on(lock.acquire, call_fake=_lock_acquire)
        self.spy_on(lock.release)

        cache_key = 'abc123'
        data_yielded = []

        data1 = self.build_test_chunk_data(num_chunks=2)[0]
        data2 = self.build_test_chunk_data(num_chunks=2)[0]

        def cache_func() -> Iterator[str]:
            yield data1
            data_yielded.append('data1')

            yield data2
            data_yielded.append('data2')

        self.spy_on(cache_func)

        results = list(cache_memoize_iter(cache_key,
                                          cache_func,
                                          compress_large_data=False,
                                          lock=lock))
        self.assertEqual(data_yielded, [])
        self.assertEqual(len(results), 2)
        self.assertEqual(results, [existing1, existing2])

        self.assertSpyNotCalled(cache_func)

        self.assertSpyCallCount(lock.acquire, 1)
        self.assertSpyCallCount(lock.release, 1)
        self.assertIsNone(cache.get(lock.full_cache_key))

    def test_with_lock_and_wait_with_result(self) -> None:
        """Testing cache_memoize_iter with lock and waiting with result
        from cache
        """
        existing_lock = CacheLock(key='lock-key')
        lock_key = existing_lock.full_cache_key

        with existing_lock as locked:
            self.assertTrue(locked)

            existing1 = self.build_test_chunk_data(data_char='z',
                                                   num_chunks=2)[0]
            existing2 = self.build_test_chunk_data(data_char='z',
                                                   num_chunks=2)[0]

            new_lock = CacheLock(key='lock-key',
                                 timeout_secs=0.1,
                                 retry_secs=0.05)

            def _lock_acquire(_self, *args, **kwargs) -> bool:
                # Place a value in cache and release the lock so the new
                # lock can be acquired.
                list(cache_memoize_iter(cache_key,
                                        lambda: [existing1, existing2],
                                        compress_large_data=False))
                existing_lock.release()

                return new_lock.acquire.call_original(*args, **kwargs)

            self.spy_on(new_lock.acquire, call_fake=_lock_acquire)
            self.spy_on(new_lock.release)

            cache_key = 'abc123'
            data_yielded = []

            data1 = self.build_test_chunk_data(num_chunks=2)[0]
            data2 = self.build_test_chunk_data(num_chunks=2)[0]

            def cache_func() -> Iterator[str]:
                yield data1
                data_yielded.append('data1')

                yield data2
                data_yielded.append('data2')

            self.spy_on(cache_func)

            results = list(cache_memoize_iter(cache_key,
                                              cache_func,
                                              compress_large_data=False,
                                              lock=new_lock))
            self.assertEqual(data_yielded, [])
            self.assertEqual(len(results), 2)
            self.assertEqual(results, [existing1, existing2])

            self.assertSpyNotCalled(cache_func)

            self.assertSpyCallCount(new_lock.acquire, 1)
            self.assertSpyCallCount(new_lock.release, 1)

            self.assertIsNone(cache.get(lock_key))

        self.assertIsNone(cache.get(lock_key))

    def test_with_lock_and_wait_with_timeout(self) -> None:
        """Testing cache_memoize_iter with lock and waiting with timeout"""
        existing_lock = CacheLock(key='lock-key')
        lock_key = existing_lock.full_cache_key

        with existing_lock as locked:
            self.assertTrue(locked)

            new_lock = CacheLock(key='lock-key',
                                 timeout_secs=0.1,
                                 retry_secs=0.05)

            self.spy_on(new_lock.acquire)
            self.spy_on(new_lock.release)

            cache_key = 'abc123'
            data_yielded = []

            data1 = self.build_test_chunk_data(num_chunks=2)[0]
            data2 = self.build_test_chunk_data(num_chunks=2)[0]

            def cache_func() -> Iterator[str]:
                yield data1
                data_yielded.append('data1')

                yield data2
                data_yielded.append('data2')

            self.spy_on(cache_func)

            with self.assertLogs() as cm:
                results = list(cache_memoize_iter(cache_key,
                                                  cache_func,
                                                  compress_large_data=False,
                                                  lock=new_lock))

            self.assertEqual(data_yielded, ['data1', 'data2'])
            self.assertEqual(len(results), 2)
            self.assertEqual(results, [data1, data2])

            self.assertSpyCallCount(cache_func, 1)

            self.assertSpyCallCount(new_lock.acquire, 1)
            self.assertSpyNotCalled(new_lock.release)
            self.assertSpyLastRaisedMessage(
                new_lock.acquire,
                TimeoutError,
                'Timed out waiting for lock: example.com:lock-key')

            self.assertEqual(cm.output, [
                f'WARNING:djblets.protect.locks:Timed out waiting for cache '
                f'lock "example.com:lock-key" (token "{new_lock.token}") '
                f'for 0.1 seconds',

                f'ERROR:djblets.cache.backend:Timeout waiting on distributed '
                f'cache lock {new_lock!r}',
            ])

            self.assertEqual(cache.get(lock_key), existing_lock.token)

        self.assertIsNone(cache.get(lock_key))

    def test_with_lock_and_wait_with_timeout_and_value_in_cache(self) -> None:
        """Testing cache_memoize_iter with lock and waiting with timeout and
        new value in cache
        """
        existing_lock = CacheLock(key='lock-key')
        lock_key = existing_lock.full_cache_key

        with existing_lock as locked:
            self.assertTrue(locked)

            existing1 = self.build_test_chunk_data(data_char='z',
                                                   num_chunks=2)[0]
            existing2 = self.build_test_chunk_data(data_char='z',
                                                   num_chunks=2)[0]

            new_lock = CacheLock(key='lock-key',
                                 timeout_secs=0.1,
                                 retry_secs=0.05)

            def _lock_acquire(_self, *args, **kwargs) -> bool:
                # Place a value in cache and release the lock so the new
                # lock can be acquired.
                list(cache_memoize_iter(cache_key,
                                        lambda: [existing1, existing2],
                                        compress_large_data=False))

                return new_lock.acquire.call_original(*args, **kwargs)

            self.spy_on(new_lock.acquire, call_fake=_lock_acquire)
            self.spy_on(new_lock.release)

            cache_key = 'abc123'
            data_yielded = []

            def cache_func() -> Iterator[str]:
                yield self.build_test_chunk_data(num_chunks=2)[0]
                data_yielded.append('data1')

            self.spy_on(cache_func)

            with self.assertLogs() as cm:
                results = list(cache_memoize_iter(cache_key,
                                                  cache_func,
                                                  compress_large_data=False,
                                                  lock=new_lock))

            self.assertEqual(data_yielded, [])
            self.assertEqual(len(results), 2)
            self.assertEqual(results, [existing1, existing2])

            self.assertSpyNotCalled(cache_func)

            self.assertSpyCallCount(new_lock.acquire, 1)
            self.assertSpyNotCalled(new_lock.release)
            self.assertSpyLastRaisedMessage(
                new_lock.acquire,
                TimeoutError,
                'Timed out waiting for lock: example.com:lock-key')

            self.assertEqual(cm.output, [
                f'WARNING:djblets.protect.locks:Timed out waiting for cache '
                f'lock "example.com:lock-key" (token "{new_lock.token}") '
                f'for 0.1 seconds',

                f'ERROR:djblets.cache.backend:Timeout waiting on distributed '
                f'cache lock {new_lock!r}',
            ])

            self.assertEqual(cache.get(lock_key), existing_lock.token)

        self.assertIsNone(cache.get(lock_key))


class MakeCacheKeyTests(BaseCacheTestCase):
    """Unit tests for make_cache_key."""

    def test_default(self) -> None:
        """Testing make_cache_key"""
        self._check_key('test123',
                        'example.com:test123')

    def test_with_sequence(self) -> None:
        """Testing make_cache_key with key sequence"""
        self._check_key(('test', '123'),
                        'example.com:test:123')

    def test_with_sequence_escapes(self) -> None:
        """Testing make_cache_key with key sequence escapes parts"""
        self._check_key(('%test%', '%1:2:3%'),
                        'example.com:%25test%25:%251%3A2%3A3%25')

    @override_settings(SITE_ROOT='/subdir/')
    def test_with_site_root(self) -> None:
        """Testing make_cache_key with SITE_ROOT"""
        self._check_key('test123',
                        'example.com:/subdir/:test123')

    @override_settings(SITE_ROOT='/subdir/')
    def test_with_site_root_and_sequence(self) -> None:
        """Testing make_cache_key with SITE_ROOT and key sequence"""
        self._check_key(('test', ':123'),
                        'example.com:/subdir/:test:%3A123')

    def test_without_site(self) -> None:
        """Testing make_cache_key without Site object."""
        Site.objects.all().delete()
        self._check_key('test123',
                        'test123')

    def test_without_site_and_sequence(self) -> None:
        """Testing make_cache_key without Site object and key sequence"""
        Site.objects.all().delete()
        self._check_key(('test', ':123'),
                        'test:%3A123')

    def test_with_unicode(self) -> None:
        """Testing make_cache_key with Unicode characters"""
        self._check_key('test🥳123',
                        'example.com:test🥳123')

    def test_with_unicode_and_sequence(self) -> None:
        """Testing make_cache_key with Unicode characters and key sequence"""
        self._check_key((':test', '🥳123'),
                        'example.com:%3Atest:🥳123')

    def test_with_invalid_chars(self) -> None:
        """Testing make_cache_key with invalid characters"""
        self._check_key('test\0\tkey !"\x7f',
                        r'example.com:test\x00\x09key\x20!"\x7f')

    def test_with_invalid_chars_and_sequence(self) -> None:
        """Testing make_cache_key with invalid characters and key sequence"""
        self._check_key(('t:est\0\t', 'k%ey !"\x7f'),
                        r'example.com:t%3Aest\x00\x09:k%25ey\x20!"\x7f')

    def test_with_large_keys_max_length(self) -> None:
        """Testing make_cache_key with large keys at max length"""
        length = MAX_KEY_SIZE - len('example.com:')
        self._check_key(
            'x' * length,
            'example.com:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
            'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
            'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
            'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')

    def test_with_large_keys_max_length_and_sequence(self) -> None:
        """Testing make_cache_key with large keys at max length and key
        sequence
        """
        length = MAX_KEY_SIZE - len('example.com:') - 1
        self._check_key(
            ('x' * 10, 'x' * (length - 10)),
            'example.com:xxxxxxxxxx:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
            'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
            'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
            'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')

    def test_with_large_keys_overflow(self) -> None:
        """Testing make_cache_key with large keys > max length"""
        length = MAX_KEY_SIZE - len('example.com:') + 1
        self._check_key(
            'x' * length,
            'example.com:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
            'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
            'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxedf8474a1b91e737'
            'ec28252abe7a8aa5604539b239505e8ccad8890a44198c58')

    def test_with_large_keys_overflow_and_sequence(self) -> None:
        """Testing make_cache_key with large keys > max length and key
        sequence
        """
        length = MAX_KEY_SIZE - len('example.com:')
        self._check_key(
            ('x' * 10, 'x' * (length - 10)),
            'example.com:xxxxxxxxxx:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
            'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
            'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxc1f6edf6f476acb9'
            '3b1858f99ee2fbe8dac1907d595c7f9f9d211fe7c46335c1')

    def test_with_encryption(self) -> None:
        """Testing make_cache_key with use_encryption=True"""
        self._check_key(
            'abc123',
            '0a3195ea908f9bd178ab3c67a257ea4e7954e4b67ac240d1c86953953cde3a0b',
            use_encryption=True)

    def test_with_encryption_and_sequence(self) -> None:
        """Testing make_cache_key with use_encryption=True and key sequence"""
        self._check_key(
            ('abc', '123'),
            '61f180a36b711a5364235cc13096d237b5b27256be8aa78e723faf1d73237851',
            use_encryption=True)

    def test_with_encryption_and_custom_encryption_key(self) -> None:
        """Testing make_cache_key with use_encryption=True and custom
        encryption_key
        """
        self._check_key(
            'abc123',
            '10c4714f5c6c49045ed25c8da7d04a4be2254fa275fc3b63bdeebe887aee52f9',
            use_encryption=True,
            encryption_key=self.CUSTOM_ENCRYPTION_KEY)

    def test_with_encryption_and_custom_encryption_key_and_sequence(
        self,
    ) -> None:
        """Testing make_cache_key with use_encryption=True and custom
        encryption_key and key sequence
        """
        self._check_key(
            ('abc', '123'),
            'c93f54fcf3063f17a1bb59d74e3ecd146a1154ea0bf7a4a7d95c82e71c56be7e',
            use_encryption=True,
            encryption_key=self.CUSTOM_ENCRYPTION_KEY)

    @override_settings(DJBLETS_CACHE_FORCE_ENCRYPTION=True)
    def test_with_force_encryption_setting(self) -> None:
        """Testing make_cache_key with
        settings.DJBLETS_CACHE_FORCE_ENCRYPTION=True
        """
        self._check_key(
            'abc123',
            '0a3195ea908f9bd178ab3c67a257ea4e7954e4b67ac240d1c86953953cde3a0b')

    @override_settings(DJBLETS_CACHE_FORCE_ENCRYPTION=True)
    def test_with_force_encryption_setting_and_key_sequence(self) -> None:
        """Testing make_cache_key with
        settings.DJBLETS_CACHE_FORCE_ENCRYPTION=True and key sequence
        """
        self._check_key(
            ('abc', '123'),
            '61f180a36b711a5364235cc13096d237b5b27256be8aa78e723faf1d73237851')

    def _check_key(
        self,
        key: str | Sequence[str],
        expected_key: str,
        **kwargs,
    ) -> None:
        """Check the results of a key, and ensure it works in cache.

        Args:
            key (str or Sequence[str]):
                The key to build a cache key out of.

            expected_key (str):
                The expected full cache key.

            **kwargs (dict):
                Keyword arguments to pass to
                :py:func:`~djblets.cache.backend.make_cache_key`.

        Raises:
            AssertionError:
                The results were not equal.
        """
        full_cache_key = make_cache_key(key, **kwargs)

        self.assertIsInstance(full_cache_key, str)
        self.assertEqual(full_cache_key, expected_key)

        # Generate a second, to be sure nothing changes.
        full_cache_key2 = make_cache_key(key, **kwargs)
        self.assertEqual(full_cache_key, full_cache_key2)

        # Validate the key.
        self.assertEqual(
            list(memcache_key_warnings(full_cache_key)),
            [])

        # Make sure this can be set and retrieved from cache.
        cache.set(full_cache_key, 'test-value')
        self.assertEqual(cache.get(full_cache_key), 'test-value')
