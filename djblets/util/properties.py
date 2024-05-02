"""Specialized descriptors/properties for classes."""

from __future__ import annotations

import warnings
from typing import (Any, Callable, Generic, Optional, Sequence, Tuple, Type,
                    Union, cast, overload)

from typing_extensions import Self, TypeAlias, TypeVar


# NOTE: When mypy supports PEP 696, we can give many of these defaults.
#       Setters can be based on the preceding getters as specific in
#       Generic[...]. This will simplify usage for callers in the default
#       case.
_StoredT = TypeVar('_StoredT')
_GetT = TypeVar('_GetT')
_SetT = TypeVar('_SetT')

_AliasPropertySetT = TypeVar('_AliasPropertySetT')
_AliasPropertyStoredT: TypeAlias = Any

_TypedPropertyGetT = TypeVar('_TypedPropertyGetT')
_TypedPropertyValidTypesParamT: TypeAlias = Union[Type[_SetT],
                                                  Sequence[Type[_SetT]]]


class BaseProperty(Generic[_StoredT]):
    """Base class for a custom property for a class.

    This is an optional base class that provides handy utilities that
    properties may need. For instance, being able to determine the name of
    the property's attribute on a class.

    Version Changed:
        3.3:
        This now supports generics for typing, taking the type of the stored
        content.
    """

    ######################
    # Instance variables #
    ######################

    #: The name of the owning attribute.
    #:
    #: Version Added:
    #:     3.3
    attr_name: str

    def __set_name__(
        self,
        owner: type,
        name: str,
    ) -> None:
        """Handle setting the attribute name for this property.

        Version Added:
            3.3

        Args:
            owner (type, unused):
                The class that owns the property.

            name (str):
                The attribute name for this property.
        """
        self.attr_name = name


