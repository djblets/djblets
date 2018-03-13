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
    if isinstance(args[0], six.string_types):
        prefix = args[0]
        args = args[1:]
    else:
        prefix = None

    if prefix:
        msg = ('String prefixes for URLs in never_cache_patterns() is '
               'deprecated, and will not work on Django 1.10 or higher.')

        if hasattr(RegexURLPattern, 'add_prefix'):
            warnings.warn(msg, DeprecationWarning)
        else:
            raise ValueError(msg)

    pattern_list = []

    for t in args:
        if prefix:
            if isinstance(t, (list, tuple)):
                # This will crash on Django 1.10. The user has been warned.
                t = url(prefix=prefix, *t)
            elif isinstance(t, RegexURLPattern):
                # This will crash on Django 1.10. The user has been warned.
                t.add_prefix(prefix)

        cb = never_cache(t.callback)

        if hasattr(t, '_callback'):
            # Django <= 1.9
            t._callback = cb
        else:
            # Django >= 1.10
            t.callback = cb

        pattern_list.append(t)

    return pattern_list
