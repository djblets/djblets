"""Utility mixins for registries."""

from typing import Generic, Optional, TYPE_CHECKING

from djblets.registries.errors import ItemLookupError
from djblets.registries.registry import RegistryItemType


if TYPE_CHECKING:
    # When checking types, we set the base class to a custom class that has
    # a compatible function signature. This is done for two reasons:
    #
    # 1. So that the type checker doesn't see a call to super().get() as
    #    being an invalid method on Generic.
    #
    # 2. So the get() method has a compatible return type and doesn't result
    #    in errors during type checking (which would happen if subclassing
    #    Registry or using a Protocol).
    class _BaseClass(Generic[RegistryItemType]):
        def get(
            self,
            attr_name: str,
            attr_value: object,
        ) -> Optional[RegistryItemType]:
            ...
else:
    _BaseClass = Generic


class ExceptionFreeGetterMixin(_BaseClass[RegistryItemType]):
    """A mixin that prevents lookups from throwing errors.

    If using typed registries and inheriting from this mixin, the same type
    should be passed to this class as well.

    This class may be deprecated in the future. Callers may want to switch
    to calling :py:meth:`Registry.get_or_none()
    <djblets.registries.registry.Registry.get_or_none>` instead, which offers
    the same functionality.

    Version Changed:
        3.1:
        Added support for specifying a registry item type when subclassing
        this mixin.
    """

    def get(
        self,
        attr_name: str,
        attr_value: object,
    ) -> Optional[RegistryItemType]:
        """Return the requested registered item.

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
        # This effectively duplicates Registry.get_or_none(), but since that
        # calls get(), we can't use it or we'd create an infinite loop.
        try:
            return super().get(attr_name, attr_value)
        except ItemLookupError:
            return None
