from django.views.decorators.cache import never_cache


def never_cache_patterns(*args):
    """Prevent any included URLs from being cached by the browser.

    It's sometimes desirable not to allow browser caching for a set of URLs.
    Any URLs passed in will have the
    :py:func:`~django.views.decorators.cache.never_cache` decorator applied.

    Args:
        *args (tuple):
            The URL arguments to pass to the function.

    Returns:
        list:
        A list of URL patterns.
    """
    pattern_list = []

    for t in args:
        t.callback = never_cache(t.callback)
        pattern_list.append(t)

    return pattern_list
