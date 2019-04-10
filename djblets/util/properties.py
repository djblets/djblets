"""Specialized descriptors/properties for classes."""

from __future__ import unicode_literals

import warnings

from django.utils import six


class BaseProperty(object):
    """Base class for a custom property for a class.

    This is an optional base class that provides handy utilities that
    properties may need. For instance, being able to determine the name of
    the property's attribute on a class.
    """

    def get_attr_name(self, instance):
        """Return the name of this property's attribute.

        The value will be computed only once per property instance.

        Args:
            instance (object):
                The instance owning this property.

        Returns:
            str:
            The name of this property on the instance.
        """
        if not hasattr(self, '_attr_name'):
            cls = type(instance)
            self._attr_name = get_descriptor_attr_name(self, cls)

            assert self._attr_name is not None, (
                'Could not find the attribute for %r on %r' % (self, cls))

        return self._attr_name


class AliasProperty(BaseProperty):
    """A property that aliases to another property or attribute.

    Alias properties are used to automatically retrieve from another property
    on access, or to set a value on another property. It's useful when
    wanting to rename an attribute but continue to provide a deprecated
    version, or when creating an object that provides a set of compatibility
    attributes for use with legacy code.

    Alias properties can optionally emit a deprecation warning on use, in order
    to help in the process of migrating legacy code.
    """

    def __init__(self, prop_name, convert_to_func=None, convert_from_func=None,
                 deprecated=False, deprecation_warning=DeprecationWarning):
        """Initialize the property.

        Args:
            prop_name (str):
                The name of the property or attribute to read from and write
                it.

            convert_to_func (callable, optional):
                An optional function to call on a value before setting it on
                the aliased property name. This must take in the value as a
                parameter and return a value to set.

            convert_from_func (callable, optional):
                An optional function to call on a value after accessing it on
                the aliased property name and before returning to the caller.
                This must take in the value from the aliased property and
                return a value to return to the caller.

            deprecated (bool, optional):
                Whether to emit a deprecation warning when setting or accessing
                the property.

            deprecation_warning (type):
                The type of class to use for the deprecation warning. This
                should be a subclass of :py:class:`DeprecationWarning`.
        """
        self.prop_name = prop_name
        self.deprecated = deprecated
        self.deprecation_warning = deprecation_warning

        self._convert_to_func = convert_to_func
        self._convert_from_func = convert_from_func

    def __set__(self, instance, value):
        """Set a value on the property.

        This will convert the value (if ``convert_to_func`` was provided
        to this property) and set it on the aliased property.

        If this is a deprecated property, this will emit a warning.

        Args:
            instance (object):
                The instance owning this property.

            value (object):
                The value being set.
        """
        if self.deprecated:
            cls_name = type(instance).__name__
            warnings.warn('%s.%s is deprecated. Please set %s.%s instead.'
                          % (cls_name, self.get_attr_name(instance),
                             cls_name, self.prop_name),
                          self.deprecation_warning,
                          stacklevel=2)

        if value is not None and self._convert_to_func is not None:
            value = self._convert_to_func(value)

        setattr(instance, self.prop_name, value)

    def __get__(self, instance, owner):
        """Return the value of the property.

        This will retrieve the value from the aliased property, converting
        it (if ``convert_from_func`` was provided to this property), and
        return it.

        If this is a deprecated property, this will emit a warning.

        Args:
            instance (object):
                The instance owning this property.

            owner (type):
                The instance's class.

        Returns:
            object:
            The property value.
        """
        if self.deprecated:
            cls_name = type(instance).__name__
            warnings.warn('%s.%s is deprecated. Please access %s.%s instead.'
                          % (cls_name, self.get_attr_name(instance),
                             cls_name, self.prop_name),
                          self.deprecation_warning,
                          stacklevel=2)

        value = getattr(instance, self.prop_name)

        if value is not None and self._convert_from_func is not None:
            value = self._convert_from_func(value)

        return value


class TypedProperty(BaseProperty):
    """A property that enforces type safety.

    This property will ensure that only values that are compatible with a
    given type can be set. This ensures type safety and helps catch errors
    early.
    """

    def __init__(self, valid_types, default=None, allow_none=True):
        """Initialize the property.

        Args:
            valid_types (list of type):
                The types of values that are permitted to be set.

            default (object, optional):
                The default value, if one is not set.

            allow_none (bool, optional):
                Whether ``None`` values are allowed to be set.
        """
        self.valid_types = valid_types
        self.default = default
        self.allow_none = allow_none

    def __set__(self, instance, value):
        """Set a value on the property.

        This will check if the value is of a valid type, and then set it on
        the instance.

        Args:
            instance (object):
                The instance owning this property.

            value (object):
                The value being set.

        Raises:
            TypeError:
                The value is not of a valid type.
        """
        if value is None and not self.allow_none:
            raise TypeError('None is not a valid value for this property.')

        if value is not None and not isinstance(value, self.valid_types):
            raise TypeError('%s (%r) is not a valid type for this property.'
                            % (type(value).__name__, value))

        attr_name = self.get_attr_name(instance)
        instance.__dict__['_%s_typed' % attr_name] = value

    def __get__(self, instance, owner):
        """Return the value of the property.

        Args:
            instance (object):
                The instance owning this property.

            owner (type):
                The instance's class.

        Returns:
            object:
            The property value.
        """
        attr_name = self.get_attr_name(instance)
        return instance.__dict__.get('_%s_typed' % attr_name, self.default)


def get_descriptor_attr_name(descriptor, cls):
    """Return the name of a property/descriptor instance on a class.

    This will go through the class and all parent classes, looking for the
    property, and returning its attribute name. This is primarily intended
    to help with providing better error messages.

    Args:
        descriptor (object):
            The instance of the property/descriptor. For a proper value to
            be returned, this must exist on ``cls``.

        cls (type):
            The class owning the property.

    Returns:
        str:
        The name of the property/descriptor.
    """
    for attr_name, attr_value in six.iteritems(cls.__dict__):
        if attr_value is descriptor:
            return attr_name

    for parent_cls in cls.__mro__:
        attr_name = get_descriptor_attr_name(descriptor, parent_cls)

        if attr_name is not None:
            return attr_name

    return None
