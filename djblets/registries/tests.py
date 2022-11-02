from typing import Any, Iterable

from kgb import SpyAgency

from djblets.registries.errors import (AlreadyRegisteredError,
                                       ItemLookupError,
                                       RegistrationError)
from djblets.registries.registry import Registry, OrderedRegistry, UNREGISTER
from djblets.registries.signals import registry_populating
from djblets.testing.testcases import TestCase


class Item:
    """An item used for registry tests."""

    ######################
    # Instance variables #
    ######################

    id: int
    name: str
    fake: bool

    def __init__(
        self,
        **attrs,
    ) -> None:
        """Initialize the item.

        Args:
            **attrs (dict):
                Attribute name and value pairs to set on the item.
        """
        self._attrs = set(attr_name for attr_name in attrs)

        for attr_name, attr_value in attrs.items():
            setattr(self, attr_name, attr_value)

    def __repr__(self) -> str:
        attrs = (
            '%s=%r' % (attr_name, getattr(self, attr_name))
            for attr_name in self._attrs
        )
        return '<Item(%s)>' % ', '.join(attrs)

    def __hash__(self) -> int:
        return id(self)

    def __eq__(
        self,
        other: Any,
    ) -> bool:
        return (type(self) is type(other) and
                self._attrs == other._attrs and
                all(getattr(self, attr_name) == getattr(other, attr_name)
                    for attr_name in self._attrs))


class RegistryTests(SpyAgency, TestCase):
    """Tests for djblets.registries.Registry."""

    def test_empty_by_default(self):
        """Testing Registry instances are created empty"""
        r = Registry()

        self.assertEqual(len(r), 0)
        self.assertEqual(set(r), set())

    def test_get_invalid_attribute(self):
        """Testing Registry.get_item with invalid attributes"""
        r = Registry()

        with self.assertRaises(ItemLookupError):
            r.get('foo', 'bar')

    def test_register_item(self):
        """Testing Registry.register_item"""
        r = Registry()
        items = [1, 2, 3]

        for item in items:
            r.register(item)

        self.assertEqual(set(r), set(items))

    def test_unregister_item(self):
        """Testing Registry.unregister_item"""
        r = Registry()
        items = [1, 2, 3]

        for item in items:
            r.register(item)

        for item in items:
            r.unregister(item)

        self.assertEqual(set(r), set())

    def test_unregister_removes_attr_lookups(self):
        """Testing Registry.unregister removes lookup entries"""
        class TestRegistry(Registry[Item]):
            lookup_attrs = ('id',)

        r = TestRegistry()
        items = [Item(id=0), Item(id=1), Item(id=2)]

        for item in items:
            r.register(item)

        for item in items:
            r.unregister(item)

            with self.assertRaises(ItemLookupError):
                r.get('id', item.id)

        self.assertEqual(len(r), 0)

    def test_population_on_register(self):
        """Testing Registry.register_item triggers population before
        registration
        """
        original_item = Item(id=0)
        duplicate_item = Item(id=0, fake=True)

        class TestRegistry(Registry[Item]):
            lookup_attrs = ('id',)

            def get_defaults(self):
                yield original_item

        self.spy_on(registry_populating.send)

        r = TestRegistry()

        with self.assertRaises(AlreadyRegisteredError):
            r.register(duplicate_item)

        self.assertIs(r.get('id', original_item.id),
                      original_item)
        self.assertSpyCalledWith(
            registry_populating.send,
            sender=TestRegistry,
            registry=r)

    def test_population_on_unregister(self):
        """Testing Registry.unregister_item triggers population before
        unregistration.
        """
        item = Item(id=0)

        class TestRegistry(Registry[Item]):
            lookup_attrs = ('id',)

            def get_defaults(self):
                yield item

        self.spy_on(registry_populating.send)

        r = TestRegistry()
        r.unregister(item)
        self.assertEqual(len(r), 0)

        self.assertSpyCalledWith(
            registry_populating.send,
            sender=TestRegistry,
            registry=r)

    def test_registering_duplicate(self):
        """Testing Registry.register_item with duplicate items"""
        r = Registry()
        r.register(1)

        with self.assertRaises(AlreadyRegisteredError):
            r.register(1)

    def test_registering_duplicate_attributes(self):
        """Testing Registry.register_item with items that have identical
        attributes
        """
        class TestRegistry(Registry[Item]):
            lookup_attrs = ('id',)

        r = TestRegistry()
        r.register(Item(id=0, name='foo'))

        with self.assertRaises(AlreadyRegisteredError):
            r.register(Item(id=0, name='bar'))

    def test_register_missing_attributes(self):
        """Testing Registry.register_item with items that have missing
        attributes
        """
        class TestRegistry(Registry[Item]):
            lookup_attrs = ('id',)

        r = TestRegistry()

        with self.assertRaises(RegistrationError):
            r.register(Item())

    def test_contains(self):
        """Testing Registry.__contains__"""
        r = Registry()
        r.register(1)

        self.assertIn(1, r)
        self.assertNotIn(2, r)

    def test_error_override(self):
        """Testing Registry error formatting strings"""
        class TestRegistry(Registry[int]):
            errors = {
                UNREGISTER: 'The foo "%(item)s" is unregistered.'
            }

        r = TestRegistry()

        with self.assertRaisesMessage(ItemLookupError,
                                      'The foo "1" is unregistered.'):
            r.unregister(1)


class OrderedRegistryTests(TestCase):
    """Tests for djblets.registries.registry.OrderedRegistry."""

    class TestRegistry(OrderedRegistry[int]):
        def get_defaults(self) -> Iterable[int]:
            return [1, 2, 3]

    def setUp(self):
        self.registry = OrderedRegistryTests.TestRegistry()

    def test_iteration_order(self):
        """Testing OrderedRegistry iteration order"""
        self.registry.register(4)
        self.assertListEqual(list(self.registry),
                             [1, 2, 3, 4])

    def test_getitem(self):
        """Testing OrderedRegistry.__getitem__"""
        self.assertEqual(self.registry[0], 1)
        self.assertEqual(self.registry[1], 2)
        self.assertEqual(self.registry[2], 3)

    def test_getitem_negative_indices(self):
        """Testing OrderedRegistry.__getitem__ with negative indices"""
        self.assertEqual(self.registry[-1], 3)
        self.assertEqual(self.registry[-2], 2)
        self.assertEqual(self.registry[-3], 1)

    def test_getitem_invalid_index(self):
        """Testing OrderedRegistry.__getitem__ with an invalid index"""
        with self.assertRaises(TypeError):
            self.registry['foo']  # type: ignore

    def test_getitem_out_of_range(self):
        """Testing OrderedRegistry.__getitem__ with an out of range index"""
        with self.assertRaises(IndexError):
            self.registry[1000]
