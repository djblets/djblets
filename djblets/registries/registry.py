"""Djblets registries.

Registries are collections that keep track of unique objects.

For information on writing registries, see
:ref:`the guide on writing registries <writing-registries>`.
"""

from __future__ import annotations

import logging
from enum import Enum
from threading import RLock
from typing import (Dict, Generic, Iterable, Iterator, List, Optional,
                    Sequence, Set, Type, TypeVar)

from django.utils.translation import gettext_lazy as _
from importlib_metadata import EntryPoint, entry_points
from typing_extensions import Final, TypeAlias

from djblets.deprecation import RemovedInDjblets70Warning
from djblets.registries.errors import (AlreadyRegisteredError,
                                       ItemLookupError,
                                       RegistrationError)
from djblets.registries.signals import registry_populating
from djblets.util.typing import StrOrPromise

logger = logging.getLogger(__name__)


#: A mapping of error types to error messages.
#:
#: The error messages should be localized.
#:
#: Version Added:
#:     3.3
RegistryErrorsDict: TypeAlias = Dict[str, StrOrPromise]


#: A generic type for items stored in a registry.
#:
#: This can be used for subclasses of :py:class:`Registry`, mixins, or other
#: utility code that need to stay generic. In normal usage, an explicit type
#: will be provided when subclassing instead.
#:
#: Version Added:
#:     3.1
RegistryItemType = TypeVar('RegistryItemType')


#: Error code indicating an item is already registered.
ALREADY_REGISTERED: Final[str] = 'already_registered'

#: Error code indicating a lookup attribute value is already registered.
ATTRIBUTE_REGISTERED: Final[str] = 'attribute_registered'

#: Error code indicating a lookup attribute isn't supported by the registry.
INVALID_ATTRIBUTE: Final[str] = 'invalid_attribute'

#: Error code indicating an item is missing a lookup attribute.
MISSING_ATTRIBUTE: Final[str] = 'missing_attribute'

#: Error code indicating an item is not registered when trying to unregister.
UNREGISTER: Final[str] = 'unregister'

#: Error code indicating an item is not registered when looking it up.
NOT_REGISTERED: Final[str] = 'not_registered'

#: Error indicating an error looking up an item via a Python Entry Point.
LOAD_ENTRY_POINT: Final[str] = 'load_entry_point'


#: Default error messages for registries.
DEFAULT_ERRORS: Final[RegistryErrorsDict] = {
    ALREADY_REGISTERED: _(
        'Could not register %(item)s: it is already registered.'
    ),
    ATTRIBUTE_REGISTERED: _(
        'Could not register %(item)s: another item (%(duplicate)s) is already '
        'registered with %(attr_name)s = %(attr_value)s.'
    ),
    INVALID_ATTRIBUTE: _(
        '"%(attr_name)s" is not a registered lookup attribute.'
    ),
    LOAD_ENTRY_POINT: _(
        'Could not load entry point %(entry_point)s: %(error)s.',
    ),
    MISSING_ATTRIBUTE: _(
        'Could not register %(item)s: it does not have a "%(attr_name)s" '
        'attribute.'
    ),
    UNREGISTER: _(
        'Could not unregister %(item)s: it is not registered.'
    ),
    NOT_REGISTERED: _(
        'No item registered with %(attr_name)s = %(attr_value)s.'
    ),
}


class RegistryState(Enum):
    """The operations state of a registry.

    Version Added:
        5.0
    """

    #: The registry is pending setup.
    PENDING = 0

    #: The registry is in the process of populating default items.
    POPULATING = 1

    #: The registry is populated and ready to be used.
    READY = 2


