"""Common type definitions used for Djblets and consuming projects.

Version Changed:
    6.0:
    Updated many of the exports here to just be forwarding exports for
    typelets.

Version Added:
    3.3
"""

from __future__ import annotations

from typing import Protocol

from typelets.django.json import (
    SerializableDjangoJSONDict as SerializableJSONDict,
    SerializableDjangoJSONDictImmutable as SerializableJSONDictImmutable,
    SerializableDjangoJSONList as SerializableJSONList,
    SerializableDjangoJSONListImmutable as SerializableJSONListImmutable,
    SerializableDjangoJSONValue as SerializableJSONValue,
)
from typelets.django.strings import StrOrPromise, StrPromise
from typelets.funcs import KwargsDict
from typelets.json import (
    JSONDict,
    JSONDictImmutable,
    JSONList,
    JSONListImmutable,
    JSONValue,
)


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


__all__ = [
    'JSONDict',
    'JSONDictImmutable',
    'JSONList',
    'JSONListImmutable',
    'JSONValue',
    'KwargsDict',
    'SerializableJSONDict',
    'SerializableJSONDictImmutable',
    'SerializableJSONList',
    'SerializableJSONListImmutable',
    'SerializableJSONValue',
    'SerializableJSONValue',
    'StrOrPromise',
    'StrPromise',
    'ToJsonProtocol',
]
