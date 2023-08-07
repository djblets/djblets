"""Filesystem-related utilities."""

from __future__ import annotations

import os
import sys
from typing import Any, Callable, Optional, cast

from django.core.exceptions import SuspiciousFileOperation
from typing_extensions import Protocol


class _PathModule(Protocol):
    """Protocol representing a path module.

    This helps with typing within these utility functions. It should not
    be used outside of this module, and is subject to change.

    Version Added:
        4.0
    """

    abspath: Callable[[str], str]
    dirname: Callable[[str], str]
    join: Callable[..., str]
    normcase: Callable[[str], str]
    relpath: Callable[[str, str], str]
    sep: str


def is_exe_in_path(
    name: str,
) -> bool:
    """Checks whether an executable is in the user's search path.

    This expects a name without any system-specific executable extension.
    It will append the proper extension as necessary. For example,
    use "myapp" and not "myapp.exe".

    This will return True if the app is in the path, or False otherwise.
    """

    if sys.platform == 'win32' and not name.endswith('.exe'):
        name += ".exe"

    for dir in os.environ['PATH'].split(os.pathsep):
        if os.path.exists(os.path.join(dir, name)):
            return True

    return False


def safe_join(
    base: str,
    *paths: str,
    path_mod: Any = os.path,
    rel_to: Optional[str] = None,
) -> str:
    """Safely join filesystem paths, ensuring the result is within a base path.

    This will join paths and and ensure the resulting path doesn't escape the
    base path, making it safer when including non-static path components.

    The result is always an absolute path, unless ``rel_to`` is provided.

    The implementation is based on Django's internal
    :py:func:`django.utils._os.safe_join` function, with additional
    functionality, optimizations, and typing.

    Version Added:
        4.0

    Args:
        base (str):
            The base path that the remaining paths will be joined to.

        paths (tuple of str):
            The resulting paths to join.

        path_mod (module, optional):
            An explicit path module to use.

            This is useful when building non-native filesystem paths.

        rel_to (str, optional):
            A path that the result will be made relative to.

    Returns:
        str:
        The absolute joined path.

    Raises:
        django.core.exceptions.SuspiciousFileOperation:
            The resulting path was outside of the base path.
    """
    _path_mod = cast(_PathModule, path_mod)

    result_path = _path_mod.abspath(_path_mod.join(base, *paths))
    abs_base_path = _path_mod.abspath(base)

    norm_result_path = _path_mod.normcase(result_path)
    norm_base_path = _path_mod.normcase(abs_base_path)

    # We're checking that the resulting path is somewhere within the base
    # path (rather than being the base path or higher up in the tree
    # somewhere).
    #
    # One of three conditions must be satisfied:
    #
    # 1. The resulting path is the same as the base path.
    #
    # 2. The resulting path is within the base path.
    #
    # 3. The resulting path is the root of the filesystem.
    if (norm_result_path != norm_base_path and
        not norm_result_path.startswith(norm_base_path + _path_mod.sep) and
        _path_mod.dirname(norm_base_path) != norm_base_path):
        raise SuspiciousFileOperation(
            'The joined path (%r) is located outside of the base path (%r).'
            % (result_path, abs_base_path))

    if rel_to:
        result_path = _path_mod.relpath(result_path, rel_to)

    return result_path
