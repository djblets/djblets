"""Unit tests for djblets.protect.locks.CacheLock.

Version Added:
    5.3
"""

from __future__ import annotations

import logging
import sys

import kgb
from django.core.cache import cache

from djblets.protect.locks import CacheLock
from djblets.testing.testcases import TestCase


# Workaround for different implementations of assertNoLogs() between Django and
# the standard library.
if sys.version_info < (3, 10):
    root_logger = 'root'
else:
    root_logger = None


class CacheLockTests(kgb.SpyAgency, TestCase):
    """Unit tests for CacheLock.

    Version Added:
        5.3
    """

    def setUp(self) -> None:
        super().setUp()

        cache.clear()

    def tearDown(self) -> None:
        super().tearDown()

        cache.clear()

    def test_acquire_with_new_lock(self) -> None:
        """Testing CacheLock.acquire with new lock"""
        lock = CacheLock(key='1D5BC5F3')

        with self.assertLogs(level=logging.DEBUG) as cm:
            self.assertTrue(lock.acquire())

        self.addCleanup(lock.release)

        self.assertEqual(len(cm.output), 1)
        self.assertRegex(
            cm.output[0],
            r'DEBUG:djblets.protect.locks:Acquired cache lock '
            r'"example.com:1D5BC5F3" with token "[\a-z0-9-]+" for 30 '
            r'seconds \(monotonic expiration = \d+\.\d+, '
            r'estimated timestamp = \d+\.\d+\)')

        self.assertTrue(lock.acquired)
        self.assertEqual(cache.get(lock.full_cache_key), lock.token)

    def test_acquire_with_existing_lock_and_not_blocking(self) -> None:
        """Testing CacheLock.acquire with existing lock and blocking=False"""
        existing_lock = CacheLock(key='ACC54266')

        with self.assertLogs(level=logging.DEBUG) as cm:
            self.assertTrue(existing_lock.acquire())

        self.addCleanup(existing_lock.release)

        self.assertEqual(len(cm.output), 1)
        self.assertRegex(
            cm.output[0],
            r'DEBUG:djblets.protect.locks:Acquired cache lock '
            r'"example.com:ACC54266" with token "[\a-z0-9-]+" for 30 '
            r'seconds \(monotonic expiration = \d+\.\d+, '
            r'estimated timestamp = \d+\.\d+\)')

        new_lock = CacheLock(key='ACC54266',
                             blocking=False)
        self.assertFalse(new_lock.blocking)

        with self.assertNoLogs(logger=root_logger, level=logging.DEBUG):
            self.assertFalse(new_lock.acquire())

        self.assertFalse(new_lock.acquired)
        self.assertEqual(cache.get(new_lock.full_cache_key),
                         existing_lock.token)

    def test_acquire_with_existing_lock_and_blocking_and_released(
        self,
    ) -> None:
        """Testing CacheLock.acquire with existing lock and blocking=True and
        lock released
        """
        existing_lock = CacheLock(key='72C7A1A3',
                                  lock_expiration_secs=1)
        new_lock = CacheLock(key='72C7A1A3')

        with self.assertLogs(level=logging.DEBUG) as cm:
            self.assertTrue(existing_lock.acquire())

        self.addCleanup(existing_lock.release)

        self.assertEqual(len(cm.output), 1)
        self.assertRegex(
            cm.output[0],
            r'DEBUG:djblets.protect.locks:Acquired cache lock '
            r'"example.com:72C7A1A3" with token "[\a-z0-9-]+" for 1 '
            r'seconds \(monotonic expiration = \d+\.\d+, '
            r'estimated timestamp = \d+\.\d+\)')

        with self.assertLogs(level=logging.DEBUG) as cm:
            self.assertTrue(new_lock.acquire())

        self.addCleanup(new_lock.release)

        self.assertEqual(len(cm.output), 1)
        self.assertRegex(
            cm.output[0],
            r'DEBUG:djblets.protect.locks:Acquired cache lock '
            r'"example.com:72C7A1A3" with token "[\a-z0-9-]+" for 30 '
            r'seconds \(monotonic expiration = \d+\.\d+, '
            r'estimated timestamp = \d+\.\d+\)')

        self.assertTrue(new_lock.acquired)
        self.assertEqual(cache.get(new_lock.full_cache_key),
                         new_lock.token)

    def test_acquire_with_existing_lock_and_blocking_and_timeout(self) -> None:
        """Testing CacheLock.acquire with existing lock and blocking=True and
        lock released
        """
        existing_lock = CacheLock(key='44A816B0')
        existing_lock.acquire()
        self.addCleanup(existing_lock.release)

        new_lock = CacheLock(key='44A816B0',
                             timeout_secs=0.05)

        message = 'Timed out waiting for lock: example.com:44A816B0'

        with self.assertLogs(level=logging.DEBUG) as cm:
            with self.assertRaisesMessage(TimeoutError, message):
                self.assertFalse(new_lock.acquire())

        self.assertEqual(
            cm.output,
            [
                f'WARNING:djblets.protect.locks:Timed out waiting for cache '
                f'lock "example.com:44A816B0" (token "{new_lock.token}") '
                f'for 0.05 seconds',
            ])

        self.assertFalse(new_lock.acquired)
        self.assertEqual(cache.get(new_lock.full_cache_key),
                         existing_lock.token)

    def test_acquire_with_blocking_false(self) -> None:
        """Testing CacheLock.acquire with blocking=False overriding
        constructor
        """
        existing_lock = CacheLock(key='DF71C7BC')
        existing_lock.acquire()
        self.addCleanup(existing_lock.release)

        new_lock = CacheLock(key='DF71C7BC',
                             blocking=True,
                             timeout_secs=10)

        with self.assertNoLogs(logger=root_logger, level=logging.DEBUG):
            self.assertFalse(new_lock.acquire(blocking=False))

        self.assertFalse(new_lock.acquired)
        self.assertEqual(cache.get(new_lock.full_cache_key),
                         existing_lock.token)

    def test_release_with_acquired(self) -> None:
        """Testing CacheLock.release with lock acquired"""
        lock = CacheLock(key='F0E07CB8')
        lock.acquire()

        with self.assertLogs(level=logging.DEBUG) as cm:
            lock.release()

        self.assertEqual(
            cm.output,
            [
                f'DEBUG:djblets.protect.locks:Released cache lock '
                f'"example.com:F0E07CB8" (token "{lock.token}")'
            ])

        self.assertFalse(lock.acquired)
        self.assertIsNone(cache.get(lock.full_cache_key))

    def test_release_with_not_acquired(self) -> None:
        """Testing CacheLock.release with lock not acquired"""
        lock = CacheLock(key='CC8E30F5')

        message = 'Cannot release a lock that was not acquired.'

        with self.assertNoLogs(logger=root_logger, level=logging.DEBUG):
            with self.assertRaisesMessage(RuntimeError, message):
                lock.release()

        self.assertFalse(lock.acquired)
        self.assertIsNone(cache.get(lock.full_cache_key))

    def test_release_with_lock_token_replaced(self) -> None:
        """Testing CacheLock.release with lock token replaced"""
        lock = CacheLock(key='A49A3C30')
        lock.acquire()

        cache.set(lock.full_cache_key, 'XXX')

        with self.assertLogs(level=logging.DEBUG) as cm:
            lock.release()

        self.assertEqual(
            cm.output,
            [
                f'DEBUG:djblets.protect.locks:Released cache lock '
                f'"example.com:A49A3C30" (token "{lock.token}")'
            ])

        self.assertFalse(lock.acquired)
        self.assertEqual(cache.get(lock.full_cache_key), 'XXX')

    def test_release_with_held_beyond_expiration(self) -> None:
        """Testing CacheLock.release with lock held beyond epiration"""
        lock = CacheLock(key='4BB55758',
                         lock_expiration_secs=1)
        lock.acquire()
        lock._lock_expires_time -= 100

        self.spy_on(cache.touch)

        with self.assertLogs(level=logging.DEBUG) as cm:
            lock.release()

        self.assertEqual(
            cm.output,
            [
                f'DEBUG:djblets.protect.locks:Released cache lock '
                f'"example.com:4BB55758" (token "{lock.token}"), which '
                f'already expired from cache',
            ])

        self.assertFalse(lock.acquired)
        self.assertSpyNotCalled(cache.touch)

        # We're simulating that a new key may be in cache at the end of
        # this.
        self.assertIsNotNone(cache.get(lock.full_cache_key))

    def test_release_with_lost_key(self) -> None:
        """Testing CacheLock.release with lock key not in cache"""
        lock = CacheLock(key='84E054E5')
        lock.acquire()

        self.spy_on(cache.touch, op=kgb.SpyOpReturn(False))

        with self.assertLogs(level=logging.DEBUG) as cm:
            lock.release()

        self.assertEqual(
            cm.output,
            [
                f'DEBUG:djblets.protect.locks:Released cache lock '
                f'"example.com:84E054E5" (token '
                f'"{lock.token}"), which already expired from cache',
            ])

        self.assertFalse(lock.acquired)

        self.assertSpyCalledWith(
            cache.touch,
            'example.com:84E054E5',
            timeout=30)

        # We're simulating that a new key may be in cache at the end of
        # this.
        self.assertIsNotNone(cache.get(lock.full_cache_key))

    def test_update_expiration(self) -> None:
        """Testing CacheLock.update_expiration"""
        self.spy_on(cache.touch)

        lock = CacheLock(key='E977344F')
        lock.acquire()
        self.addCleanup(lock.release)

        with self.assertLogs(level=logging.DEBUG) as cm:
            lock.update_expiration()

        self.assertEqual(len(cm.output), 1)
        self.assertRegex(
            cm.output[0],
            r'DEBUG:djblets.protect.locks:Extended cache lock '
            r'"example.com:E977344F" \(token "[a-f0-9-]+"\) to 30 '
            r'seconds \(monotonic expiration = \d+\.\d+, estimated '
            r'timestamp = \d+\.\d+\)')

        self.assertSpyCalledWith(
            cache.touch,
            'example.com:E977344F',
            timeout=30)

    def test_update_expiration_with_custom_time(self) -> None:
        """Testing CacheLock.update_expiration with custom expiration time"""
        self.spy_on(cache.touch)

        lock = CacheLock(key='587961F7')
        lock.acquire()
        self.addCleanup(lock.release)

        with self.assertLogs(level=logging.DEBUG) as cm:
            lock.update_expiration(100)

        self.assertEqual(len(cm.output), 1)
        self.assertRegex(
            cm.output[0],
            r'DEBUG:djblets.protect.locks:Extended cache lock '
            r'"example.com:587961F7" \(token "[a-f0-9-]+"\) to 100 '
            r'seconds \(monotonic expiration = \d+\.\d+, estimated '
            r'timestamp = \d+\.\d+\)')

        self.assertSpyCalledWith(
            cache.touch,
            'example.com:587961F7',
            timeout=100)

    def test_update_expiration_with_lost_lock(self) -> None:
        """Testing CacheLock.update_expiration with lost lock"""
        self.spy_on(cache.touch, op=kgb.SpyOpReturn(False))

        lock = CacheLock(key='47714EF6')
        lock.acquire()
        self.addCleanup(lock.release)

        with self.assertLogs() as cm:
            lock.update_expiration()

        self.assertEqual(
            cm.output,
            [
                f'WARNING:djblets.protect.locks:Cache lock '
                f'"example.com:47714EF6" (token "{lock.token}") fell '
                f'out of cache. The lock is no longer valid.',
            ])

        self.assertSpyCalledWith(
            cache.touch,
            'example.com:47714EF6',
            timeout=30)

    def test_context_manager(self) -> None:
        """Testing CacheLock as context manager"""
        with CacheLock(key='6E58D95B') as lock:
            self.assertTrue(lock.acquired)
            self.assertEqual(cache.get(lock.full_cache_key), lock.token)

        self.assertIsNone(cache.get(lock.full_cache_key))

    def test_del_while_acquired(self) -> None:
        """Testing CacheLock destruction while lock acquired"""
        lock = CacheLock(key='ADAEAFA1')
        lock.acquire()

        with self.assertLogs() as cm:
            del lock

        self.assertEqual(cm.output, [
            'ERROR:djblets.protect.locks:Cache lock "example.com:ADAEAFA1" '
            'was garbage collected without being released! The caller must '
            'be careful to keep this lock around until it is released.'
        ])
