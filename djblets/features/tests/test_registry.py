from __future__ import unicode_literals

from djblets.features import Feature
from djblets.features.errors import FeatureConflictError
from djblets.features.registry import FeaturesRegistry
from djblets.registries.errors import RegistrationError
from djblets.testing.testcases import TestCase


class DummyFeature(Feature):
    feature_id = 'djblets.tests.dummy-feature'
    name = 'Dummy Feature'
    summary = 'This is a dummy feature.'

    def initialize(self):
        self._feature_inited = True

    def shutdown(self):
        self._feature_inited = False


class FeaturesRegistryTests(TestCase):
    """Unit tests for djblets.features.registry.FeaturesRegistry."""

    def setUp(self):
        super(FeaturesRegistryTests, self).setUp()

        self.registry = FeaturesRegistry()

    def test_register_with_missing_id(self):
        """Testing FeaturesRegistry.register with missing ID"""
        class InvalidFeature(Feature):
            pass

        with self.assertRaises(RegistrationError):
            self.registry.register(InvalidFeature())

    def test_register_with_conflict(self):
        """Testing FeaturesRegistry.register with conflicting ID"""
        self.registry.register(DummyFeature(register=False))

        with self.assertRaises(FeatureConflictError):
            self.registry.register(DummyFeature(register=False))

    def test_register_calls_initialize(self):
        """Testing FeaturesRegistry.register initializes feature"""
        feature = DummyFeature(register=False)
        self.registry.register(feature)

        self.assertTrue(getattr(feature, '_feature_inited', False))

    def test_unregister_calls_shutdown(self):
        """Testing FeaturesRegistry.register shuts down feature"""
        feature = DummyFeature(register=False)

        self.registry.register(feature)
        self.assertTrue(getattr(feature, '_feature_inited', False))

        self.registry.unregister(feature)
        self.assertFalse(feature._feature_inited)

    def test_get_feature(self):
        """Testing FeaturesRegistry.get_feature"""
        feature = DummyFeature(register=False)

        self.registry.register(feature)
        self.assertEqual(self.registry.get_feature(feature.feature_id),
                         feature)

    def test_get_feature_with_invalid_id(self):
        """Testing FeaturesRegistry.get_feature with invalid ID"""
        self.assertEqual(self.registry.get_feature('bad-id'), None)
