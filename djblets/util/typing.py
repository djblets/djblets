"""Common type definitions used for Djblets and consuming projects.

Version Added:
    3.3
"""

from __future__ import annotations

from typing import Any, Dict, List, NewType, TYPE_CHECKING, Union

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


#: A type indicating a valid value in JSON data.
#:
#: Version Added:
#:     3.3
JSONValue: TypeAlias = Union[
    'JSONDict',
    'JSONList',
    None,
    bool,
    float,
    int,
    str,
]


#: A type for a JSON dictionary mapping strings to JSON vlaues.
#:
#: Version Added:
#:     3.3
JSONDict: TypeAlias = Dict[str, JSONValue]


#: A type for a JSON list of values.
#:
#: Version Added:
#:     3.3
JSONList: TypeAlias = List[JSONValue]


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
