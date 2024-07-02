"""Unit tests for djblets.cache.synchronizer.GenerationSynchronizer."""

from __future__ import annotations

import re

import kgb
from django.core.cache import cache

from djblets.cache.synchronizer import GenerationSynchronizer
from djblets.testing.testcases import TestCase


class GenerationSynchronizerTests(kgb.SpyAgency, TestCase):
    """Unit tests for djblets.cache.synchronizer.GenerationSynchronizer."""

    def setUp(self):
        super(GenerationSynchronizerTests, self).setUp()

        self.gen_sync = GenerationSynchronizer('test-synchronizer')

    def test_initial_state(self):
        """Testing GenerationSynchronizer initial state"""
        self.assertIsNotNone(self.gen_sync.sync_gen)

    def test_is_expired_when_expired(self):
        """Testing GenerationSynchronizer.is_expired when expired"""
        cache.set(self.gen_sync.cache_key, self.gen_sync.sync_gen + 1)
        self.assertTrue(self.gen_sync.is_expired())

    def test_is_expired_when_not_expired(self):
        """Testing GenerationSynchronizer.is_expired when not expired"""
        self.assertFalse(self.gen_sync.is_expired())

    def test_is_expired_with_exception(self) -> None:
        """Testing GenerationSynchronizer.is_expired when encountering an
        exception
        """
        self.spy_on(self.gen_sync._get_latest_sync_gen,
                    op=kgb.SpyOpRaise(Exception('Oh no')))

        with self.assertLogs() as logs:
            self.assertTrue(self.gen_sync.is_expired())

        self.assertEqual(len(logs.output), 1)
        self.assertRegex(
            logs.output[0],
            re.compile(
                r'ERROR:djblets\.cache\.synchronizer:Unexpected error '
                r'checking for expiration in cached synchronization '
                r'state key "example\.com:test-synchronizer"\. Is the cache '
                r'server down\? Error = Oh no\n'
                r'Traceback.*Exception: Oh no',
                re.S))

    def test_refresh(self):
        """Testing GenerationSynchronizer.refresh"""
        new_sync_gen = self.gen_sync.sync_gen + 1
        cache.set(self.gen_sync.cache_key, new_sync_gen)

        self.gen_sync.refresh()
        self.assertEqual(self.gen_sync.sync_gen, new_sync_gen)

    def test_clear(self):
        """Testing GenerationSynchronizer.clear"""
        self.gen_sync.clear()
        self.assertEqual(cache.get(self.gen_sync.cache_key), None)

    def test_mark_updated(self):
        """Testing GenerationSynchronizer.mark_updated"""
        sync_gen = self.gen_sync.sync_gen

        self.gen_sync.mark_updated()
        self.assertEqual(self.gen_sync.sync_gen, sync_gen + 1)
        self.assertEqual(cache.get(self.gen_sync.cache_key),
                         self.gen_sync.sync_gen)
