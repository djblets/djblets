"""Unit tests for djblets.extensions.hooks.ExtensionHookPoint."""

from mock import Mock

from djblets.extensions.extension import Extension
from djblets.extensions.hooks import ExtensionHook, ExtensionHookPoint
from djblets.extensions.testing import ExtensionTestCaseMixin
from djblets.testing.testcases import TestCase


class MyTestExtensionHook(ExtensionHook, metaclass=ExtensionHookPoint):
    pass


class MyTestExtension(Extension):
    pass


class ExtensionHookPointTest(ExtensionTestCaseMixin, TestCase):
    """Unit tests for djblets.extensions.hooks.ExtensionHookPoint."""

    extension_class = MyTestExtension

    def setUp(self):
        super(ExtensionHookPointTest, self).setUp()

        self.extension_hook_class = MyTestExtensionHook
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
