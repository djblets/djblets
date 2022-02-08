"""Unit tests for djblets.extensions.hooks.BaseRegistryHook."""

from djblets.extensions.extension import Extension
from djblets.extensions.hooks import ExtensionHookPoint, BaseRegistryHook
from djblets.extensions.testing import ExtensionTestCaseMixin
from djblets.registries.registry import Registry
from djblets.testing.testcases import TestCase


class MyTestExtension(Extension):
    pass


class BaseRegistryHookTests(ExtensionTestCaseMixin, TestCase):
    """Unit tests for djblets.extensions.hooks.BaseRegistryHook."""

    extension_class = MyTestExtension

    class DummyRegistry(Registry):
        lookup_attrs = ('foo_id',)

    class DummyItem(object):
        def __init__(self, foo_id):
            self.foo_id = foo_id

    def setUp(self):
        super(BaseRegistryHookTests, self).setUp()

        self.registry = self.DummyRegistry()

        class DummyRegistryHook(BaseRegistryHook,
                                metaclass=ExtensionHookPoint):
            registry = self.registry

        self.hook_cls = DummyRegistryHook

    def test_hook_register(self):
        """Testing BaseRegistryHook item registration"""
        self.assertEqual(list(self.registry), [])

        item = self.DummyItem(123)
        self.hook_cls(self.extension, item)

        self.assertIn(item, self.registry)

    def test_hook_unregister(self):
        """Testing BaseRegistryHook item unregistration"""
        self.assertEqual(list(self.registry), [])
        item = self.DummyItem(123)
        self.hook_cls(self.extension, item)

        self.extension.shutdown()
        self.assertEqual(list(self.registry), [])
