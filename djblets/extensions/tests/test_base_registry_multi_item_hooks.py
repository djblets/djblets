"""Unit tests for djblets.extensions.hooks.BaseRegistryMultiItemsHook."""

from djblets.extensions.extension import Extension
from djblets.extensions.hooks import (ExtensionHookPoint,
                                      BaseRegistryMultiItemHook)
from djblets.extensions.testing import ExtensionTestCaseMixin
from djblets.registries.errors import AlreadyRegisteredError
from djblets.registries.registry import Registry
from djblets.testing.testcases import TestCase


class DummyRegistry(Registry):
    lookup_attrs = ('foo_id',)


class DummyItem(object):
    def __init__(self, foo_id):
        self.foo_id = foo_id


class MyTestExtension(Extension):
    pass


class BaseRegistryMultiItemHookTests(ExtensionTestCaseMixin, TestCase):
    """Unit tests for djblets.extensions.hooks.BaseRegistryMultiItemsHook."""

    extension_class = MyTestExtension

    def setUp(self):
        super(BaseRegistryMultiItemHookTests, self).setUp()

        self.registry = DummyRegistry()

        class DummyRegistryHook(BaseRegistryMultiItemHook,
                                metaclass=ExtensionHookPoint):
            registry = self.registry

        self.hook_cls = DummyRegistryHook

    def test_initialize(self):
        """Testing BaseRegistryMultiItemHook.initialize"""
        self.assertEqual(list(self.registry), [])

        item1 = DummyItem(123)
        item2 = DummyItem(456)
        self.hook_cls(self.extension, [item1, item2])

        self.assertIn(item1, self.registry)
        self.assertIn(item2, self.registry)

    def test_initialize_handles_errors(self):
        """Testing BaseRegistryMultiItemHook.initialize unregisters all items
        on registration error
        """
        self.assertEqual(list(self.registry), [])

        item1 = DummyItem(123)
        item2 = DummyItem(123)

        with self.assertRaises(AlreadyRegisteredError):
            self.hook_cls(self.extension, [item1, item2])

        self.assertEqual(list(self.registry), [])

    def test_shutdown(self):
        """Testing BaseRegistryMultiItemHook.shutdown"""
        self.assertEqual(list(self.registry), [])

        item1 = DummyItem(123)
        item2 = DummyItem(456)
        self.hook_cls(self.extension, [item1, item2])

        self.extension.shutdown()
        self.assertEqual(list(self.registry), [])
