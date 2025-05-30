"""HTTP-related utilities."""

from __future__ import annotations

import hashlib
from typing import Mapping, Union
from urllib.parse import urlencode

from django.http import HttpResponse, HttpResponseNotModified
from django.utils.encoding import force_bytes

from djblets.util.dates import http_date


class HttpResponseNotAcceptable(HttpResponse):
    status_code = 406


def set_last_modified(response, timestamp):
    """
    Sets the Last-Modified header in a response based on a DateTimeField.
    """
    response['Last-Modified'] = http_date(timestamp)


def get_modified_since(request, last_modified):
    """
    Checks if a Last-Modified timestamp is newer than the requested
    HTTP_IF_MODIFIED_SINCE from the browser. This can be used to bail
    early if no updates have been performed since the last access to the
    page.

    This can take a DateField, datetime, HTTP date-formatted string, or
    a function for the last_modified timestamp. If a function is passed,
    it will only be called if the HTTP_IF_MODIFIED_SINCE header is present.
    """
    if_modified_since = request.META.get('HTTP_IF_MODIFIED_SINCE', None)

    if if_modified_since is not None:
        if callable(last_modified):
            last_modified = last_modified()

        return (if_modified_since == http_date(last_modified))

    return False


def set_etag(response, etag):
    """
    Sets the ETag header in a response.
    """
    response['ETag'] = etag


def encode_etag(
    etag: Union[bytes, str],
) -> str:
    """Encode a string as a SHA256 value, for use in an ETag.

    Version Changed:
        5.3:
        Uses SHA256 encoding instead of SHA1.

    Args:
        etag (bytes or str):
            The ETag to encode.

    Returns:
        str:
        The encoded ETag.
    """
    return hashlib.sha256(force_bytes(etag)).hexdigest()


def etag_if_none_match(request, etag):
    """
    Checks if an ETag matches the If-None-Match header sent by the browser.
    This can be used to bail early if no updates have been performed since
    the last access to the page.
    """
    return etag == request.META.get('HTTP_IF_NONE_MATCH', None)


def etag_if_match(request, etag):
    """
    Checks if an ETag matches the If-Match header sent by the browser. This
    is used by PUT requests to to indicate that the update should only happen
    if the specified ETag matches the header.
    """
    return etag == request.META.get('HTTP_IF_MATCH', None)


def build_not_modified_from_response(response):
    """Build a Not Modified response from an existing response.

    This will create a new :py:class:`~django.http.HttpResponseNotModified`
    containing headers from an original response. It should be used in
    conjunction with functions like :py:func:`etag_if_none_match` when
    checking against an otherwise valid response that's been built.

    Args:
        response (django.http.HttpResponse):
            The HTTP response to build the Not Modified response from.

    Returns:
        django.http.HttpResponseNotModified:
        The new Not Modified response.
    """
    new_response = HttpResponseNotModified()

    # Copy cache-related headers from the original response into the new one.
    for header_name in ('Cache-Control', 'Content-Location', 'Date', 'ETag',
                        'Expires', 'Vary'):
        try:
            new_response[header_name] = response[header_name]
        except KeyError:
            pass

    return new_response


def get_http_accept_lists(request):
    """Returns lists of mimetypes from the request's Accept header.

    This will return two lists, a list of acceptable mimetypes in order
    of requested priority, and a list of unacceptable mimetypes.
    """
    # Check cached copies for this in the request so we only ever do it once.
    if (hasattr(request, 'djblets_acceptable_mimetypes') and
        hasattr(request, 'djblets_unacceptable_mimetypes')):
        return (request.djblets_acceptable_mimetypes,
                request.djblets_unacceptable_mimetypes)

    acceptable_mimetypes = []
    unacceptable_mimetypes = []

    for accept_item in request.META.get('HTTP_ACCEPT', '').strip().split(','):
        parts = accept_item.strip().split(";")
        mimetype = parts[0]
        priority = 1.0

        for part in parts[1:]:
            try:
                key, value = part.split('=')
            except ValueError:
                # There's no '=' in that part.
                continue

            if key == 'q':
                try:
                    priority = float(value)
                except ValueError:
                    # The value isn't a number.
                    continue

        if priority == 0:
            unacceptable_mimetypes.append(mimetype)
        else:
            acceptable_mimetypes.append((mimetype, priority))

    acceptable_mimetypes.sort(key=lambda x: x[1], reverse=True)
    acceptable_mimetypes = [m[0] for m in acceptable_mimetypes]

    setattr(request, 'djblets_acceptable_mimetypes', acceptable_mimetypes)
    setattr(request, 'djblets_unacceptable_mimetypes', unacceptable_mimetypes)

    return acceptable_mimetypes, unacceptable_mimetypes


def get_http_requested_mimetype(request, supported_mimetypes):
    """Gets the mimetype that should be used for returning content.

    This is based on the client's requested list of mimetypes (in the
    HTTP Accept header) and the supported list of mimetypes that can be
    returned in this request.

    If a valid mimetype that can be used is found, it will be returned.
    Otherwise, None is returned, and the caller is expected to return
    HttpResponseNotAccepted.
    """
    acceptable_mimetypes, unacceptable_mimetypes = \
        get_http_accept_lists(request)

    supported_mimetypes_set = set(supported_mimetypes)
    acceptable_mimetypes_set = set(acceptable_mimetypes)
    unacceptable_mimetypes_set = set(unacceptable_mimetypes)

    if not supported_mimetypes_set.intersection(acceptable_mimetypes_set):
        # None of the requested mimetypes are in the supported list.
        # See if there are any mimetypes that are explicitly forbidden.
        if '*/*' in unacceptable_mimetypes:
            acceptable_mimetypes = []
            unacceptable_mimetypes = supported_mimetypes
        else:
            acceptable_mimetypes = [
                mimetype
                for mimetype in supported_mimetypes
                if mimetype not in unacceptable_mimetypes_set
            ]

    if acceptable_mimetypes:
        for mimetype in acceptable_mimetypes:
            if mimetype in supported_mimetypes:
                return mimetype

    # We didn't find any mimetypes that are on the supported list.
    # We need to choose a default now.
    for mimetype in supported_mimetypes:
        if mimetype not in unacceptable_mimetypes:
            return mimetype

    return None


def is_mimetype_a(mimetype, parent_mimetype):
    """Returns whether or not a given mimetype is a subset of another.

    This is generally used to determine if vendor-specific mimetypes is
    a subset of another type. For example,
    :mimetype:`application/vnd.djblets.foo+json` is a subset of
    :mimetype:`application/json`.
    """
    parts = mimetype.split('/')
    parent_parts = parent_mimetype.split('/')

    return (parts[0] == parent_parts[0] and
            (parts[1] == parent_parts[1] or
             parts[1].endswith('+' + parent_parts[1])))


def get_url_params_except(
    query: Mapping[str, str],
    *params: str,
) -> str:
    """Return a URL query string that filters out some params.

    This is used often when one wants to preserve some GET parameters and not
    others.

    The results are always sorted. This ensures consistent URLs, helping with
    caching and search indexing.

    Version Changed:
        5.3:
        The results are now always sorted.

    Args:
        query (dict):
            The query arguments to filter.

        *params (tuple):
            The parameters to filter out.

    Returns:
        str:
        The encoded and sorted query string.
    """
    return urlencode(sorted(
        (key, value)
        for key, value in query.items()
        if key not in params
    ))
