"""Functions for safeguarding personally identifiable information."""

from __future__ import unicode_literals

import re

from django.conf import settings
from django.utils import six


#: A default list of unsafe keywords for URL patterns and querysets.
DEFAULT_PII_UNSAFE_URL_KEYWORDS = ('user', 'mail')


def build_pii_safe_page_url(url, url_kwargs=None, query_dict=None,
                            unsafe_keywords=None):
    """Return the current page URL with personal information redacted.

    This takes a URL and keywords used to match and build components of that
    URL and and looks for information to redact. It does this by inspecting
    ``url_kwargs`` and looking for any that contain certain keywords ("user"
    and "mail" by default) or could be e-mail addresses (containing a "@"),
    replacing them with "<REDACTED>". The redaction also applies to keys in the
    query string (if ``query_dict`` is provided).

    This can be used for services like Google Analytics, logging, or other
    purposes where a rough URL is needed that does not need to directly
    identify a specific location.

    Custom keywords can be set using the
    ``settings.DJBLETS_PII_UNSAFE_URL_KEYWORDS`` setting.

    Args:
        url (unicode):
            The URL to make safe.

        url_kwargs (dict, optional):
            A dictionary of keywords to values found in the URL. These keywords
            are matched against the list of unsafe keywords.

        query_dict (django.http.QueryDict, optional):
            An optional query dictionary representing a parsed querystring. If
            provided, the result will be appended to the URL.

        unsafe_keywords (set, optional):
            Custom keywords to match that are considered unsafe. This replaces
            the default keywords.

    Returns:
        unicode:
        The safe URL stripped of identifying information.
    """
    def _build_unsafe_keys(d):
        unsafe_keys = set()

        for key, value in six.iteritems(d):
            if isinstance(value, six.text_type):
                if '@' in value:
                    # This might be an e-mail address. Redact it.
                    unsafe_keys.add(key)
                else:
                    # Check for any keyword arguments that contain any unsafe
                    # keyword names as part of the key.
                    for unsafe_key in unsafe_keywords:
                        if unsafe_key in key:
                            unsafe_keys.add(key)
                            break

        return unsafe_keys

    unsafe_keywords = set(unsafe_keywords or
                          getattr(settings, 'DJBLETS_PII_UNSAFE_URL_KEYWORDS',
                                  DEFAULT_PII_UNSAFE_URL_KEYWORDS))

    cur_unsafe_url_keys = _build_unsafe_keys(url_kwargs or {})
    cur_unsafe_qs_keys = _build_unsafe_keys(query_dict or {})

    if cur_unsafe_url_keys:
        # This is not perfect. It's entirely possible that part of what we're
        # trying to replace would appear elsewhere in the URL, and we'd redact
        # more than what we intended.
        #
        # Ideally, we'd grab the original regex and try to fill out the URL
        # based on the resolved match and redacted data, but we don't have
        # that information handy.
        #
        # Really, this is just for the purposes of providing URLs in places
        # that need some informative URL without PII, so this will suffice.
        new_url = re.sub(
            '(%s)' % '|'.join(
                re.escape(url_kwargs[key])
                for key in cur_unsafe_url_keys
            ),
            '<REDACTED>',
            url)
    else:
        new_url = url

    if cur_unsafe_qs_keys:
        new_query = query_dict.copy()

        # We want to set this through a loop instead of using update() in
        # order to properly replace keys instead of appending to them when
        # using a QueryDict.
        for key in cur_unsafe_qs_keys:
            new_query[key] = '<REDACTED>'
    else:
        new_query = query_dict

    if new_query:
        new_url = '%s?%s' % (new_url, new_query.urlencode(safe='/<>'))

    return new_url


def build_pii_safe_page_url_for_request(request, unsafe_keywords=None):
    """Return the current page URL with personal information redacted.

    This wraps :py:func:`build_pii_safe_page_url`, returning a PII-safe URL
    based on the URL pattern used for the current page.

    Args:
        request (django.http.HttpRequest):
            The HTTP request from the client.

        unsafe_keywords (set, optional):
            Custom keywords to match that are considered unsafe. This replaces
            the default keywords.

    Returns:
        unicode:
        The safe URL stripped of identifying information.
    """
    if request.resolver_match is None:
        url_kwargs = {}
    else:
        url_kwargs = request.resolver_match.kwargs

    return build_pii_safe_page_url(url=request.path,
                                   url_kwargs=url_kwargs,
                                   query_dict=request.GET,
                                   unsafe_keywords=unsafe_keywords)
