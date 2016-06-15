from __future__ import unicode_literals

from djblets.features import Feature, FeatureLevel, get_features_registry
from djblets.features.testing import (override_feature_check,
                                      override_feature_checks)
from djblets.testing.testcases import TestCase


class StableFeature(Feature):
    feature_id = 'djblets.tests.stable-feature'
    level = FeatureLevel.STABLE


class ExperimentalFeature(Feature):
    feature_id = 'djblets.tests.experimental-feature'
    level = FeatureLevel.EXPERIMENTAL


class FeatureTestingTests(TestCase):
    """Unit tests for djblets.features.testing."""

    def tearDown(self):
        super(FeatureTestingTests, self).tearDown()

        get_features_registry().reset()

    def test_override_feature_check(self):
        """Testing override_feature_check"""
        stable_feature = StableFeature()
        experimental_feature = ExperimentalFeature()

        self.assertTrue(stable_feature.is_enabled())
        self.assertFalse(experimental_feature.is_enabled())

        with override_feature_check(stable_feature.feature_id, enabled=False):
            self.assertFalse(stable_feature.is_enabled())
            self.assertFalse(experimental_feature.is_enabled())

        with override_feature_check(experimental_feature.feature_id,
                                    enabled=True):
            self.assertTrue(stable_feature.is_enabled())
            self.assertTrue(experimental_feature.is_enabled())

        # Make sure they haven't been permanently overridden.
        self.assertTrue(stable_feature.is_enabled())
        self.assertFalse(experimental_feature.is_enabled())

    def test_override_feature_checks(self):
        """Testing override_feature_checks"""
        stable_feature = StableFeature()
        experimental_feature = ExperimentalFeature()

        self.assertTrue(stable_feature.is_enabled())
        self.assertFalse(experimental_feature.is_enabled())

        feature_states = {
            stable_feature.feature_id: False,
            experimental_feature.feature_id: True,
        }

        with override_feature_checks(feature_states):
            self.assertFalse(stable_feature.is_enabled())
            self.assertTrue(experimental_feature.is_enabled())

        # Make sure they haven't been permanently overridden.
        self.assertTrue(stable_feature.is_enabled())
        self.assertFalse(experimental_feature.is_enabled())
