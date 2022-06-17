import inspect
import pickle
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
                                   make_cache_key)
from djblets.testing.testcases import TestCase


class BaseCacheTestCase(kgb.SpyAgency, TestCase):
    """Base class for cache-related unit tests."""

    def tearDown(self):
        super().tearDown()

        cache.clear()

    def build_test_chunk_data(self, num_chunks):
        """Build enough test data to fill up the specified number of chunks.

        This takes into account the size of the pickle data, and will
        get us to exactly the specified number of chunks of data in the cache.

        Args:
            num_chunks (int):
                The number of chunks to build.

        Returns:
            tuple:
            A 2-tuple containing:

            1. The data to cache.
            2. The resulting pickled data.
        """
        data = 'x' * (CACHE_CHUNK_SIZE * num_chunks - 3 * num_chunks)
        pickled_data = pickle.dumps(data, protocol=0)

        self.assertTrue(pickled_data.startswith(b'Vxxxxxxxx'))
        self.assertEqual(len(pickled_data), CACHE_CHUNK_SIZE * num_chunks)

        return data, pickled_data


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
        data = self.build_test_chunk_data(num_chunks=2)[0] + 'x'
        pickled_data = pickle.dumps(data, protocol=0)

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

        data, pickled_data = self.build_test_chunk_data(num_chunks=2)
        stored_data = zlib.compress(pickled_data)
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

    def _check_key(self, key, expected_key):
        """Check the results of a key, and ensure it works in cache.

        Args:
            key (str):
                The key to build a cache key out of.

            expected_key (str):
                The expected full cache key.

        Raises:
            AssertionError:
                The results were not equal.
        """
        full_cache_key = make_cache_key(key)

        self.assertIsInstance(full_cache_key, str)
        self.assertEqual(full_cache_key, expected_key)

        # Validate the key.
        self.assertEqual(
            list(memcache_key_warnings(full_cache_key)),
            [])

        # Make sure this can be set and retrieved from cache.
        cache.set(full_cache_key, 'test-value')
        self.assertEqual(cache.get(full_cache_key), 'test-value')
