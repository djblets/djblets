"""Djblets registries.

Registries are collections that keep track of unique objects.

For information on writing registries, see
:ref:`the guide on writing registries <writing-registries>`.
"""

from __future__ import unicode_literals

from django.utils.translation import ugettext as _
from django.utils import six

from djblets.registries.errors import (AlreadyRegisteredError,
                                       ItemLookupError,
                                       RegistrationError)


ALREADY_REGISTERED = 'already_registered'
ATTRIBUTE_REGISTERED = 'attribute_registered'
INVALID_ATTRIBUTE = 'invalid_attribute'
MISSING_ATTRIBUTE = 'missing_attribute'
UNREGISTER = 'unregister'
NOT_REGISTERED = 'not_registered'


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


class Registry(object):
    """An item registry.

    Item registries hold a set of objects that can be looked up by attributes.
    Each item is guaranteed to be unique and not share these attributes with
    any other item in the registry.
    """

    #: The name of the items being registered.
    item_name = None

    #: A list of attributes that items can be looked up by.
    lookup_attrs = []

    #: Error formatting strings for exceptions.
    #:
    #: Entries here override the global :py:data:`DEFAULT_ERRORS` dictionary
    #: for error messages.
    errors = {}

    #: The default error formatting strings.
    #:
    #: If subclasses need to provide additional errors that can be overridden,
    #: they should copy :py:data:`DEFAULT_ERRORS` and set their copy on the
    #: subclass as this attribute.
    default_errors = DEFAULT_ERRORS

    def format_error(self, error_name, **error_kwargs):
        fmt = self.errors.get(error_name,
                              self.default_errors[error_name])
        assert fmt

        return fmt % error_kwargs

    def __init__(self):
        """Initialize the registry."""
        self._registry = {}
        self._populated = False
        self._items = set()

        for attr_name in self.lookup_attrs:
            self._registry[attr_name] = {}

    def get(self, attr_name, attr_value):
        """Return an item by its attribute value.

        Args:
            attr_name (unicode):
                The attribute name to look up an item by.

            attr_value (object):
                The corresponding attribute value.

        Returns:
            object: The registered item.

        Raises:
            djblets.registries.errors.ItemLookupError:
                When a lookup is attempted with an unsupported attribute, or
                the item cannot be found, this exception is raised.
        """
        self.populate()

        try:
            attr_map = self._registry[attr_name]
        except KeyError:
            raise ItemLookupError(self.format_error(INVALID_ATTRIBUTE,
                                                    attr_name=attr_name))

        try:
            return attr_map[attr_value]
        except KeyError:
            raise ItemLookupError(self.format_error(NOT_REGISTERED,
                                                    attr_name=attr_name,
                                                    attr_value=attr_value))

    def register(self, item):
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
        attr_values = {}

        if item in self._items:
            raise AlreadyRegisteredError(self.format_error(
                ALREADY_REGISTERED,
                item=item))

        for attr_name in self.lookup_attrs:
            attr_map = self._registry[attr_name]

            try:
                attr_value = getattr(item, attr_name)

                if attr_value in attr_map:
                    raise AlreadyRegisteredError(self.format_error(
                        ATTRIBUTE_REGISTERED,
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

        for attr_name, attr_value in six.iteritems(attr_values):
            self._registry[attr_name][attr_value] = item

        self._items.add(item)

    def unregister_by_attr(self, attr_name, attr_value):
        """Unregister an item from the registry by an attribute.

        Args:
            attr_name (unicode):
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
            raise ItemLookupError(self.format_error(INVALID_ATTRIBUTE,
                                                    attr_name=attr_name))
        try:
            item = attr_map[attr_value]
        except KeyError:
            raise ItemLookupError(self.format_error(NOT_REGISTERED,
                                                    attr_name=attr_name,
                                                    attr_value=attr_value))

        self.unregister(item)

    def unregister(self, item):
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
            raise ItemLookupError(self.format_error(UNREGISTER, item=item))

        for attr_name in self.lookup_attrs:
            attr_value = getattr(item, attr_name)
            del self._registry[attr_name][attr_value]

    def populate(self):
        """Ensure the registry is populated.

        Calling this method more than once will have no effect.

        Returns:
            bool: Whether or not this was the first call to the method.
        """
        if self._populated:
            return False

        self._populated = True

        for item in self.get_defaults():
            self.register(item)

        return True

    def get_defaults(self):
        """Return the default items for the registry.

        This method should be overridden by a subclass.

        Returns:
            list:
            The default items for the registry.
        """
        return []

    def __iter__(self):
        """Iterate through all items in the registry.

        This method does not provide a stable ordering.

        Yields:
            object: The items registered in this registry.
        """
        self.populate()

        for item in self._items:
            yield item

    def __len__(self):
        """Return the number of items in the registry.

        Returns:
            int: The number of items in the registry.
        """
        self.populate()
        return len(self._items)

    def __contains__(self, item):
        """Return whether or not the item is contained in the registry.

        Args:
            item (object):
                The item to look for.

        Returns:
            bool: Whether or not the item is contained in the registry.
        """
        self.populate()
        return item in self._items
