"""Unit tests for djblets.extensions.extension.Extension."""

from __future__ import unicode_literals

from django.core.exceptions import ImproperlyConfigured
from django.utils import six
from kgb import SpyAgency

from djblets.extensions.extension import Extension
from djblets.extensions.hooks import ExtensionHook, ExtensionHookPoint
from djblets.extensions.settings import ExtensionSettings
from djblets.extensions.tests.base import ExtensionTestsMixin
from djblets.testing.testcases import TestCase


@six.add_metaclass(ExtensionHookPoint)
class DummyHook(ExtensionHook):
    def initialize(self):
        self.foo = [1]

    def shutdown(self):
        self.foo.pop()


class ExtensionTest(SpyAgency, ExtensionTestsMixin, TestCase):
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
            __module__ = 'djblets.extensions.tests.apps.test'

        extension = self.setup_extension(TestExtension, enable=False)

        try:
            extension.admin_urlconf
        except ImproperlyConfigured:
            self.fail('Should have loaded admin_urls.py')
