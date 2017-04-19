"""Serial numbers used for front-end and back-end caching keys/URLs.

These functions generate stable serial numbers based on the content shipped
with the product (static media files, templates, locales). These can be used
in various cache keys, ETags, and URLs to help keep content in cache until
it changes on disk.
"""

from __future__ import unicode_literals

import logging
import os

from django.conf import settings
from django.utils import importlib


logger = logging.getLogger(__name__)


def generate_media_serial():
    """Generate a media serial number for static media files.

    The media serial number can be appended to a media filename in order to
    make a URL that can be cached forever without fear of change.  The next
    time the file is updated and the server is restarted, a new path will be
    accessed and cached.

    This will crawl the media files (using directories in
    :setting:`MEDIA_SERIAL_DIRS` if specified, or all of
    :django:setting:`STATIC_ROOT` otherwise), figuring out the latest
    timestamp, and return that value.
    """
    MEDIA_SERIAL = getattr(settings, "MEDIA_SERIAL", 0)

    if not MEDIA_SERIAL:
        media_dirs = getattr(settings, "MEDIA_SERIAL_DIRS", ["."])

        for media_dir in media_dirs:
            media_path = os.path.join(settings.STATIC_ROOT, media_dir)

            for root, dirs, files in os.walk(media_path):
                for name in files:
                    mtime = int(os.stat(os.path.join(root, name)).st_mtime)

                    if mtime > MEDIA_SERIAL:
                        MEDIA_SERIAL = mtime

        setattr(settings, "MEDIA_SERIAL", MEDIA_SERIAL)


def generate_ajax_serial():
    """Generate a template-based AJAX serial number for requests and ETags.

    The serial number can be appended to filenames involving dynamic loads of
    URLs in order to make a URL that can be cached forever without fear of
    change.

    This will crawl the template files (using directories in
    :django:setting:`TEMPLATE_DIRS`), figuring out the latest timestamp, and
    return that value.
    """
    AJAX_SERIAL = getattr(settings, "AJAX_SERIAL", 0)

    if not AJAX_SERIAL:
        template_dirs = getattr(settings, "TEMPLATE_DIRS", ["."])

        for template_path in template_dirs:
            for root, dirs, files in os.walk(template_path):
                for name in files:
                    mtime = int(os.stat(os.path.join(root, name)).st_mtime)

                    if mtime > AJAX_SERIAL:
                        AJAX_SERIAL = mtime

        setattr(settings, "AJAX_SERIAL", AJAX_SERIAL)


def generate_locale_serial(packages):
    """Generate a locale serial for the given set of packages.

    This will be equal to the most recent mtime of all the .mo files that
    contribute to the localization of the given packages.

    Unlike the other serial-generation functions, this will return the
    value, rather than setting it on ``settings``.

    Args:
        packages (list of unicode):
            A list of Python module paths containing :file:`locale`
            directories.

    Returns:
        int: The resulting serial number.
    """
    serial = 0

    paths = []
    for package in packages:
        try:
            p = importlib.import_module(package)
            path = os.path.join(os.path.dirname(p.__file__), 'locale')
            paths.append(path)
        except Exception as e:
            logger.exception(
                'Failed to import package %s to compute locale serial: %s',
                package, e)

    for locale_path in paths:
        for root, dirs, files in os.walk(locale_path):
            for name in files:
                if name.endswith('.mo'):
                    mtime = int(os.stat(os.path.join(root, name)).st_mtime)
                    if mtime > serial:
                        serial = mtime

    return serial


def generate_cache_serials():
    """Generate both static media and AJAX serial numbers.

    This is a wrapper around :py:func:`generate_media_serial` and
    :py:func:`generate_ajax_serial`, which generates all the serial numbers
    in one go.

    This should be called early in the startup, such as in the site's
    main :file:`urls.py`.
    """
    generate_media_serial()
    generate_ajax_serial()
