"""Context processors for serial numbers used for front-end caching.

These context processors can be used to inject the :setting:`MEDIA_SERIAL`
and :setting:`AJAX_SERIAL` settings into templates so that links can be
built that take these caching serials into account.

See :py:mod:`djblets.cache.serials` for more information on building these
serials.
"""

from __future__ import unicode_literals

from django.conf import settings


def media_serial(request):
    """Add ``MEDIA_SERIAL`` to template contexts.

    Exposes a media serial number that can be appended to a media filename
    in order to make a URL that can be cached forever without fear of change.
    The next time the file is updated and the server is restarted, a new
    path will be accessed and cached.

    This returns the value of :setting:`MEDIA_SERIAL`, which must either be
    set manually or ideally should be set to the value of
    :py:func:`djblets.cache.serials.generate_media_serial`.
    """
    return {'MEDIA_SERIAL': getattr(settings, "MEDIA_SERIAL", "")}


def ajax_serial(request):
    """Add ``AJAX_SERIAL`` to template contexts.

    Exposes a serial number that can be appended to filenames involving
    dynamic loads of URLs in order to make a URL that can be cached forever
    without fear of change.

    This returns the value of :setting:`AJAX_SERIAL`, which must either be
    set manually or ideally should be set to the value of
    :py:func:`djblets.cache.serials.generate_ajax_serial`.
    """
    return {'AJAX_SERIAL': getattr(settings, "AJAX_SERIAL", "")}
