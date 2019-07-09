from __future__ import unicode_literals

import warnings

from django.conf.urls import url
from django.core.urlresolvers import RegexURLPattern
from django.utils import six
from django.views.decorators.cache import never_cache


def never_cache_patterns(*args):
    """Prevent any included URLs from being cached by the browser.

    It's sometimes desirable not to allow browser caching for a set of URLs.
    Any URLs passed in will have the
    :py:func:`~django.views.decorators.cache.never_cache` decorator applied.

    Args:
        *args (tuple):
            The URL arguments to pass to the function.

            If the first parameter is a prefix string for view lookup strings,
            then this will emit a deprecation warning, as these are no longer
            supported in Django 1.10 or higher.

    Returns:
        list:
        A list of URL patterns.
    """
    pattern_list = []

    for t in args:
        cb = never_cache(t.callback)

        if hasattr(t, '_callback'):
            # Django <= 1.9
            t._callback = cb
        else:
            # Django >= 1.10
            t.callback = cb

        pattern_list.append(t)

    return pattern_list
