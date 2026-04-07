"""Basic version and package information."""

from __future__ import annotations

from djblets._version import (
    VERSION,
    __version__,
    __version_info__,
    get_package_version,
    get_version_string,
    is_release,
)


__all__ = [
    'VERSION',
    '__version__',
    '__version_info__',
    'get_package_version',
    'get_version_string',
    'is_release',
]
