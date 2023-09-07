"""Common type definitions used for Djblets and consuming projects.

Version Added:
    3.3
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import (Any, Dict, List, Mapping, NewType, Protocol, Sequence,
                    TYPE_CHECKING, Union)
from uuid import UUID

from typing_extensions import TypeAlias

if TYPE_CHECKING:
    from django.utils.functional import _StrOrPromise, _StrPromise
else:
    from django.utils.functional import Promise

    # The main reason we're using NewType here is to avoid Sphinx thinking
    # this is an attribute during doc generation. At runtime here, NewType()
    # will just return Promise.
    _StrPromise: TypeAlias = NewType('StrPromise', Promise)
    _StrOrPromise: TypeAlias = Union[str, _StrPromise]


class ToJsonProtocol(Protocol):
    """Protocol for a class containing a to_json function.

    This enables supporting classes that can serialize themselves via a
    :py:meth:`to_json` method in :py:data:`SerializableJSONValue`.

    Version Added:
        4.0
    """

    def to_json(self) -> SerializableJSONValue:
        """Return a JSON-serializable value for the object.

        Returns:
            SerializableJSONValue:
            The JSON-serializable value.
        """
        ...


#: A type indicating a dictionary used for keyword arguments.
#:
#: Version Added:
#:     3.3
KwargsDict: TypeAlias = Dict[str, Any]


#: A type indicating a Unicode string or lazily-localized string.
#:
#: Version Added:
#:     3.3
StrOrPromise: TypeAlias = _StrOrPromise


#: A type indicating a lazily-localized string.
#:
#: Version Added:
#:     3.3
StrPromise: TypeAlias = _StrPromise


#: A type indicating a valid value in JSON data.
#:
#: All values are natively-supported JSON data. To support Python objects that
#: can be serialized to JSON, see :py:data:`SerializableJSONValue`.
#:
#: Version Added:
#:     3.3
JSONValue: TypeAlias = Union[
    'JSONDict',
    'JSONDictImmutable',
    'JSONList',
    'JSONListImmutable',
    None,
    bool,
    float,
    int,
    str,
]


#: A type for a dictionary mapping strings to JSON vlaues.
#:
#: All values are natively-supported JSON data. To support Python objects that
#: can be serialized to JSON, see :py:data:`SerializableJSONDict`.
#:
#: Version Added:
#:     3.3
JSONDict: TypeAlias = Dict[str, JSONValue]


#: An immutable type mapping strings to JSON vlaues.
#:
#: This is an immutable version of :py:class:`JSONDict`, which cannot be
#: modified once set. It can help with type narrowing and is recommended when
#: returning data from a function that should not be changed.
#:
#: All values are natively-supported JSON data. To support Python objects that
#: can be serialized to JSON, see :py:data:`SerializableJSONDictImmutable`.
#:
#: Version Added:
#:     3.4
JSONDictImmutable: TypeAlias = Mapping[str, JSONValue]


#: A type for a list of JSON values.
#:
#: All values are natively-supported JSON data. To support Python objects that
#: can be serialized to JSON, see :py:data:`SerializableJSONList`.
#:
#: Version Added:
#:     3.3
JSONList: TypeAlias = List[JSONValue]


#: An immutable type of a list of JSON values.
#:
#: This is an immutable version of :py:class:`JSONList`, which cannot be
#: modified once set. It can help with type narrowing and is recommended when
#: returning data from a function that should not be changed.
#:
#: All values are natively-supported JSON data. To support Python objects that
#: can be serialized to JSON, see :py:data:`SerializableJSONListImmutable`.
#:
#: Version Added:
#:     3.4
JSONListImmutable: TypeAlias = Sequence[JSONValue]


#: A type indicating a valid value that can be serialized to JSON.
#:
#: These values are all supported in
#: :py:class:`~djblets.util.serializers.DjbletsJSONEncoder`.
#:
#: Version Added:
#:     4.0
SerializableJSONValue: TypeAlias = Union[
    'SerializableJSONDict',
    'SerializableJSONDictImmutable',
    'SerializableJSONList',
    'SerializableJSONListImmutable',
    Decimal,
    JSONValue,
    StrPromise,
    ToJsonProtocol,
    UUID,
    date,
    datetime,
    time,
    timedelta,
]


#: A type for a dictionary mapping strings to JSON-serializable values.
#:
#: These values are all supported in
#: :py:class:`~djblets.util.serializers.DjbletsJSONEncoder`.
#:
#: Version Added:
#:     4.0
SerializableJSONDict: TypeAlias = Dict[str, SerializableJSONValue]


#: An immutable type mapping strings to JSON-serializable values.
#:
#: This is an immutable version of :py:class:`SerializableJSONDict`, which
#: cannot be modified once set. It can help with type narrowing and is
#: recommended when returning data from a function that should not be changed.
#:
#: These values are all supported in
#: :py:class:`~djblets.util.serializers.DjbletsJSONEncoder`.
#:
#: Version Added:
#:     4.0
SerializableJSONDictImmutable: TypeAlias = Mapping[str, SerializableJSONValue]


#: A type for a list of JSON-serializable values.
#:
#: These values are all supported in
#: :py:class:`~djblets.util.serializers.DjbletsJSONEncoder`.
#:
#: Version Added:
#:     4.0
SerializableJSONList: TypeAlias = List[SerializableJSONValue]


#: An immutable type of a list of JSON-serializable values.
#:
#: This is an immutable version of :py:class:`SerializableJSONList`, which
#: cannot be modified once set. It can help with type narrowing and is
#: recommended when returning data from a function that should not be changed.
#:
#: These values are all supported in
#: :py:class:`~djblets.util.serializers.DjbletsJSONEncoder`.
#:
#: Version Added:
#:     4.0
SerializableJSONListImmutable: TypeAlias = Sequence[SerializableJSONValue]
