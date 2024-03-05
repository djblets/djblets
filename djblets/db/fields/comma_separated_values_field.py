"""Database field for storing comma-separated values.

Version Added:
    5.0
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Union

from django.db import models

if TYPE_CHECKING:
    from django.db.backends.base.base import BaseDatabaseWrapper


class CommaSeparatedValuesField(models.CharField):
    """Database field for storing comma-separated values.

    Version Added:
        5.0
    """

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
