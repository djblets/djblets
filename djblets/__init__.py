"""Basic version and package information."""

from __future__ import annotations


# The version of Djblets
#
# This is in the format of:
#
#   (Major, Minor, Micro, alpha/beta/rc/final, Release Number, Released)
#
VERSION: tuple[int, int, int, str, int, bool] = \
    (6, 0, 0, 'alpha', 0, False)


def get_version_string() -> str:
    """Return the djblets version as a human-readable string.

    Returns:
        str:
        The djblets version string.
    """
    major, minor, micro, tag, release_num, released = VERSION
    version = f'{major}.{minor}'

    if micro:
        version += f'.{micro}'

    if tag != 'final':
        if tag == 'rc':
            version += f' RC{release_num}'
        else:
            version += f' {tag} {release_num}'

    if not released:
        version += ' (dev)'

    return version


def get_package_version() -> str:
    """Return the djblets package version.

    Returns:
        str:
        The djblets package version.
    """
    major, minor, micro, tag, release_num = VERSION[:-1]

    version = f'{major}.{minor}'

    if micro:
        version = '%s.%d' % (version, micro)

    if tag != 'final':
        if tag == 'alpha':
            tag = 'a'
        elif tag == 'beta':
            tag = 'b'

        version += f'{tag}{release_num}'

    return version


def is_release() -> bool:
    """Return whether the current version is released.

    Returns:
        bool:
        True if the current version is a release.
    """
    return VERSION[-1]


__version_info__ = VERSION[:-1]
__version__ = get_package_version()
