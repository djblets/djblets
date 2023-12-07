import inspect
import pickle
import re
import zlib

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
from djblets.secrets.crypto import AES_BLOCK_SIZE, aes_decrypt, aes_encrypt
from djblets.testing.testcases import TestCase


class BaseCacheTestCase(kgb.SpyAgency, TestCase):
    """Base class for cache-related unit tests."""

    CUSTOM_ENCRYPTION_KEY = b'0123456789abcdef'

    def tearDown(self):
        super().tearDown()

        cache.clear()

    def build_test_chunk_data(self, num_chunks, extra_len=0,
                              use_compression=False, use_encryption=False,
                              encryption_key=None):
        """Build enough test data to fill up the specified number of chunks.

        This takes into account the size of the pickle data, and will
        get us to exactly the specified number of chunks of data in the cache.

        Args:
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

            1. The raw generated data.
            2. The resulting chunk data to store.
        """
        data_len = CACHE_CHUNK_SIZE * num_chunks - 3 * num_chunks + extra_len

        if use_encryption:
            data_len -= AES_BLOCK_SIZE

        data = 'x' * data_len

        chunk_data = pickle.dumps(data, protocol=0)
        self.assertTrue(chunk_data.startswith(b'Vxxxxxxxx'))

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


class MakeCacheKeyTests(BaseCacheTestCase):
    """Unit tests for make_cache_key."""

    def test_default(self):
        """Testing make_cache_key"""
        self._check_key('test123',
                        'example.com:test123')

    @override_settings(SITE_ROOT='/subdir/')
    def test_with_site_root(self):
        """Testing make_cache_key with SITE_ROOT"""
        self._check_key('test123',
                        'example.com:/subdir/:test123')

    def test_without_site(self):
        """Testing make_cache_key without Site object."""
        Site.objects.all().delete()
        self._check_key('test123',
                        'test123')

    def test_with_unicode(self):
        """Testing make_cache_key with Unicode characters"""
        self._check_key('test🥳123',
                        'example.com:test🥳123')

    def test_with_invalid_chars(self):
        """Testing make_cache_key with invalid characters"""
        self._check_key('test\0\tkey !"\x7f',
                        r'example.com:test\x00\x09key\x20!"\x7f')

    def test_with_large_keys_max_length(self):
        """Testing make_cache_key with large keys at max length"""
        length = MAX_KEY_SIZE - len('example.com:')
        self._check_key(
            'x' * length,
            'example.com:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
            'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
            'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
            'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')

    def test_with_large_keys_overflow(self):
        """Testing make_cache_key with large keys > max length"""
        length = MAX_KEY_SIZE - len('example.com:') + 1
        self._check_key(
            'x' * length,
            'example.com:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
            'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
            'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxedf8474a1b91e737'
            'ec28252abe7a8aa5604539b239505e8ccad8890a44198c58')

    def test_with_encryption(self):
        """Testing make_cache_key with use_encryption=True"""
        self._check_key(
            'abc123',
            '0a3195ea908f9bd178ab3c67a257ea4e7954e4b67ac240d1c86953953cde3a0b',
            use_encryption=True)

    def test_with_encryption_and_custom_encryption_key(self):
        """Testing make_cache_key with use_encryption=True and custom
        encryption_key
        """
        self._check_key(
            'abc123',
            '10c4714f5c6c49045ed25c8da7d04a4be2254fa275fc3b63bdeebe887aee52f9',
            use_encryption=True,
            encryption_key=self.CUSTOM_ENCRYPTION_KEY)

    @override_settings(DJBLETS_CACHE_FORCE_ENCRYPTION=True)
    def test_with_force_encryption_setting(self):
        """Testing make_cache_key with
        settings.DJBLETS_CACHE_FORCE_ENCRYPTION=True
        """
        self._check_key(
            'abc123',
            '0a3195ea908f9bd178ab3c67a257ea4e7954e4b67ac240d1c86953953cde3a0b')

    def _check_key(self, key, expected_key, **kwargs):
        """Check the results of a key, and ensure it works in cache.

        Args:
            key (str):
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
