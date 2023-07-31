"""Utilities for working with functional code.

Version Added:
    4.0
"""

from __future__ import annotations

import itertools
import re
from collections import deque
from typing import Any, AnyStr, Iterable, cast

from django.utils.functional import SimpleLazyObject


def iterable_len(
    iterable: Iterable[Any],
) -> int:
    """Return the length of an iterable.

    This is an efficient way of counting the total number of items in an
    iterable.

    Note that this requires that the iterable is finite in length, and does not
    result in an infinite loop.

    Version Added:
        4.0

    Args:
        iterable (iterable):
            The iterable of which to compute the length.

    Returns:
        int:
        The length of the iterable.
    """
    if hasattr(iterable, '__len__'):
        return len(iterable)  # type: ignore

    # Benchmarks tested across Python 3.7-3.11 show that this is far more
    # efficient than alternative methods (summing and deque + enumerate).
    counter = itertools.count()
    deque(zip(iterable, counter), maxlen=0)

    return next(counter)


def lazy_re_compile(
    regex: AnyStr,
    flags: int = 0,
) -> re.Pattern:
    """Return a lazily-compiled regular expression.

    This will be compiled the first time it's accessed, helping to reduce
    startup time when loading modules or classes that define regular
    expressions.

    Version Added:
        4.0

    Args:
        regex (bytes or str):
            The regular expression to compile.

        flags (int, optional):
            Any flags to pass when compiling the regular expression.

    Returns:
        django.utils.functional.SimpleLazyObject:
        A lazily-resolved regular expression.
    """

    return cast(re.Pattern, SimpleLazyObject(lambda: re.compile(regex, flags)))
