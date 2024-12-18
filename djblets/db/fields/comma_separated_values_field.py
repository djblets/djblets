"""Database field for storing comma-separated values.

Version Added:
    5.0
"""

from __future__ import annotations

from typing import Optional, Sequence, TYPE_CHECKING, Union

from django.db import models

if TYPE_CHECKING:
    from django.db.backends.base.base import BaseDatabaseWrapper


class CommaSeparatedValuesField(models.CharField):
    """Database field for storing comma-separated values.

    This field wraps a comma-separated list of values, helping translate
    between Python lists of strings and the stored string.

    Items in the list are expected to be simple values, and must not contain
    a comma (``,``).

    The following methods are made available on the model containing the
    field:

    .. py:method:: MyModel.get_<fieldname>_list() -> Sequence[str]

        Return a list of display names for all items.

        If this field was set up with a ``choices=`` parameter, the choice
        display names will be used to represent each item in the list. If
        not, or if a choice is not present, the respective item's string
        representation will be used instead.

        .. versionadded:: 5.2

    .. py:method:: MyModel.get_<fieldname>_display() -> str

        Return a string display representation of the items.

        This will return a string containing a comma-separated list of
        display names for all values in the field.

        .. versionadded:: 5.2

    Version Changed:
        5.2:
        :samp:`get_<fieldname>_list()` and
        :samp:`get_<fieldname>_display()` methods are now added to the model.

    Version Added:
        5.0
    """

    def contribute_to_class(
        self,
        cls: type[models.Model],
        name: str,
        *args,
        **kwargs,
    ) -> None:
        """Add methods to the model.

        This will add the :samp:`get_{fieldname}_list()` and
        :samp:`get_{fieldname}_display()` methods to the model.

        Version Added:
            5.2

        Args:
            cls (type):
                The model class that owns the field.

            name (str):
                The name of the field.

            *args (tuple):
                Positional arguments to pass to the parent.

            **kwargs (dict):
                Keyword arguments to pass to the parent.
        """
        super().contribute_to_class(cls, name, *args, **kwargs)

        setattr(cls, f'get_{name}_list', lambda obj: self._get_list(obj))
        setattr(cls, f'get_{name}_display', lambda obj: self._get_display(obj))

    def from_db_value(
        self,
        value: Optional[str],
        *args,
    ) -> Optional[list[str]]:
        """Convert the value coming from the database.

        Args:
            value (str):
                The value to convert.

            *args (tuple, unused):
                Unused additional keyword arguments.

        Returns:
            list of str:
            The converted value.
        """
        if value is None:
            return value
        else:
            return self.to_python(value)

    def to_python(
        self,
        value: Union[str, list],
    ) -> list[str]:
        """Convert the given value from DB representation to Python.

        Args:
            value (str or list):
                The value to convert.

        Returns:
            list of str:
            The converted value.
        """
        if isinstance(value, list):
            return value
        elif value == '':
            return []
        else:
            return value.split(',')

    def get_prep_value(
        self,
        value: Optional[list[str]],
    ) -> str:
        """Convert the given Python representation to DB format.

        Args:
            value (list of str):
                The value to convert.

        Returns:
            str:
            The data to store in the database.
        """
        if value is None:
            return ''
        else:
            return ','.join(value)

    def get_db_prep_value(
        self,
        value: Union[list[str], str, None],
        connection: BaseDatabaseWrapper,
        prepared: bool = False,
    ) -> str:
        """Return the prepared value for saving to the database.

        Args:
            value (list of str or str):
                The value to save.

            connection (django.db.backends.base.base.BaseDatabaseWrapper):
                The database connection.

            prepared (bool, optional):
                Whether the value has already been prepared.
        """
        if not prepared and not isinstance(value, str):
            return self.get_prep_value(value)
        else:
            assert isinstance(value, str)
            return value

    def value_to_string(
        self,
        obj: models.Model,
    ) -> str:
        """Return the value as a string.

        Args:
            obj (django.db.models.Model):
                The model that this field is a part of.

        Returns:
            str:
            A string representation of the field contents.
        """
        return self.get_prep_value(self.value_from_object(obj))

    def get_default(self) -> list:
        """Return the default value for the field.

        Returns:
            list:
            The default value for the field.
        """
        if self.has_default() and not callable(self.default):
            return self.default

        default = super().get_default()

        if default == '':
            return []

        return default

    def _get_list(
        self,
        obj: models.Model,
    ) -> Sequence[str]:
        """Return a list of display names for all items.

        If this field was set up with a ``choices=`` parameter, the choice
        display names will be used to represent each item in the list. If
        not, or if a choice is not present, the respective item's string
        representation will be used instead.

        Version Added:
            5.2

        Args:
            obj (django.db.models.Model):
                The model owning the field.

        Returns:
            list of str:
            The list of display names for items.
        """
        choices = dict(self.choices or [])

        return [
            str(choices.get(item, item))
            for item in getattr(obj, self.name, [])
        ]

    def _get_display(
        self,
        obj: models.Model,
    ) -> str:
        """Return a string display representation of the items.

        This will return a string containing a comma-separated list of
        display names for all values in the field.

        Version Added:
            5.2

        Args:
            obj (django.db.models.Model):
                The model owning the field.

        Returns:
            str:
            The comma-separated string representation of the items.
        """
        return ', '.join(self._get_list(obj))
