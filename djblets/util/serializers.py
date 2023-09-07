"""Utilities for serializing content."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from django.core.serializers.json import DjangoJSONEncoder

if TYPE_CHECKING:
    from djblets.util.typing import SerializableJSONValue


class DjbletsJSONEncoder(DjangoJSONEncoder):
    """A JSON encoder that supports lazy strings, datetimes, and other objects.

    This is a specialization of
    :py:class:`~django.core.serializers.json.DjangoJSONEncoder` the does the
    following:

    * Removes the milliseconds and microseconds
      from :py:class:`datetimes <datetime.datetime>` (unless setting
      ``strip_datetime_ms=False`` when constructing the encoder). This is
      to help keep timestamps from appearing too new when compared against
      data coming from a MySQL database (which historically, and by default,
      chops off milliseconds).

    * Serializes objects (including :py:class:`Django models
      <django.db.models.base.Model>` with) containing a ``to_json`` method.
    """

    ######################
    # Instance variables #
    ######################

    #: Whether milliseconds should be stripped from a datetime.
    #:
    #: Type:
    #:     bool
    strip_datetime_ms: bool

    def __init__(
        self,
        strip_datetime_ms: bool = True,
        *args,
        **kwargs,
    ) -> None:
        """Initialize the encoder.

        Args:
            strip_datetime_ms (bool, optional):
                Determines whether milliseconds should be stripped from a
                :py:class:`~datetime.datetime`.

                This is ``True`` by default, to preserve the old behavior of
                the encoder.
        """
        super().__init__(*args, **kwargs)

        self.strip_datetime_ms = strip_datetime_ms

    def default(
        self,
        obj: SerializableJSONValue,
    ) -> SerializableJSONValue:
        """Encode the object into a JSON-compatible structure.

        The result from this will be re-encoded as JSON.

        Args:
            obj (object):
                The object to encode.

        Returns:
            object:
            A JSON-compatible value, or a value that can be serialized to
            JSON through this encoder.
        """
        # This will already have been handled. We type check to avoid
        # warnings below.
        assert obj is not None

        if isinstance(obj, set):
            return sorted(obj)
        elif self.strip_datetime_ms and isinstance(obj, datetime.datetime):
            # This is like DjangoJSONEncoder's datetime encoding
            # implementation, except that it filters out the milliseconds
            # in addition to microseconds. This ensures consistency between
            # database-stored timestamps and serialized objects.
            r = obj.isoformat()

            if obj.microsecond:
                r = r[:19] + r[26:]

            if r.endswith('+00:00'):
                r = r[:-6] + 'Z'

            return r
        elif hasattr(obj, 'to_json') and callable(obj.to_json):
            return obj.to_json()

        return super().default(obj)
