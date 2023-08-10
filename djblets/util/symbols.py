"""Common symbols useful for function signatures.

Version Added:
    3.3
"""

from enum import Enum
from typing import TypeVar, Union

from typing_extensions import Final, Literal, TypeAlias


_T = TypeVar('_T')


class UnsetSymbol(Enum):
    """A type indicating an unsettable value.

    This can be useful in functions that take default values to distinguish
    between a value not provided and a false/``None`` value.

    Version Changed:
        4.0:
        This is now an Enum, allowing values to be used in
        :py:class:`typing.Literal`.

    Version Added:
        3.3
    """

    UNSET = '<UNSET>'


#: An instance of a symbol indicating an unset value.
#:
#: Version Added:
#:     3.3
UNSET: Final[Literal[UnsetSymbol.UNSET]] = UnsetSymbol.UNSET


#: A generic type alias for marking a type as unsettable.
#:
#: This allows for usage like:
#:
#: .. code-block:: python
#:
#:    def __init__(
#:        self,
#:        value: Unsettable[str],
#:    ) -> None:
#:        ...
#:
#: Version Added:
#:     4.0
Unsettable: TypeAlias = Union[Literal[UnsetSymbol.UNSET], _T]
