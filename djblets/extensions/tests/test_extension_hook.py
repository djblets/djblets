"""Unit tests for djblets.extensions.hooks.ExtensionHook."""

from __future__ import unicode_literals

from django.utils import six

from djblets.extensions.extension import Extension
from djblets.extensions.hooks import ExtensionHook, ExtensionHookPoint
from djblets.extensions.tests.base import ExtensionTestsMixin
from djblets.testing.testcases import TestCase


@six.add_metaclass(ExtensionHookPoint)
class TestExtensionHook(ExtensionHook):
    pass


class TestExtension(Extension):
    pass


class ExtensionHookTest(ExtensionTestsMixin, TestCase):
    """Unit tests for djblets.extensions.hooks.ExtensionHook."""

    def setUp(self):
        super(ExtensionHookTest, self).setUp()

        self.extension = self.setup_extension(TestExtension)

    def test_init_hook_states(self):
        """Testing ExtensionHook enabling hook states"""
        @six.add_metaclass(ExtensionHookPoint)
        class InitTestHook(ExtensionHook):
            def initialize(hook):
                self.assertFalse(hook.initialized)
                self.assertEqual(hook.hook_state,
                                 ExtensionHook.HOOK_STATE_ENABLING)

        hook = InitTestHook(self.extension)
        self.assertEqual(hook.hook_state, ExtensionHook.HOOK_STATE_ENABLED)
        self.assertTrue(hook.initialized)

    def test_disable_hook_states(self):
        """Testing ExtensionHook disabling states"""
        @six.add_metaclass(ExtensionHookPoint)
        class InitTestHook(ExtensionHook):
            def shutdown(hook):
                self.assertFalse(hook.initialized)
                self.assertEqual(hook.hook_state,
                                 ExtensionHook.HOOK_STATE_DISABLING)

        hook = InitTestHook(self.extension)
        hook.disable_hook()
        self.assertEqual(hook.hook_state, ExtensionHook.HOOK_STATE_DISABLED)
        self.assertFalse(hook.initialized)

    def test_init_with_start_enabled_false(self):
        """Testing ExtensionHook construction with start_enabled=False"""
        @six.add_metaclass(ExtensionHookPoint)
        class InitTestHook(ExtensionHook):
            def initialize(hook):
                self.fail('initialize() should not have been reached')

        hook = InitTestHook(self.extension, start_enabled=False)
        self.assertEqual(hook.hook_state, ExtensionHook.HOOK_STATE_DISABLED)
        self.assertFalse(hook.initialized)

    def test_registration(self):
        """Testing ExtensionHook registration"""
        extension_hook = TestExtensionHook(self.extension)

        self.assertEqual(self.extension, extension_hook.extension)
        self.assertIn(extension_hook, self.extension.hooks)
        self.assertIn(extension_hook, extension_hook.__class__.hooks)

    def test_shutdown(self):
        """Testing ExtensionHook.shutdown"""
        extension_hook = TestExtensionHook(self.extension)
        extension_hook.disable_hook()

        self.assertNotIn(extension_hook, extension_hook.__class__.hooks)
