"""Testing feature-related decorators."""

from __future__ import unicode_literals

from django.http import (HttpResponse, HttpResponseForbidden,
                         HttpResponseNotFound)
from kgb import SpyAgency

from djblets.features.decorators import feature_required
from djblets.features.testing import override_feature_check
from djblets.features.tests.test_feature import DummyFeature
from djblets.features import get_features_registry
from djblets.features.checkers import set_feature_checker
from djblets.testing.testcases import TestCase


class FeatureRequiredTests(SpyAgency, TestCase):
    """Tests for the @feature_required decorator."""

    @classmethod
    def setUpClass(cls):
        super(FeatureRequiredTests, cls).setUpClass()

        cls.features = get_features_registry()

    def tearDown(self):
        super(FeatureRequiredTests, self).tearDown()

        self.features.reset()
        set_feature_checker(None)

    def test_feature_required_disabled(self):
        """Testing @feature_required() with a disabled feature"""
        feature = DummyFeature()
        self.assertFalse(feature.is_enabled())

        @feature_required(feature)
        def view(request):
            assert False, "view() should not be called."

        result = view(None)
        self.assertIsInstance(result, HttpResponseNotFound)

    def test_feature_require_enabled(self):
        """Testing @feature_required with an enabled feature"""
        feature = DummyFeature()
        self.assertFalse(feature.is_enabled())

        def view(request):
            return HttpResponse(content=b'foo')

        decorated = feature_required(feature)(view)

        self.spy_on(view)

        with override_feature_check(feature.feature_id, enabled=True):
            self.assertTrue(feature.is_enabled())

            result = decorated(None)
            self.assertIsInstance(result, HttpResponse)
            self.assertEqual(result.content, b'foo')
            self.assertTrue(view.spy.called)

    def test_feature_required_disabled_backup_view(self):
        """Testing @feature_required with a disabled view calls the correct
        backup view
        """
        feature = DummyFeature()
        self.assertFalse(feature.is_enabled())

        def _403(*args, **kwargs):
            return HttpResponseForbidden()

        @feature_required(feature, _403)
        def view(request):
            assert False, "view() should not be called."

        result = view(None)
        self.assertIsInstance(result, HttpResponseForbidden)
