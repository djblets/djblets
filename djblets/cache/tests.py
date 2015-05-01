from __future__ import unicode_literals

import inspect
import zlib

from django.core.cache import cache
from django.utils.six.moves import cPickle as pickle
from kgb import SpyAgency

from djblets.cache.backend import (cache_memoize, cache_memoize_iter,
                                   make_cache_key,
                                   CACHE_CHUNK_SIZE)
from djblets.testing.testcases import TestCase


class CacheTests(SpyAgency, TestCase):
    def tearDown(self):
        super(CacheTests, self).tearDown()

        cache.clear()

    def test_cache_memoize(self):
        """Testing cache_memoize"""
        cacheKey = 'abc123'
        testStr = 'Test 123'

        def cacheFunc(cacheCalled=[]):
            self.assertTrue(not cacheCalled)
            cacheCalled.append(True)
            return testStr

        result = cache_memoize(cacheKey, cacheFunc)
        self.assertEqual(result, testStr)

        # Call a second time. We should only call cacheFunc once.
        result = cache_memoize(cacheKey, cacheFunc)
        self.assertEqual(result, testStr)

    def test_cache_memoize_large_files_uncompressed(self):
        """Testing cache_memoize with large files without compression"""
        cache_key = 'abc123'

        # This takes into account the size of the pickle data, and will
        # get us to exactly 2 chunks of data in cache.
        data, pickled_data = self._build_test_chunk_data(num_chunks=2)

        def cache_func():
            return data

        self.spy_on(cache_func, call_original=True)

        result = cache_memoize(cache_key, cache_func, large_data=True,
                               compress_large_data=False)
        self.assertEqual(result, data)
        self.assertTrue(cache_func.spy.called)

        cache_key_0 = make_cache_key('%s-0' % cache_key)
        cache_key_1 = make_cache_key('%s-1' % cache_key)

        self.assertTrue(make_cache_key(cache_key) in cache)
        self.assertTrue(cache_key_0 in cache)
        self.assertTrue(cache_key_1 in cache)
        self.assertFalse(make_cache_key('%s-2' % cache_key) in cache)

        # Verify the contents of the stored data.
        stored_data = b''.join(cache.get(cache_key_0) + cache.get(cache_key_1))
        self.assertEqual(stored_data, pickled_data)

        # Try fetching the data we stored.
        cache_func.spy.reset_calls()

        result = cache_memoize(cache_key, cache_func, large_data=True,
                               compress_large_data=False)
        self.assertEqual(result, data)
        self.assertFalse(cache_func.spy.called)

    def test_cache_memoize_large_files_uncompressed_off_by_one(self):
        """Testing cache_memoize with large files without compression and
        one byte larger than an even chunk size."""
        cache_key = 'abc123'

        # This takes into account the size of the pickle data, and will
        # get us to just barely 3 chunks of data in cache.
        data = self._build_test_chunk_data(num_chunks=2)[0] + 'x'
        pickled_data = pickle.dumps(data)

        def cache_func():
            return data

        self.spy_on(cache_func, call_original=True)

        result = cache_memoize(cache_key, cache_func, large_data=True,
                               compress_large_data=False)
        self.assertEqual(result, data)
        self.assertTrue(cache_func.spy.called)

        cache_key_0 = make_cache_key('%s-0' % cache_key)
        cache_key_1 = make_cache_key('%s-1' % cache_key)
        cache_key_2 = make_cache_key('%s-2' % cache_key)

        self.assertTrue(make_cache_key(cache_key) in cache)
        self.assertTrue(cache_key_0 in cache)
        self.assertTrue(cache_key_1 in cache)
        self.assertTrue(cache_key_2 in cache)
        self.assertFalse(make_cache_key('%s-3' % cache_key) in cache)

        # Verify the contents of the stored data.
        stored_data = b''.join(cache.get(cache_key_0) +
                               cache.get(cache_key_1) +
                               cache.get(cache_key_2))
        self.assertEqual(stored_data, pickled_data)

        # Try fetching the data we stored.
        cache_func.spy.reset_calls()

        result = cache_memoize(cache_key, cache_func, large_data=True,
                               compress_large_data=False)
        self.assertEqual(result, data)
        self.assertFalse(cache_func.spy.called)

    def test_cache_memoize_large_files_compressed(self):
        """Testing cache_memoize with large files with compression"""
        cache_key = 'abc123'

        data, pickled_data = self._build_test_chunk_data(num_chunks=2)

        def cache_func():
            return data

        self.spy_on(cache_func, call_original=True)

        result = cache_memoize(cache_key, cache_func, large_data=True,
                               compress_large_data=True)
        self.assertTrue(cache_func.spy.called)

        cache_key_0 = make_cache_key('%s-0' % cache_key)

        self.assertTrue(make_cache_key(cache_key) in cache)
        self.assertTrue(cache_key_0 in cache)
        self.assertFalse(make_cache_key('%s-1' % cache_key) in cache)
        self.assertFalse(make_cache_key('%s-2' % cache_key) in cache)

        # Verify the contents of the stored data.
        stored_data = cache.get(cache_key_0)[0]
        self.assertEqual(stored_data, zlib.compress(pickled_data))

        # Try fetching the data we stored.
        cache_func.spy.reset_calls()
        result = cache_memoize(cache_key, cache_func, large_data=True,
                               compress_large_data=True)
        self.assertEqual(result, data)
        self.assertFalse(cache_func.spy.called)

    def test_cache_memoize_large_files_load_uncompressed(self):
        """Testing cache_memoize with large files without compression and
        loading data
        """
        cache_key = 'abc123'

        # This takes into account the size of the pickle data, and will
        # get us to exactly 2 chunks of data in cache.
        data, pickled_data = self._build_test_chunk_data(num_chunks=2)

        cache.set(make_cache_key(cache_key), '2')
        cache.set(make_cache_key('%s-0' % cache_key),
                  [pickled_data[:CACHE_CHUNK_SIZE]])
        cache.set(make_cache_key('%s-1' % cache_key),
                  [pickled_data[CACHE_CHUNK_SIZE:]])

        def cache_func():
            return ''

        self.spy_on(cache_func, call_original=True)

        result = cache_memoize(cache_key, cache_func, large_data=True,
                               compress_large_data=False)
        self.assertEqual(result, data)
        self.assertFalse(cache_func.spy.called)

    def test_cache_memoize_large_files_load_compressed(self):
        """Testing cache_memoize with large files with compression and
        loading cached data
        """
        cache_key = 'abc123'

        data, pickled_data = self._build_test_chunk_data(num_chunks=2)
        stored_data = zlib.compress(pickled_data)
        self.assertTrue(len(stored_data) < CACHE_CHUNK_SIZE)

        cache.set(make_cache_key(cache_key), '1')
        cache.set(make_cache_key('%s-0' % cache_key), [stored_data])

        def cache_func():
            return ''

        self.spy_on(cache_func, call_original=True)

        result = cache_memoize(cache_key, cache_func, large_data=True,
                               compress_large_data=True)
        self.assertEqual(result, data)
        self.assertFalse(cache_func.spy.called)

    def test_cache_memoize_large_files_missing_chunk(self):
        """Testing cache_memoize with loading large files with missing chunks
        """
        cache_key = 'abc123'

        # This takes into account the size of the pickle data, and will
        # get us to exactly 2 chunks of data in cache.
        data, pickled_data = self._build_test_chunk_data(num_chunks=2)

        cache.set(make_cache_key(cache_key), '2')
        cache.set(make_cache_key('%s-0' % cache_key),
                  [pickled_data[:CACHE_CHUNK_SIZE]])

        def cache_func():
            return data

        self.spy_on(cache_func, call_original=True)

        result = cache_memoize(cache_key, cache_func, large_data=True,
                               compress_large_data=False)
        self.assertEqual(len(result), len(data))
        self.assertEqual(result, data)
        self.assertTrue(cache_func.spy.called)

    def test_cache_memoize_iter_uncompressed(self):
        """Testing cache_memoize_iter without compression"""
        cache_key = 'abc123'
        data_yielded = []

        data1, pickled_data_1 = self._build_test_chunk_data(num_chunks=2)
        data2, pickled_data_2 = self._build_test_chunk_data(num_chunks=2)

        def cache_func():
            data_yielded.append('data1')
            yield data1

            data_yielded.append('data2')
            yield data2

        self.spy_on(cache_func, call_original=True)

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

        self.assertTrue(cache_func.spy.called)

        cache_key_main = make_cache_key(cache_key)
        cache_key_0 = make_cache_key('%s-0' % cache_key)
        cache_key_1 = make_cache_key('%s-1' % cache_key)
        cache_key_2 = make_cache_key('%s-2' % cache_key)
        cache_key_3 = make_cache_key('%s-3' % cache_key)

        self.assertTrue(cache_key_main in cache)
        self.assertTrue(cache_key_0 in cache)
        self.assertTrue(cache_key_1 in cache)
        self.assertTrue(cache_key_2 in cache)
        self.assertTrue(cache_key_3 in cache)
        self.assertFalse(make_cache_key('%s-4' % cache_key) in cache)

        # Verify the contents of the stored data.
        stored_data = b''.join(cache.get(cache_key_0) +
                               cache.get(cache_key_1) +
                               cache.get(cache_key_2) +
                               cache.get(cache_key_3))
        self.assertEqual(cache.get(cache_key_main), '4')
        self.assertEqual(stored_data, pickled_data_1 + pickled_data_2)

        # Try fetching the data we stored.
        cache_func.spy.reset_calls()
        data_yielded = []

        result = cache_memoize_iter(cache_key, cache_func,
                                    compress_large_data=False)
        self.assertTrue(inspect.isgenerator(result))

        self.assertEqual(next(result), data1)
        self.assertEqual(next(result), data2)

        with self.assertRaises(StopIteration):
            next(result)

        self.assertEqual(data_yielded, [])
        self.assertFalse(cache_func.spy.called)

    def test_cache_memoize_iter_compressed(self):
        """Testing cache_memoize_iter with compression"""
        cache_key = 'abc123'
        data_yielded = []

        # This takes into account the size of the pickle data, and will
        # get us to exactly 2 chunks of data in cache, each.
        data1, pickled_data_1 = self._build_test_chunk_data(num_chunks=2)
        data2, pickled_data_2 = self._build_test_chunk_data(num_chunks=2)

        def cache_func():
            data_yielded.append('data1')
            yield data1

            data_yielded.append('data2')
            yield data2

        self.spy_on(cache_func, call_original=True)

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

        self.assertTrue(cache_func.spy.called)

        cache_key_main = make_cache_key(cache_key)
        cache_key_0 = make_cache_key('%s-0' % cache_key)

        self.assertTrue(cache_key_main in cache)
        self.assertTrue(cache_key_0 in cache)
        self.assertFalse(make_cache_key('%s-1' % cache_key) in cache)

        # Verify the contents of the stored data.
        self.assertEqual(cache.get(cache_key_main), '1')
        self.assertEqual(cache.get(cache_key_0)[0],
                         zlib.compress(pickled_data_1 + pickled_data_2))

        # Try fetching the data we stored.
        cache_func.spy.reset_calls()
        data_yielded = []

        result = cache_memoize_iter(cache_key, cache_func,
                                    compress_large_data=True)
        self.assertTrue(inspect.isgenerator(result))
        self.assertEqual(next(result), data1)
        self.assertEqual(next(result), data2)

        with self.assertRaises(StopIteration):
            next(result)

        self.assertEqual(data_yielded, [])
        self.assertFalse(cache_func.spy.called)

    def _build_test_chunk_data(self, num_chunks):
        """Build enough test data to fill up the specified number of chunks.

        This takes into account the size of the pickle data, and will
        get us to exactly the specified number of chunks of data in the cache.
        """
        data = 'x' * (CACHE_CHUNK_SIZE * num_chunks - 3 * num_chunks)
        pickled_data = pickle.dumps(data)

        self.assertEqual(len(pickled_data), CACHE_CHUNK_SIZE * num_chunks)

        return data, pickled_data
