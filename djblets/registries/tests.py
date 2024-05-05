"""Unit tests for djblets.registries."""

from __future__ import annotations

import time
from threading import Lock, Thread
from typing import Any, Callable, Iterable

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


class ThreadRegistry(Registry[Item]):
    """A registry used for thread tests.

    Version Added:
        5.0
    """

    lookup_attrs = ('id',)

    ######################
    # Instance variables #
    ######################

    count: int
    sleep_lock: Lock

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the registry.

        Args:
            *args (tuple):
                Positional arguments to pass to the parent.

            **kwargs (tuple):
                Keyword arguments to pass to the parent.
        """
        super().__init__(*args, **kwargs)

        self.count = 0
        self.sleep_lock = Lock()

    def sleep_first_thread(self) -> None:
        """Sleep the first time a thread calls this method."""
        with self.sleep_lock:
            do_sleep = (self.count == 0)
            self.count += 1

        if do_sleep:
            time.sleep(0.1)


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

    def test_register_item(self) -> None:
        """Testing Registry.register_item"""
        r = Registry()

        self.spy_on(r.on_item_registering)
        self.spy_on(r.on_item_registered)

        items = [1, 2, 3]

        for item in items:
            r.register(item)

        self.assertEqual(set(r), set(items))

        self.assertSpyCallCount(r.on_item_registering, 3)
        self.assertSpyCalledWith(r.on_item_registering, 1)
        self.assertSpyCalledWith(r.on_item_registering, 2)
        self.assertSpyCalledWith(r.on_item_registering, 3)

        self.assertSpyCallCount(r.on_item_registered, 3)
        self.assertSpyCalledWith(r.on_item_registered, 1)
        self.assertSpyCalledWith(r.on_item_registered, 2)
        self.assertSpyCalledWith(r.on_item_registered, 3)

    def test_register_item_with_thread_conflict(self) -> None:
        """Testing Registry.register_item with same item in different threads
        """
        def _thread_main(
            secs: float,
            item: Item,
            expect_fail: bool,
        ) -> None:
            time.sleep(secs)

            if expect_fail:
                with self.assertRaises(AlreadyRegisteredError):
                    registry.register(item)
            else:
                registry.register(item)

        class TestRegistry(ThreadRegistry):
            def on_item_registering(
                self,
                item: Item,
            ) -> None:
                self.sleep_first_thread()

        registry = TestRegistry()
        registry.populate()
        self.spy_on(registry.on_item_registering)
        self.spy_on(registry.on_item_registered)

        self.assertEqual(len(registry), 0)

        item1 = Item(id=0)
        item2 = Item(id=0)

        self._run_threads(
            target=_thread_main,
            threads_args=[
                [0.1, item1, True],
                [0.05, item2, False],
            ])

        self.assertIs(registry.get('id', 0), item2)

        self.assertSpyCallCount(registry.on_item_registering, 2)
        self.assertSpyCallCount(registry.on_item_registered, 1)

    def test_unregister_item(self):
        """Testing Registry.unregister_item"""
        r = Registry()
        items = [1, 2, 3]

        self.spy_on(r.on_item_unregistering)
        self.spy_on(r.on_item_unregistered)

        for item in items:
            r.register(item)

        for item in items:
            r.unregister(item)

        self.assertEqual(set(r), set())

        self.assertSpyCallCount(r.on_item_unregistering, 3)
        self.assertSpyCalledWith(r.on_item_unregistering, 1)
        self.assertSpyCalledWith(r.on_item_unregistering, 2)
        self.assertSpyCalledWith(r.on_item_unregistering, 3)

        self.assertSpyCallCount(r.on_item_unregistered, 3)
        self.assertSpyCalledWith(r.on_item_unregistered, 1)
        self.assertSpyCalledWith(r.on_item_unregistered, 2)
        self.assertSpyCalledWith(r.on_item_unregistered, 3)

    def test_unregister_item_with_thread_conflict(self) -> None:
        """Testing Registry.unregister_item with same item in different
        threads
        """
        def _thread_main(
            secs: float,
            expect_fail: bool,
        ) -> None:
            time.sleep(secs)

            if expect_fail:
                with self.assertRaises(ItemLookupError):
                    registry.unregister(item1)
            else:
                registry.unregister(item1)

        class TestRegistry(ThreadRegistry):
            def on_item_unregistering(
                self,
                item: Item,
            ) -> None:
                self.sleep_first_thread()

        registry = TestRegistry()
        self.spy_on(registry.on_item_unregistering)
        self.spy_on(registry.on_item_unregistered)

        item1 = Item(id=0)
        registry.register(item1)

        self.assertEqual(len(registry), 1)

        self._run_threads(
            target=_thread_main,
            threads_args=[
                [0.1, True],
                [0.05, False],
            ])

        self.assertEqual(len(registry), 0)
        self.assertSpyCallCount(registry.on_item_unregistering, 2)
        self.assertSpyCallCount(registry.on_item_unregistered, 1)

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

    def test_populate(self) -> None:
        """Testing Registry.populate"""
        item1 = Item(id=0)
        item2 = Item(id=1)

        class TestRegistry(Registry[Item]):
            lookup_attrs = ('id',)

            def get_defaults(self):
                yield item1
                yield item2

        self.spy_on(registry_populating.send)

        r = TestRegistry()
        self.spy_on(r.on_populated)
        self.spy_on(r.on_populating)

        r.populate()

        self.assertEqual(r._registry, {
            'id': {
                0: item1,
                1: item2,
            },
        })

        self.assertSpyCalled(r.on_populated)
        self.assertSpyCalled(r.on_populating)

        self.assertIs(r.get('id', item1.id), item1)
        self.assertIs(r.get('id', item2.id), item2)

        self.assertSpyCalledWith(
            registry_populating.send,
            sender=TestRegistry,
            registry=r)

    def test_populate_with_thread_conflict(self) -> None:
        """Testing Registry.populate with multiple threads"""
        def _thread_main(
            secs: float,
        ) -> None:
            time.sleep(secs)
            registry.populate()

            self.assertEqual(list(registry._items), [item1, item2])

        class TestRegistry(ThreadRegistry):
            def get_defaults(self):
                yield item1
                yield item2

            def on_populating(self) -> None:
                self.sleep_first_thread()

        registry = TestRegistry()
        self.spy_on(registry.on_populating)
        self.spy_on(registry.on_populated)

        item1 = Item(id=0)
        item2 = Item(id=1)

        self._run_threads(
            target=_thread_main,
            threads_args=[
                [0.1],
                [0.05],
            ])

        self.assertEqual(list(registry._items), [item1, item2])
        self.assertSpyCallCount(registry.on_populating, 1)
        self.assertSpyCallCount(registry.on_populated, 1)

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

    def test_reset(self) -> None:
        """Testing Registry.reset"""
        item1 = Item(id=0)
        item2 = Item(id=1)

        class TestRegistry(Registry[Item]):
            lookup_attrs = ('id',)

            def get_defaults(self):
                yield item1
                yield item2

        self.spy_on(registry_populating.send)

        r = TestRegistry()
        self.spy_on(r.on_resetting)
        self.spy_on(r.on_reset)

        r.populate()
        r.reset()

        self.assertEqual(r._registry, {
            'id': {},
        })

        self.assertSpyCalled(r.on_resetting)
        self.assertSpyCalled(r.on_reset)

    def test_reset_with_thread_conflict(self) -> None:
        """Testing Registry.reset with multiple threads"""
        def _thread_main(
            secs: float,
        ) -> None:
            self.assertEqual(list(registry._items), [item1, item2])

            time.sleep(secs)
            registry.reset()

            self.assertEqual(list(registry._items), [])

        class TestRegistry(ThreadRegistry):
            def get_defaults(self):
                yield item1
                yield item2

            def on_resetting(self) -> None:
                self.sleep_first_thread()

        item1 = Item(id=0)
        item2 = Item(id=1)

        registry = TestRegistry()
        registry.populate()
        self.spy_on(registry.on_resetting)
        self.spy_on(registry.on_reset)

        self._run_threads(
            target=_thread_main,
            threads_args=[
                [0.1],
                [0.05],
            ])

        self.assertEqual(len(registry._items), 0)
        self.assertSpyCallCount(registry.on_resetting, 1)
        self.assertSpyCallCount(registry.on_reset, 1)

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

    def _run_threads(
        self,
        target: Callable[..., None],
        threads_args: list[list[Any]],
    ) -> None:
        """Run tests with a specified number of threads.

        This will create multiple threads with the same target and different
        arguments, starting them up and then joining them back to the main
        thread.

        Version Added:
            5.0

        Args:
            target (callable):
                The function for each thread to call when started.

            threads_args (list):
                Arguments to provide for each created thread.

                The number of items in this list dictates the number of
                threads.
        """
        threads = [
            Thread(target=target,
                   args=thread_args)
            for thread_args in threads_args
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()


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
