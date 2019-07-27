"""Unit tests for djblets.extensions.hooks.ExtensionHookPoint."""

from __future__ import unicode_literals

from django.utils import six
from mock import Mock

from djblets.extensions.extension import Extension
from djblets.extensions.hooks import ExtensionHook, ExtensionHookPoint
from djblets.extensions.tests.base import ExtensionTestsMixin
from djblets.testing.testcases import TestCase


@six.add_metaclass(ExtensionHookPoint)
class TestExtensionHook(ExtensionHook):
    pass


class TestExtension(Extension):
    pass


class ExtensionHookPointTest(ExtensionTestsMixin, TestCase):
    """Unit tests for djblets.extensions.hooks.ExtensionHookPoint."""

    def setUp(self):
        super(ExtensionHookPointTest, self).setUp()

        self.extension = self.setup_extension(TestExtension)
        self.extension_hook_class = TestExtensionHook
        self.dummy_hook = Mock()
        self.extension_hook_class.add_hook(self.dummy_hook)

    def test_extension_hook_class_gets_hooks(self):
        """Testing ExtensionHookPoint.hooks"""
        self.assertTrue(hasattr(self.extension_hook_class, "hooks"))

    def test_add_hook(self):
        """Testing ExtensionHookPoint.add_hook"""
        self.assertTrue(self.dummy_hook in self.extension_hook_class.hooks)

    def test_remove_hook(self):
        """Testing ExtensionHookPoint.remove_hook"""
        self.extension_hook_class.remove_hook(self.dummy_hook)
        self.assertTrue(self.dummy_hook not in self.extension_hook_class.hooks)