class Registry(Generic[RegistryItemType]):
    """An item registry.

    Item registries hold a set of objects that can be looked up by attributes.
    Each item is guaranteed to be unique and not share these attributes with
    any other item in the registry.

    Registries default to holding arbitrary objects. To limit objects to a
    specific type, specify a type when subclassing. For example:

    .. code-block:: python

        class MyRegistry(Registry[MyItemType]):
            ...

    Version Changed:
        5.0:
        * Registries now use a reentrant lock when populating, resetting,
          registering items, or unregistering items.
        * Added :py:attr:`state` for determining the current registry state.
        * Deprecated :py:attr:`populated`.
        * Added new hooks for customizing registry behavior with thread-safe
          guarantees:
          * :py:meth:`on_item_registering`,
          * :py:meth:`on_item_registered`,
          * :py:meth:`on_item_unregistering`
          * :py:meth:`on_item_unregistered`,
          * :py:meth:`on_populating`
          * :py:meth:`on_populated`,
          * :py:meth:`on_resetting`
          * :py:meth:`on_reset`.

    Version Changed:
        3.1:
        Added support for specifying a registry item type when subclassing
        this registry.
    """

    #: The name of the items being registered.
    #:
    #: Type:
    #:     str
    item_name: Optional[str] = None

    #: A list of attributes that items can be looked up by.
    #:
    #: Type:
    #:     list of str
    lookup_attrs: Sequence[str] = []

    #: Error formatting strings for exceptions.
    #:
    #: Entries here override the global :py:data:`DEFAULT_ERRORS` dictionary
    #: for error messages.
    #:
    #: Type:
    #:     dict
    errors: RegistryErrorsDict = {}

    #: The default error formatting strings.
    #:
    #: If subclasses need to provide additional errors that can be overridden,
    #: they should copy :py:data:`DEFAULT_ERRORS` and set their copy on the
    #: subclass as this attribute.
    #:
    #: Type:
    #:     dict
    default_errors: RegistryErrorsDict = DEFAULT_ERRORS

    #: The error class indicating an already registered item.
    #:
    #: This must be a subclass of
    #: :py:class:`~djblets.registries.errors.AlreadyRegisteredError`.
    #:
    #: Type:
    #:     type
    already_registered_error_class: Type[AlreadyRegisteredError] = \
        AlreadyRegisteredError

    #: The lookup error exception class.
    #:
    #: This must be a subclass of
    #: :py:class:`~djblets.registries.errors.ItemLookupError`.
    #:
    #: Type:
    #:     type
    lookup_error_class: Type[ItemLookupError] = ItemLookupError

    ######################
    # Instance variables #
    ######################

    #: The current state of the registry.
    #:
    #: Version Added:
    #:     5.0
    state: RegistryState

    #: A set of the items stored in the registry.
    _items: set[RegistryItemType]

    #: A lock used to ensure population only happens once.
    #:
    #: Version Added:
    #:     5.0
    _lock: RLock

    #: The registry of stored items.
    #:
    #: This is a mapping of lookup attribute names to value-to-item mappings.
    _registry: dict[str, dict[object, RegistryItemType]]

    def __init__(self) -> None:
        """Initialize the registry."""
        self.state = RegistryState.PENDING

        self._registry = {
            _attr_name: {}
            for _attr_name in self.lookup_attrs
        }
        self._lock = RLock()
        self._items = set()

    @property
    def populated(self) -> bool:
        """Whether or not the registry is populated.

        This can be used to determine if the registry is populated (or in
        the process of being populated).

        Consumers should check :py:attr:`state` instead, for more precise
        tracking. This method is deprecated.

        Deprecated:
            5.0:
            This has been replaced by :py:attr:`state` and will be removed in
            Djblets 7.

        Returns:
            bool:
            Whether or not the registry is populated.
        """
        RemovedInDjblets70Warning.warn(
            'Registry.populated is deprecated and will be removed in '
            'Djblets 7. Please check Registry.state instead.')

        return self.state != RegistryState.PENDING

    def format_error(
        self,
        error_name: str,
        **error_kwargs,
    ) -> str:
        """Format an error message.

        Args:
            error_name (str):
                A symbolic name for the error, such as
                :py:data:`ALREADY_REGISTERED`.

            **error_kwargs (dict):
                The keyword arguments to provide to the error-specific
                formatting string.

        Returns:
            str:
            The formatted error message.

        Raises:
            ValueError:
                A registered error message for ``error_name`` could not be
                found.
        """
        fmt = self.errors.get(error_name, self.default_errors.get(error_name))

        if fmt is None:
            raise ValueError('%s.format_error: Unknown error: "%s".',
                             type(self), error_name)

        return fmt % error_kwargs

    def get(
        self,
        attr_name: str,
        attr_value: object,
    ) -> RegistryItemType:
        """Return an item by its attribute value.

        Args:
            attr_name (str):
                The attribute name to look up an item by.

            attr_value (object):
                The corresponding attribute value.

        Returns:
            object:
            The registered item.

        Raises:
            djblets.registries.errors.ItemLookupError:
                When a lookup is attempted with an unsupported attribute, or
                the item cannot be found, this exception is raised.
        """
        self.populate()

        try:
            attr_map = self._registry[attr_name]
        except KeyError:
            raise self.lookup_error_class(self.format_error(
                INVALID_ATTRIBUTE, attr_name=attr_name))

        try:
            return attr_map[attr_value]
        except KeyError:
            raise self.lookup_error_class(self.format_error(
                NOT_REGISTERED, attr_name=attr_name, attr_value=attr_value))

    def get_or_none(
        self,
        attr_name: str,
        attr_value: object,
    ) -> Optional[RegistryItemType]:
        """Return the requested registered item, or None if not found.

        Version Added:
            3.1

        Args:
            attr_name (str):
                The attribute name.

            attr_value (object):
                The attribute value.

        Returns:
            object:
            The matching registered item, if found. Otherwise, ``None`` is
            returned.
        """
        try:
            return self.get(attr_name, attr_value)
        except ItemLookupError:
            return None

    def register(
        self,
        item: RegistryItemType,
    ) -> None:
        """Register an item.

        Args:
            item (object):
                The item to register with the class.

        Raises:
            djblets.registries.errors.RegistrationError:
                Raised if the item is missing one of the required attributes.

            djblets.registries.errors.AlreadyRegisteredError:
                Raised if the item is already registered or if the item shares
                an attribute name, attribute value pair with another item in
                the registry.
        """
        self.populate()
        attr_values: Dict[str, object] = {}

        with self._lock:
            if item in self._items:
                raise self.already_registered_error_class(self.format_error(
                    ALREADY_REGISTERED,
                    item=item))

            self.on_item_registering(item)

            registry_map = self._registry

            for attr_name in self.lookup_attrs:
                attr_map = registry_map[attr_name]

                try:
                    attr_value = getattr(item, attr_name)

                    if attr_value in attr_map:
                        raise self.already_registered_error_class(
                            self.format_error(ATTRIBUTE_REGISTERED,
                                              item=item,
                                              duplicate=attr_map[attr_value],
                                              attr_name=attr_name,
                                              attr_value=attr_value))

                    attr_values[attr_name] = attr_value
                except AttributeError:
                    raise RegistrationError(self.format_error(
                        MISSING_ATTRIBUTE,
                        item=item,
                        attr_name=attr_name))

            for attr_name, attr_value in attr_values.items():
                registry_map[attr_name][attr_value] = item

            self._items.add(item)
            self.on_item_registered(item)

    def unregister_by_attr(
        self,
        attr_name: str,
        attr_value: object,
    ) -> None:
        """Unregister an item from the registry by an attribute.

        Args:
            attr_name (str):
                The name of the attribute.

            attr_value (object):
                The attribute value.

        Raises:
            djblets.registries.errors.ItemLookupError:
                Raised if the attribute value is not found in the registry.
        """
        self.populate()

        with self._lock:
            try:
                attr_map = self._registry[attr_name]
            except KeyError:
                raise self.lookup_error_class(self.format_error(
                    INVALID_ATTRIBUTE,
                    attr_name=attr_name))

            try:
                item = attr_map[attr_value]
            except KeyError:
                raise self.lookup_error_class(self.format_error(
                    NOT_REGISTERED,
                    attr_name=attr_name,
                    attr_value=attr_value))

            self.unregister(item)

    def unregister(
        self,
        item: RegistryItemType,
    ) -> None:
        """Unregister an item from the registry.

        Args:
            item (object):
                The item to unregister. This must be present in the registry.

        Raises:
            djblets.registries.errors.ItemLookupError:
                Raised if the item is not found in the registry.
        """
        self.populate()

        with self._lock:
            self.on_item_unregistering(item)

            try:
                self._items.remove(item)
            except KeyError:
                raise self.lookup_error_class(self.format_error(UNREGISTER,
                                                                item=item))

            registry_map = self._registry

            for attr_name in self.lookup_attrs:
                attr_value = getattr(item, attr_name)
                del registry_map[attr_name][attr_value]

            self.on_item_unregistered(item)

    def populate(self) -> None:
        """Ensure the registry is populated.

        Calling this method when the registry is populated will have no effect.
        """
        if self.state == RegistryState.READY:
            return

        with self._lock:
            if self.state != RegistryState.PENDING:
                # This thread is actively populating the registry, or has been
                # populated while waiting for the lock to be released. We can
                # bail here.
                return

            self.state = RegistryState.POPULATING
            self.on_populating()

            for item in self.get_defaults():
                self.register(item)

            self.on_populated()
            self.state = RegistryState.READY

            registry_populating.send(sender=type(self),
                                     registry=self)

    def get_defaults(self) -> Iterable[RegistryItemType]:
        """Return the default items for the registry.

        This method should be overridden by a subclass.

        Returns:
            list:
            The default items for the registry.
        """
        return []

    def reset(self) -> None:
        """Unregister all items and mark the registry unpopulated.

        This will result in the registry containing no entries. Any call to a
        method that would populate the registry will repopulate it.
        """
        with self._lock:
            if self.state == RegistryState.READY:
                self.on_resetting()

                for item in self._items.copy():
                    self.unregister(item)

                assert len(self._items) == 0

                self.on_reset()
                self.state = RegistryState.PENDING

    def on_item_registering(
        self,
        item: RegistryItemType,
        /,
    ) -> None:
        """Handle extra steps before registering an item.

        This can be used by subclasses to perform preparation steps before
        registering an item. It's run before the item is validated and then
        registered.

        Validation can be performed in this method.

        The method is thread-safe.

        Version Added:
            5.0

        Args:
            item (object):
                The item to register.

        Raises:
            djblets.registries.errors.RegistrationError:
                There's an error registering this item.
        """
        pass

    def on_item_registered(
        self,
        item: RegistryItemType,
        /,
    ) -> None:
        """Handle extra steps after registering an item.

        This can be used by subclasses to perform additional steps when an
        item is registered. It's run after the main registration occurs.

        The method is thread-safe.

        Version Added:
            5.0

        Args:
            item (object):
                The item that was registered.
        """
        pass

    def on_item_unregistering(
        self,
        item: RegistryItemType,
        /,
    ) -> None:
        """Handle extra steps before unregistering an item.

        This can be used by subclasses to perform additional steps before
        validating and unregistering an item.

        The method is thread-safe.

        Version Added:
            5.0

        Args:
            item (object):
                The item to unregister.
        """
        pass

    def on_item_unregistered(
        self,
        item: RegistryItemType,
        /,
    ) -> None:
        """Handle extra steps after unregistering an item.

        This can be used by subclasses to perform additional steps when an
        item is unregistered. It's run after the main unregistration occurs.

        The method is thread-safe.

        Version Added:
            5.0

        Args:
            item (object):
                The item that was unregistered.
        """
        pass

    def on_populating(self) -> None:
        """Handle extra steps before a registry is populated.

        This can be used by subclasses to perform additional steps before the
        registry is populated.

        The method is thread-safe.

        Version Added:
            5.0
        """
        pass

    def on_populated(self) -> None:
        """Handle extra steps after a registry is populated.

        This can be used by subclasses to perform additional steps after the
        registry is populated. It's run after the main population occurs.

        The method is thread-safe.

        Version Added:
            5.0
        """
        pass

    def on_resetting(self) -> None:
        """Handle extra steps before resetting the registry.

        This can be used by subclasses to perform additional steps before the
        registry is reset. It's run before the main reset operations occur.

        The method is thread-safe.

        Version Added:
            5.0
        """
        pass

    def on_reset(self) -> None:
        """Handle extra steps after a registry is reset.

        This can be used by subclasses to perform additional steps after the
        registry is reset. It's run after the main reset operations occur.

        The method is thread-safe.

        Version Added:
            5.0
        """
        pass

    def __iter__(self) -> Iterator[RegistryItemType]:
        """Iterate through all items in the registry.

        This method does not provide a stable ordering.

        Yields:
            object:
            The items registered in this registry.
        """
        self.populate()

        for item in self._items:
            yield item

    def __len__(self) -> int:
        """Return the number of items in the registry.

        Returns:
            int:
            The number of items in the registry.
        """
        self.populate()
        return len(self._items)

    def __contains__(
        self,
        item: RegistryItemType,
    ) -> bool:
        """Return whether or not the item is contained in the registry.

        Args:
            item (object):
                The item to look for.

        Returns:
            bool:
            Whether or not the item is contained in the registry.
        """
        self.populate()
        return item in self._items


