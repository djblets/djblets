"""Basic version and package information."""

# Python 3.10+ removed a bunch of aliases from the collections module.
# Unfortunately, Django 1.11 and nose still rely on these. Do this before
# anything else.
import djblets.util.compat.python.collections


# The version of Djblets
#
# This is in the format of:
#
#   (Major, Minor, Micro, alpha/beta/rc/final, Release Number, Released)
#
VERSION = (3, 0, 0, 'beta', 1, True)


def get_version_string():
    version = '%s.%s' % (VERSION[0], VERSION[1])

    if VERSION[2]:
        version += ".%s" % VERSION[2]

    if VERSION[3] != 'final':
        if VERSION[3] == 'rc':
            version += ' RC%s' % VERSION[4]
        else:
            version += ' %s %s' % (VERSION[3], VERSION[4])

    if not is_release():
        version += " (dev)"

    return version


def get_package_version():
    version = '%d.%d' % (VERSION[0], VERSION[1])

    if VERSION[2]:
        version += ".%d" % VERSION[2]

    if VERSION[3] != 'final':
        version += '%s%d' % (VERSION[3], VERSION[4])

    return version


def is_release():
    return VERSION[5]


__version_info__ = VERSION[:-1]
__version__ = get_package_version()
