"""Djblets registries.

Registries are collections that keep track of unique objects.

For information on writing registries, see
:ref:`the guide on writing registries <writing-registries>`.
"""

import logging
from typing import (Dict, Generic, Iterable, Iterator, List, Optional,
                    Sequence, Set, Type, TypeVar)

from django.utils.translation import gettext_lazy as _
from pkg_resources import EntryPoint, iter_entry_points

from djblets.registries.errors import (AlreadyRegisteredError,
                                       ItemLookupError,
                                       RegistrationError)
from djblets.registries.signals import registry_populating


ALREADY_REGISTERED = 'already_registered'
ATTRIBUTE_REGISTERED = 'attribute_registered'
INVALID_ATTRIBUTE = 'invalid_attribute'
MISSING_ATTRIBUTE = 'missing_attribute'
UNREGISTER = 'unregister'
NOT_REGISTERED = 'not_registered'
LOAD_ENTRY_POINT = 'load_entry_point'


#: Default error messages for registries.
DEFAULT_ERRORS = {
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


#: A generic type for items stored in a registry.
#:
#: This can be used for subclasses of :py:class:`Registry`, mixins, or other
#: utility code that need to stay generic. In normal usage, an explicit type
#: will be provided when subclassing instead.
#:
#: Version Added:
#:     3.1
RegistryItemType = TypeVar('RegistryItemType')


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
    errors: Dict[str, str] = {}

    #: The default error formatting strings.
    #:
    #: If subclasses need to provide additional errors that can be overridden,
    #: they should copy :py:data:`DEFAULT_ERRORS` and set their copy on the
    #: subclass as this attribute.
    #:
    #: Type:
    #:     dict
    default_errors: Dict[str, str] = DEFAULT_ERRORS

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

    def __init__(self) -> None:
        """Initialize the registry."""
        self._registry: Dict[str, Dict[object, RegistryItemType]] = {
            _attr_name: {}
            for _attr_name in self.lookup_attrs
        }
        self._populated: bool = False
        self._items: Set[RegistryItemType] = set()

    @property
    def populated(self) -> bool:
        """Whether or not the registry is populated.

        Returns:
            bool:
            Whether or not the registry is populated.
        """
        return self._populated

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

        if item in self._items:
            raise self.already_registered_error_class(self.format_error(
                ALREADY_REGISTERED,
                item=item))

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

        try:
            attr_map = self._registry[attr_name]
        except KeyError:
            raise self.lookup_error_class(self.format_error(
                INVALID_ATTRIBUTE, attr_name=attr_name))
        try:
            item = attr_map[attr_value]
        except KeyError:
            raise self.lookup_error_class(self.format_error(
                NOT_REGISTERED, attr_name=attr_name, attr_value=attr_value))

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

        try:
            self._items.remove(item)
        except KeyError:
            raise self.lookup_error_class(self.format_error(UNREGISTER,
                                                            item=item))

        registry_map = self._registry

        for attr_name in self.lookup_attrs:
            attr_value = getattr(item, attr_name)
            del registry_map[attr_name][attr_value]

    def populate(self) -> None:
        """Ensure the registry is populated.

        Calling this method when the registry is populated will have no effect.
        """
        if self._populated:
            return

        self._populated = True

        for item in self.get_defaults():
            self.register(item)

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
        if self._populated:
            for item in self._items.copy():
                self.unregister(item)

            self._populated = False

        assert len(self._items) == 0

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
            entry_points = iter_entry_points(self.entry_point)

            for ep in entry_points:
                try:
                    yield self.process_value_from_entry_point(ep)
                except Exception as e:
                    logging.exception(self.format_error(LOAD_ENTRY_POINT,
                                                        entry_point=ep.name,
                                                        error=e))

    def process_value_from_entry_point(
        self,
        entry_point: EntryPoint,
    ) -> RegistryItemType:
        """Return the item to register from the entry point.

        By default, this returns the loaded entry point.

        Args:
            entry_point (pkg_resources.EntryPoint):
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
        super(OrderedRegistry, self).register(item)
        item_id = id(item)
        self._key_order.append(item_id)
        self._by_id[item_id] = item

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
        super(OrderedRegistry, self).unregister(item)
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
