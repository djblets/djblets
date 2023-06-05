from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ImproperlyConfigured

from djblets.features.checkers import (BaseFeatureChecker,
                                       SettingsFeatureChecker,
                                       SiteConfigFeatureChecker,
                                       get_feature_checker,
                                       set_feature_checker)
from djblets.features.level import FeatureLevel
from djblets.siteconfig.models import SiteConfiguration
from djblets.testing.testcases import TestCase


class BadFeatureChecker(BaseFeatureChecker):
    def __init__(self) -> None:
        raise Exception('oh no what even happened')


class FeatureCheckerTests(TestCase):
    """Unit tests for djblets.features.checkers."""

    def tearDown(self) -> None:
        super().tearDown()

        set_feature_checker(None)

        delattr(settings, 'FEATURE_CHECKER')

    def test_get_feature_checker(self) -> None:
        """Testing get_feature_checker"""
        set_feature_checker(None)

        settings.FEATURE_CHECKER = \
            'djblets.features.checkers.SiteConfigFeatureChecker'

        self.assertEqual(get_feature_checker().__class__,
                         SiteConfigFeatureChecker)

    def test_get_feature_checker_with_invalid_path(self) -> None:
        """Testing get_feature_checker with invalid feature checker path"""
        set_feature_checker(None)

        settings.FEATURE_CHECKER = \
            'djblets.features.checkers.SomethingNotHere'

        with self.assertRaises(ImproperlyConfigured):
            get_feature_checker()

    def test_get_feature_checker_with_init_error(self) -> None:
        """Testing get_feature_checker with initialization error"""
        set_feature_checker(None)

        settings.FEATURE_CHECKER = \
            'djblets.features.tests.test_checkers.BadFeatureChecker'

        with self.assertRaises(ImproperlyConfigured):
            get_feature_checker()


class BaseFeatureCheckerTests(TestCase):
    """Unit tests for djblets.features.checkers.BaseFeatureChecker."""

    def setUp(self) -> None:
        super().setUp()

        self.checker = BaseFeatureChecker()
        self._old_debug = settings.DEBUG

    def tearDown(self) -> None:
        super().tearDown()

        self.checker = BaseFeatureChecker()
        settings.DEBUG = self._old_debug

        try:
            delattr(settings, 'MIN_ENABLED_FEATURE_LEVEL')
        except AttributeError:
            pass

    def test_min_enabled_level_with_debug_true(self) -> None:
        """Testing BaseFeatureChecker.min_enabled_level with DEBUG=True"""
        settings.DEBUG = True
        self.assertEqual(self.checker.min_enabled_level, FeatureLevel.BETA)

    def test_min_enabled_level_with_debug_false(self) -> None:
        """Testing BaseFeatureChecker.min_enabled_level with DEBUG=False"""
        settings.DEBUG = False
        self.assertEqual(self.checker.min_enabled_level, FeatureLevel.STABLE)

    def test_min_enabled_level_with_setting(self) -> None:
        """Testing BaseFeatureChecker.min_enabled_level with
        MIN_ENABLED_FEATURE_LEVEL setting
        """
        settings.MIN_ENABLED_FEATURE_LEVEL = 42
        self.assertEqual(self.checker.min_enabled_level, 42)


class SettingsFeatureCheckerTests(TestCase):
    """Unit tests for djblets.features.checkers.SettingsFeatureChecker."""

    def setUp(self) -> None:
        super().setUp()

        self.checker = SettingsFeatureChecker()

    def tearDown(self) -> None:
        super().tearDown()

        try:
            delattr(settings, 'ENABLED_FEATURES')
        except AttributeError:
            pass

    def test_is_feature_enabled_with_enabled(self) -> None:
        """Testing SettingsFeatureChecker.is_feature_enabled with feature
        enabled
        """
        settings.ENABLED_FEATURES = {
            'my-feature': True,
        }

        self.assertTrue(self.checker.is_feature_enabled('my-feature'))

    def test_is_feature_enabled_with_disabled(self) -> None:
        """Testing SettingsFeatureChecker.is_feature_enabled with feature
        disabled
        """
        settings.ENABLED_FEATURES = {
            'my-feature': False,
        }

        self.assertFalse(self.checker.is_feature_enabled('my-feature'))

    def test_is_feature_enabled_with_unset(self) -> None:
        """Testing SettingsFeatureChecker.is_feature_enabled with feature state
        not set
        """
        self.assertFalse(self.checker.is_feature_enabled('my-feature'))


class SiteConfigFeatureCheckerTests(TestCase):
    """Unit tests for djblets.features.checkers.SiteConfigFeatureChecker."""

    def setUp(self) -> None:
        super().setUp()

        self.checker = SiteConfigFeatureChecker()
        self.siteconfig = SiteConfiguration.objects.create(
            site=Site.objects.get_current())

    def tearDown(self) -> None:
        super().tearDown()

        try:
            delattr(settings, 'ENABLED_FEATURES')
        except AttributeError:
            pass

    def test_is_feature_enabled_with_siteconfig_enabled(self) -> None:
        """Testing SiteConfigFeatureChecker.is_feature_enabled with feature
        enabled in SiteConfiguration
        """
        self.siteconfig.set('enabled_features', {
            'my-feature': True,
        })
        self.siteconfig.save()

        settings.ENABLED_FEATURES = {
            'my-feature': False,
        }

        self.assertTrue(self.checker.is_feature_enabled('my-feature'))

    def test_is_feature_enabled_with_siteconfig_disabled(self) -> None:
        """Testing SiteConfigFeatureChecker.is_feature_enabled with feature
        disabled in SiteConfiguration
        """
        self.siteconfig.set('enabled_features', {
            'my-feature': False,
        })
        self.siteconfig.save()

        settings.ENABLED_FEATURES = {
            'my-feature': True,
        }

        self.assertFalse(self.checker.is_feature_enabled('my-feature'))

    def test_is_feature_enabled_with_settings_enabled(self) -> None:
        """Testing SiteConfigFeatureChecker.is_feature_enabled with feature
        enabled in Settings
        """
        settings.ENABLED_FEATURES = {
            'my-feature': True,
        }

        self.assertTrue(self.checker.is_feature_enabled('my-feature'))

    def test_is_feature_enabled_with_settings_disabled(self) -> None:
        """Testing SiteConfigFeatureChecker.is_feature_enabled with feature
        disabled in Settings
        """
        settings.ENABLED_FEATURES = {
            'my-feature': False,
        }

        self.assertFalse(self.checker.is_feature_enabled('my-feature'))

    def test_is_feature_enabled_with_unset(self) -> None:
        """Testing SiteConfigFeatureChecker.is_feature_enabled with feature
        state not set
        """
        self.assertFalse(self.checker.is_feature_enabled('my-feature'))
