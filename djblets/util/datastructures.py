"""Utilities for working with data structures.

Version Added:
    5.1
"""

from __future__ import annotations

from typing import Any, Sequence


def dict_get_path_value(
    d: dict[str, Any],
    path: Sequence[str],
) -> Any:
    """Return a value from a nested dictionary, given a path of keys.

    This is useful for looking up a value in a nested tree of dictionaries,
    based on a key path.

    Version Added:
        5.1

    Args:
        d (dict):
            The starting dictionary.

        path (list of str):
            The key path.

    Returns:
        object:
        The value at that key.

    Raises:
        KeyError:
            A key in the path could not be found in the dictionary.

        TypeError:
            A value found for part of the key was not a dictionary and could
            not be traversed.
    """
    if not path:
        raise KeyError('The key path cannot be empty.')

    value: Any = d
    i = 0

    try:
        for i, key in enumerate(path):
            # This may raise a KeyError.
            value = value[key]
    except KeyError:
        raise KeyError('Key %r not found.' % path[:i + 1])
    except TypeError:
        # Something in the path was not a dictionary.
        raise TypeError(
            'Key %r is not a dictionary (trying to resolve key %r).'
            % (path[:i], path))

    return value


def dict_set_path_value(
    d: dict[str, Any],
    path: Sequence[str],
    value: Any,
) -> None:
    """Set a value in a nested dictionary, given a path of keys.

    This is useful for setting a value in a nested tree of dictionaries,
    based on a key path.

    If any key in the path points to a non-dictionary value, that value will
    be replaced with a new dictionary.

    Version Added:
        5.1

    Args:
        d (dict):
            The starting dictionary.

        path (list of str):
            The key path.

        value (object):
            The value to set.
    """
    if not path:
        raise KeyError('The key path cannot be empty.')

    for key in path[:-1]:
        child: dict[str, Any]

        try:
            child = d[key]

            if not isinstance(child, dict):
                # Trigger a rebuild of this key.
                raise KeyError
        except KeyError:
            child = {}
            d[key] = child

        d = child

    d[path[-1]] = value