class AliasProperty(Generic[_GetT, _AliasPropertySetT],
                    BaseProperty[_AliasPropertyStoredT]):
    """A property that aliases to another property or attribute.

    Alias properties are used to automatically retrieve from another property
    on access, or to set a value on another property. It's useful when
    wanting to rename an attribute but continue to provide a deprecated
    version, or when creating an object that provides a set of compatibility
    attributes for use with legacy code.

    Alias properties can optionally emit a deprecation warning on use, in order
    to help in the process of migrating legacy code.

    Version Changed:
        3.3:
        This now supports generics for typing, taking the types to return on
        access, and types that can be set.

    Example:
        .. code-block:: python

           class MyClass:
               new_prop: str
               old_prop: AliasProperty[int, str] = AliasProperty[int, str](
                   'new_prop',
                   convert_to_func=str,
                   convert_from_func=int)

        Note that the explicit type declaration is important. Without it,
        type checkers may allow constructors to override the type.
    """

    ######################
    # Instance variables #
    ######################

    #: Whether to emit a deprecation warning on access.
    deprecated: bool

    #: The type of class to use for the deprecation warning.
    deprecation_warning: Type[DeprecationWarning]

    #: The name of the property or attribute to read from and write to
    prop_name: str

    def __init__(
        self,
        prop_name: str,
        *,
        convert_to_func: Optional[Callable[[_AliasPropertySetT],
                                           _AliasPropertyStoredT]] = None,
        convert_from_func: Optional[Callable[[_AliasPropertyStoredT],
                                             _GetT]] = None,
        deprecated: bool = False,
        deprecation_warning: Type[DeprecationWarning] = DeprecationWarning,
    ) -> None:
        """Initialize the property.

        Version Changed:
            3.3:
            All arguments but ``prop_name`` must be provided as keyword
            arguments. This will be enforced in Djblets 5.0.

        Args:
            prop_name (str):
                The name of the property or attribute to read from and write
                to.

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

    def __set__(
        self,
        instance: object,
        value: _AliasPropertySetT,
    ) -> None:
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
                          % (cls_name, self.attr_name,
                             cls_name, self.prop_name),
                          self.deprecation_warning,
                          stacklevel=2)

        if value is not None and self._convert_to_func is not None:
            value = self._convert_to_func(value)

        setattr(instance, self.prop_name, value)

    @overload
    def __get__(
        self,
        instance: None,
        owner: Type[object],
    ) -> Self:
        ...

    @overload
    def __get__(
        self,
        instance: object,
        owner: Type[object],
    ) -> _GetT:
        ...

    def __get__(
        self,
        instance: object,
        owner: Type[object],
    ) -> Union[Self, _GetT]:
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
        if instance is None:
            return self

        if self.deprecated:
            cls_name = type(instance).__name__
            warnings.warn('%s.%s is deprecated. Please access %s.%s instead.'
                          % (cls_name, self.attr_name,
                             cls_name, self.prop_name),
                          self.deprecation_warning,
                          stacklevel=2)

        value = getattr(instance, self.prop_name)

        if value is not None and self._convert_from_func is not None:
            value = self._convert_from_func(value)

        return value


class TypedProperty(Generic[_TypedPropertyGetT, _SetT],
                    BaseProperty[_TypedPropertyGetT]):
    """A property that enforces type safety.

    This property will ensure that only values that are compatible with a
    given type can be set. This ensures type safety and helps catch errors
    early.

    Version Changed:
        3.3:
        This now supports generics for typing, taking the types to return on
        access, and types that can be set.

    Example:
        .. code-block:: python

           class MyClass:
               optional_prop: TypedProperty[Optional[str], Optional[str]] = \
                   TypedProperty(str)
               required_to_set_prop: TypedProperty[Optional[int], int] = \
                   TypedProperty(int,
                                 default=None
                                 allow_none=False)
               never_none_prop: TypedProperty[int, int] = \
                   TypedProperty(int,
                                 default=42,
                                 allow_none=False)

        Note that the explicit type declaration is important. Without it,
        type checkers may allow constructors to override the type.
    """

    ######################
    # Instance variables #
    ######################

    #: Whether a ``None`` value is allowed to be set.
    allow_none: bool

    #: The default value for the property if one is not set.
    default: Optional[_TypedPropertyGetT]

    #: The types that are valid for this property.
    #:
    #: New values are checked against this at runtime.
    valid_types: Tuple[Type[_SetT], ...]

    def __init__(
        self,
        valid_types: _TypedPropertyValidTypesParamT,
        *,
        default: Optional[_TypedPropertyGetT] = None,
        allow_none: bool = True,
    ) -> None:
        """Initialize the property.

        Version Changed:
            3.3:
            All arguments but ``prop_name`` must be provided as keyword
            arguments. This will be enforced in Djblets 5.0.

        Args:
            valid_types (list of type):
                The types of values that are permitted to be set.

            default (object, optional):
                The default value, if one is not set.

            allow_none (bool, optional):
                Whether ``None`` values are allowed to be set.
        """
        if isinstance(valid_types, tuple):
            self.valid_types = valid_types
        elif isinstance(valid_types, Sequence):
            self.valid_types = tuple(valid_types)
        else:
            self.valid_types = (valid_types,)

        self.default = default
        self.allow_none = allow_none

    def __set__(
        self,
        instance: object,
        value: _SetT,
    ) -> None:
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

        instance.__dict__['_%s_typed' % self.attr_name] = value

    @overload
    def __get__(
        self,
        instance: None,
        owner: Type[object],
    ) -> Self:
        ...

    @overload
    def __get__(
        self,
        instance: object,
        owner: Type[object],
    ) -> _TypedPropertyGetT:
        ...

    def __get__(
        self,
        instance: object,
        owner: Type[object],
    ) -> Union[Self, _TypedPropertyGetT]:
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
        if instance is None:
            return self

        return cast(
            _TypedPropertyGetT,
            instance.__dict__.get('_%s_typed' % self.attr_name, self.default))