class EntryPointRegistry(Registry[RegistryItemType]):
    """A registry that auto-populates from an entry-point."""

    #: The entry point name.
    #:
    #: Type:
    #:     str
    entry_point: Optional[str] = None

    def get_defaults(self) -> Iterable[RegistryItemType]:
        """Yield the values from the entry point.

        Yields:
            object:
            The object from the entry point.
        """
        if self.entry_point is not None:
            eps = entry_points(group=self.entry_point)

            for ep in eps:
                try:
                    yield self.process_value_from_entry_point(ep)
                except Exception as e:
                    logger.exception(self.format_error(LOAD_ENTRY_POINT,
                                                       entry_point=ep.name,
                                                       error=e))

    def process_value_from_entry_point(
        self,
        entry_point: EntryPoint,
    ) -> RegistryItemType:
        """Return the item to register from the entry point.

        By default, this returns the loaded entry point.

        Args:
            entry_point (importlib.metadata.EntryPoint):
                The entry point.

        Returns:
            object:
            The processed entry point value.
        """
        return entry_point.load()


class OrderedRegistry(Registry[RegistryItemType]):
    """A registry that keeps track of registration order."""

    def __init__(self) -> None:
        """Initialize the OrderedRegistry"""
        super(OrderedRegistry, self).__init__()

        self._by_id: Dict[int, RegistryItemType] = {}
        self._key_order: List[int] = []

    def on_item_registered(
        self,
        item: RegistryItemType,
        /,
    ) -> None:
        """Handle extra steps before registering an item.

        This will place the item in sequential order.

        Subclasses that override this to perform additional post-registration
        operations must first call this method.

        Version Added:
            5.0

        Args:
            item (object):
                The item that was registered.
        """
        item_id = id(item)
        self._key_order.append(item_id)
        self._by_id[item_id] = item

    def on_item_unregistered(
        self,
        item: RegistryItemType,
        /,
    ) -> None:
        """Handle extra steps after unregistering an item.

        Subclasses that override this to perform additional
        post-unregistration operations must first call this method.

        Version Added:
            5.0

        Args:
            item (object):
                The item that was unregistered.
        """
        item_id = id(item)
        del self._by_id[item_id]
        self._key_order.remove(item_id)

    def __iter__(self) -> Iterator[RegistryItemType]:
        """Yield the items in the order they were registered.

        Yields:
            object:
            The registered items.
        """
        self.populate()

        by_id = self._by_id

        for key in self._key_order:
            yield by_id[key]

    def __getitem__(
        self,
        index: int,
    ) -> RegistryItemType:
        """Return an item by its registered index.

        Args:
            index (int):
                The position at which the item was registered. This is 0-based
                and negative indices are supported.

        Returns:
            object:
            The requested item.

        Raises:
            IndexError:
                This exception is raised if the requested index is out of
                range.

            TypeError:
                This exception is raised if the requested index is not an
                integer.
        """
        if not isinstance(index, int):
            raise TypeError('Index is not an integer (is %s).'
                            % type(index).__name__)

        # We don't have to call populate() because calling len() will.
        length = len(self)

        if index < 0:
            index += length

        if index > length:
            raise IndexError('Index is out of range.')

        return self._by_id[self._key_order[index]]
