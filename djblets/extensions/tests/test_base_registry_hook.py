"""Unit tests for djblets.extensions.hooks.BaseRegistryHook."""

from django.utils import six

from djblets.extensions.extension import Extension
from djblets.extensions.hooks import ExtensionHookPoint, BaseRegistryHook
from djblets.extensions.tests.base import ExtensionTestsMixin
from djblets.registries.registry import Registry
from djblets.testing.testcases import TestCase


class BaseRegistryHookTests(ExtensionTestsMixin, TestCase):
    """Unit tests for djblets.extensions.hooks.BaseRegistryHook."""

    class DummyRegistry(Registry):
        lookup_attrs = ('foo_id',)

    class DummyItem(object):
        def __init__(self, foo_id):
            self.foo_id = foo_id

    def setUp(self):
        super(BaseRegistryHookTests, self).setUp()

        self.registry = self.DummyRegistry()

        @six.add_metaclass(ExtensionHookPoint)
        class DummyRegistryHook(BaseRegistryHook):
            registry = self.registry

        class TestExtension(Extension):
            pass

        self.hook_cls = DummyRegistryHook

        self.extension = self.setup_extension(TestExtension)

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
