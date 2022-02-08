"""Unit tests for djblets.extensions.extension.Extension."""

from django.core.exceptions import ImproperlyConfigured
from kgb import SpyAgency

from djblets.extensions.extension import Extension
from djblets.extensions.hooks import ExtensionHook, ExtensionHookPoint
from djblets.extensions.settings import ExtensionSettings
from djblets.extensions.testing import ExtensionTestCaseMixin
from djblets.testing.testcases import TestCase


class DummyHook(ExtensionHook, metaclass=ExtensionHookPoint):
    def initialize(self):
        self.foo = [1]

    def shutdown(self):
        self.foo.pop()


class ExtensionTest(SpyAgency, ExtensionTestCaseMixin, TestCase):
    """Unit tests for djblets.extensions.extension.Extension."""

    def test_extension_constructor(self):
        """Testing Extension construction"""
        class TestExtension(Extension):
            pass

        extension = self.setup_extension(TestExtension)

        self.assertEqual(type(extension.settings), ExtensionSettings)
        self.assertEqual(extension, extension.settings.extension)

    def test_shutdown(self):
        """Testing Extension.shutdown"""
        class TestExtension(Extension):
            def initialize(self):
                for index in range(0, 5):
                    DummyHook(self)

        extension = self.setup_extension(TestExtension)

        for hook in extension.hooks:
            self.spy_on(hook.shutdown)

        extension.shutdown()

        for hook in extension.hooks:
            self.assertTrue(hook.shutdown.called)

    def test_shutdown_twice(self):
        """Testing Extension.shutdown when called twice"""
        class TestExtension(Extension):
            def initialize(self):
                for index in range(0, 5):
                    DummyHook(self)

        extension = self.setup_extension(TestExtension)

        for hook in extension.hooks:
            self.spy_on(hook.shutdown)

        extension.shutdown()

        for hook in extension.hooks:
            self.assertTrue(hook.shutdown.called)
            hook.shutdown.reset_calls()

        extension.shutdown()

        for hook in extension.hooks:
            self.assertFalse(hook.shutdown.called)

    def test_admin_urlconf(self):
        """Testing Extension with admin URLConfs"""
        class TestExtension(Extension):
            __module__ = 'djblets.extensions.tests.apps.model_tests'

        extension = self.setup_extension(TestExtension)

        try:
            extension.admin_urlconf
        except ImproperlyConfigured:
            self.fail('Should have loaded admin_urls.py')
