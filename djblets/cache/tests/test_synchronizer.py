from __future__ import unicode_literals

from django.core.cache import cache

from djblets.cache.synchronizer import GenerationSynchronizer
from djblets.testing.testcases import TestCase


class GenerationSynchronizerTests(TestCase):
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
