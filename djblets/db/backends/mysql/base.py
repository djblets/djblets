"""Database backend for MySQL with backported fixes."""

from __future__ import unicode_literals

from django.db.backends.mysql.base import (DatabaseWrapper as
                                           BaseMySQLDatabaseWrapper)


class DatabaseWrapper(BaseMySQLDatabaseWrapper):
    """Database backend for MySQL.

    This is a specialized version of the standard Django MySQL database backend
    which adds backported compatibility fixes from newer versions of Django.

    Currently, this fixes an issue where contents going into a
    :py:class:`~django.db.models.BinaryField` could trigger a MySQL warning
    due to the binary contents being validated as Unicode. This bug was fixed
    in Django 1.10.5, but is present on older versions.

    To use this backend, just use ``djblets.db.backends.mysql`` as the database
    backend instead of ``django.db.backends.mysql`` in :file:`settings.py`.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the database backend.

        Args:
            *args (tuple):
                Positional arguments for the backend.

            **kwargs (dict):
                Keyword arguments for the backend.
        """
        super(DatabaseWrapper, self).__init__(*args, **kwargs)

        # Django 1.10.5 fixes an issue where BinaryField on certain versions
        # of MySQL results in warnings when injecting non-Unicode text. If
        # the database backend doesn't have this fix, we need to inject it.
        ops_cls = self.ops.__class__

        if not hasattr(ops_cls, 'binary_placeholder_sql'):
            from django.db.models.fields import BinaryField

            assert not hasattr(BinaryField, 'get_placeholder')

            ops_cls.binary_placeholder_sql = self._ops_binary_placeholder_sql
            BinaryField.get_placeholder = self._binary_field_get_placeholder

    def _ops_binary_placeholder_sql(self, value):
        """Return the placeholder format string for binary content.

        This is used by :py:class:`~django.db.models.BinaryField` to retrieve
        the format string for injecting binary contents into the database.
        On MySQL, we want to prefix the contents with ``_binary``.

        Args:
            value (bytes):
                The binary contents used to determine what kind of format
                string to use.

        Returns:
            unicode:
            The format string. This is intended to be Unicode, according to
            the Django 1.10.5 code.
        """
        if value is not None:
            return '_binary %s'
        else:
            return '%s'

    def _binary_field_get_placeholder(self, value, *args):
        """Return the placeholder format string used for the BinaryField.

        If the database backend supports it, this will return a special
        format string used for injecting binary content into the database.

        Args:
            value (bytes):
                The binary contents used to determine what kind of format
                string to use.

            *args (tuple):
                Additional arguments passed to this function. Depending on
                the version of Django, this will either encompass one or two
                arguments (the connection being the last one).

        Returns:
            unicode:
            The format string. This is intended to be Unicode, according to
            the Django 1.10.5 code.
        """
        connection = args[-1]
        ops = connection.ops

        if hasattr(ops, 'binary_placeholder_sql'):
            return ops.binary_placeholder_sql(value)
        else:
            return '%s'
