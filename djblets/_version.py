"""Version information for Djblets.

Version Added:
    6.0:
    Moved these from :file:`djblets/__init__.py`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import TypeAlias

    #: Type for version tuples.
    #:
    #: Version Added:
    #:     6.0
    _Version: TypeAlias = tuple[int, int, int, str, int, bool]


# The version of Djblets.
#
# This is in the format of:
#
#   (Major, Minor, Micro, alpha/beta/rc/final, Release Number, Released)
#
VERSION: _Version = (6, 0, 0, 'alpha', 0, False)


def get_version_string() -> str:
    """Return the Djblets version as a human-readable string.

    Returns:
        str:
        The Djblets version.
    """
    major, minor, micro, tag, release_num, is_release = VERSION
    version = f'{major}.{minor}'

    if micro:
        version += f'.{micro}'

    if tag != 'final':
        if VERSION[3] == 'rc':
            version += f' RC{release_num}'
        else:
            version += f' {tag} {release_num}'

    if not is_release:
        version += ' (dev)'

    return version


def get_package_version() -> str:
    """Return the Djblets version as a Python package version string.

    Returns:
        str:
        The Djblets package version.
    """
    major, minor, micro, tag, release_num = VERSION[:5]

    version = f'{major}.{minor}'

    if micro:
        version += f'.{micro}'

    if tag != 'final':
        if tag == 'alpha':
            tag = 'a'
        elif tag == 'beta':
            tag = 'b'

        version += f'{tag}{release_num}'

    return version


def is_release() -> bool:
    """Return whether this is a released version of Djblets.

    Returns:
        bool:
        ``True`` if this is an official release.
    """
    return VERSION[5]


#: An alias for the version information from :py:data:`VERSION`.
#:
#: This does not include the last entry in the tuple (the release state).
__version_info__ = VERSION[:-1]


#: An alias for the package version string.
__version__ = get_package_version()
