"""Unit tests for djblets.extensions.hooks.URLHook."""

from __future__ import unicode_literals

from django.conf.urls import include, url

from djblets.extensions.extension import Extension
from djblets.extensions.hooks import URLHook
from djblets.extensions.tests.base import ExtensionTestsMixin
from djblets.testing.testcases import TestCase


class TestExtension(Extension):
    def initialize(self):
        self.patterns = [
            url(r'^url_hook_test/',
                include('djblets.extensions.tests.apps.urls')),
        ]
        self.url_hook = URLHook(self, self.patterns)


class URLHookTest(ExtensionTestsMixin, TestCase):
    """Unit tests for djblets.extensions.hooks.URLHook."""

    def setUp(self):
        super(URLHookTest, self).setUp()

        self.extension = self.setup_extension(TestExtension)

    def test_url_registration(self):
        """Testing URLHook URL registration"""
        self.assertTrue(
            set(self.extension.patterns)
            .issubset(set(self.extension.url_hook.dynamic_urls.url_patterns)))

        # And the URLHook should be added to the extension's list of hooks
        self.assertIn(self.extension.url_hook, self.extension.hooks)

    def test_shutdown_removes_urls(self):
        """Testing URLHook.shutdown"""
        # On shutdown, a URLHook's patterns should no longer be in its
        # parent URL resolver's pattern collection.
        self.extension.url_hook.disable_hook()
        self.assertFalse(
            set(self.extension.patterns).issubset(
                set(self.extension.url_hook.dynamic_urls.url_patterns)))

        # But the URLHook should still be in the extension's list of hooks
        self.assertIn(self.extension.url_hook, self.extension.hooks)
