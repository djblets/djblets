"""Unit tests for djblets.features.testing."""

from __future__ import annotations

from typing import ClassVar, TYPE_CHECKING

from djblets.features import Feature, FeatureLevel, get_features_registry
from djblets.features.testing import (override_feature_check,
                                      override_feature_checks)
from djblets.testing.testcases import TestCase

if TYPE_CHECKING:
    from djblets.features.testing import FeatureStates


class _StableFeature(Feature):
    feature_id: ClassVar[str] = 'djblets.tests.stable-feature'
    level = FeatureLevel.STABLE


class _ExperimentalFeature(Feature):
    feature_id: ClassVar[str] = 'djblets.tests.experimental-feature'
    level = FeatureLevel.EXPERIMENTAL


class FeatureTestingTests(TestCase):
    """Unit tests for djblets.features.testing."""

    def tearDown(self) -> None:
        """Tear down the test case."""
        super().tearDown()

        get_features_registry().reset()

    def test_override_feature_check(self) -> None:
        """Testing override_feature_check"""
        stable_feature = _StableFeature()
        experimental_feature = _ExperimentalFeature()

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

    def test_override_feature_checks(self) -> None:
        """Testing override_feature_checks"""
        stable_feature = _StableFeature()
        experimental_feature = _ExperimentalFeature()

        self.assertTrue(stable_feature.is_enabled())
        self.assertFalse(experimental_feature.is_enabled())

        feature_states: FeatureStates = {
            stable_feature.feature_id: False,
            experimental_feature.feature_id: True,
        }

        with override_feature_checks(feature_states):
            self.assertFalse(stable_feature.is_enabled())
            self.assertTrue(experimental_feature.is_enabled())

        # Make sure they haven't been permanently overridden.
        self.assertTrue(stable_feature.is_enabled())
        self.assertFalse(experimental_feature.is_enabled())

    def test_override_feature_checks_as_decorator(self) -> None:
        """Testing override_feature_checks as decorator"""
        stable_feature = _StableFeature()
        experimental_feature = _ExperimentalFeature()

        @override_feature_checks({
            stable_feature.feature_id: False,
            experimental_feature.feature_id: True,
        })
        def _do_test() -> None:
            self.assertFalse(stable_feature.is_enabled())
            self.assertTrue(experimental_feature.is_enabled())

        _do_test()

        # Make sure they haven't been permanently overridden.
        self.assertTrue(stable_feature.is_enabled())
        self.assertFalse(experimental_feature.is_enabled())

    def test_override_feature_check_as_decorator(self) -> None:
        """Testing override_feature_check as decorator"""
        stable_feature = _StableFeature()
        experimental_feature = _ExperimentalFeature()

        @override_feature_check(stable_feature.feature_id, False)
        def _do_test_1() -> None:
            self.assertFalse(stable_feature.is_enabled())

        @override_feature_check(experimental_feature.feature_id, True)
        def _do_test_2() -> None:
            self.assertTrue(experimental_feature.is_enabled())

        _do_test_1()
        _do_test_2()

        # Make sure they haven't been permanently overridden.
        self.assertTrue(stable_feature.is_enabled())
        self.assertFalse(experimental_feature.is_enabled())
