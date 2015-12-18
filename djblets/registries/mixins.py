"""Utility mixins for registries."""

from __future__ import unicode_literals

from djblets.registries.errors import ItemLookupError


class ExceptionFreeGetterMixin(object):
    """A mixin that prevents lookups from throwing errors."""

    def get(self, attr_name, attr_value):
        """Return the requested registered item.

        Args:
            attr_name (unicode):
                The attribute name.

            attr_value (object):
                The attribute value.

        Returns:
            object:
            The matching registered item, if found. Otherwise, ``None`` is
            returned.
        """
        try:
            return super(ExceptionFreeGetterMixin, self).get(attr_name,
                                                             attr_value)
        except ItemLookupError:
            return None
