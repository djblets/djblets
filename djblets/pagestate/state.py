"""Page state representations.

Version Added:
    5.3
"""

from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING, overload

from django.utils.translation import gettext as _
from typing_extensions import NotRequired, TypedDict

from djblets.pagestate.injectors import page_state_injectors

if TYPE_CHECKING:
    from collections.abc import Iterator
    from hashlib import _Hash
    from typing import Literal

    from django.http import HttpRequest
    from django.template import Context
    from django.utils.safestring import SafeString
    from typing_extensions import Self


logger = logging.getLogger(__name__)


class PageStateData(TypedDict):
    """Data to inject into a page

    This represents content for the page (as HTML-safe or unsafe text) and an
    ETag to include with the page response. Both are optional.

    Version Added:
        5.3
    """

    #: The content to include in the page.
    #:
    #: This can be HTML-safe or unsafe text.
    content: NotRequired[SafeString | str]

    #: The ETag data to include for the HTTP response.
    etag: NotRequired[str | None]


class PageState:
    """Additional state used for the dynamic construction of a page.

    This is used to dynamically inject content into a page. Pages can make
    use of :py:func:`{% page_hook_point %}
    <djblets.pagestate.templatetags.djblets_pagestate.page_hook_point>`
    template tags to specify places where content can be injected.

    Content can be injected in two ways:

    1. Manually through calls to :py:meth:inject`.

    2. Dynamically by calling registered
       :py:mod:`injectors <djblets.pagestate.injectors>`, which take a
       page hook point name and provide the data to inject.

    Both content for the page and ETags for the response can be injected.

    If the same named page hook point is used in multiple places, or across
    multiple template renders within a request/response cycle, each point
    will contain the injected content.

    Version Added:
        5.3
    """

    ######################
    # Instance variables #
    ######################

    #: A mapping of point names to lists of page state data.
    _data: dict[str, list[PageStateData]]

    #: The current SHA256 for the ETags that have been processed.
    _etag_sha: _Hash | None

    @overload
    @classmethod
    def for_request(
        cls,
        request: HttpRequest,
        *,
        only_if_exists: Literal[True],
    ) -> Self | None:
        ...

    @overload
    @classmethod
    def for_request(
        cls,
        request: HttpRequest,
        *,
        only_if_exists: Literal[False] = ...
    ) -> Self:
        ...

    @classmethod
    def for_request(
        cls,
        request: HttpRequest,
        *,
        only_if_exists: bool = False,
    ) -> Self | None:
        """Return a PageState for a given HTTP request.

        The same instance will be returned every time this is called for the
        same HTTP request.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            only_if_exists (bool, optional):
                If set, this will return ``None`` if data doesn't already
                exist.

                By default, an instance will always be returned.

        Returns:
            PageState:
            The page state instance for the request.
        """
        try:
            page_state = getattr(request, '_djblets_page_state')
        except AttributeError:
            if only_if_exists:
                return None

            page_state = cls()
            setattr(request, '_djblets_page_state', page_state)

        return page_state

    def __init__(self) -> None:
        """Initialize the page state."""
        self._data = {}
        self._etag_sha = None

    def inject(
        self,
        point_name: str,
        data: PageStateData,
    ) -> None:
        """Manually inject data into the page.

        This may contain content for the page hook point, and it may
        contain ETag data to include in the final ETag.

        Args:
            point_name (str):
                The page hook point name to inject data into.

            data (PageStateData):
                The data to inject into the page hook point.

        Raises:
            ValueError:
                The page state data was missing a required key or contained
                an incorrect type.
        """
        if not data:
            return

        if 'content' in data and not isinstance(data['content'], str):
            raise ValueError(_(
                'The "content" key must contain a string or SafeString.'
            ))

        etag = data.get('etag')

        if etag is not None and not isinstance(etag, str):
            raise ValueError(_(
                'The "etag" key must be None or a string.'
            ))

        self._data.setdefault(point_name, []).append(data)

    def clear_injections(
        self,
        point_name: (str | None) = None,
    ) -> None:
        """Clear injections for one or all page hook points.

        If a point name isn't provided, manual injections will be cleared
        from all points.

        Args:
            point_name (str, optional):
                The optional page hook point name to clear injections from.
        """
        if point_name:
            self._data.pop(point_name, None)
        else:
            self._data.clear()

    def get_etag(self) -> str:
        """Return the current ETag for the page.

        If called while the page is still being rendered, future calls may
        have a different result.

        Returns:
            str:
            The current ETag for the data on the page.
        """
        if (etag_sha := self._etag_sha):
            return etag_sha.hexdigest()

        # There's nothing included for the ETag.
        return ''

    def iter_content(
        self,
        *,
        point_name: str,
        request: HttpRequest,
        context: Context,
    ) -> Iterator[SafeString | str]:
        """Iterate through rendered content for a page hook point.

        This will first iterate through all dynamic injectors and then
        through all manual injections in order.

        Any missing ETags will be generated based on the page content,
        ensuring that changes in content will cause caches to invalidate.

        Any errors coming from an injector will be logged and the injector
        skipped.

        Args:
            point_name (str):
                The page hook point name to iterate through.

            request (django.http.HttpRequest):
                The HTTP request from the client.

            context (django.template.Context):
                The context for the template.

        Yields:
            str or django.utils.safestring.SafeString:
            Each HTML-safe or unsafe content injected into the page hook
            point.
        """
        etag_sha = self._etag_sha

        for data in self.iter_page_state_data(point_name=point_name,
                                              request=request,
                                              context=context):
            content = data.get('content')

            # Ideally we'll get an ETag back, but if not, we'll use the
            # page content as data for the ETag hash.
            etag = data.get('etag') or content

            if etag:
                if etag_sha is None:
                    etag_sha = hashlib.sha256()
                    self._etag_sha = etag_sha

                etag_sha.update(etag.encode('utf-8'))

            if content:
                yield content

    def iter_page_state_data(
        self,
        *,
        point_name: str,
        request: HttpRequest,
        context: Context,
    ) -> Iterator[PageStateData]:
        """Iterate through all page state data for a page hook point.

        This will first iterate through all dynamic injectors and then
        through all manual injections in order.

        Any errors coming from an injector will be logged and the injector
        skipped.

        Args:
            point_name (str):
                The page hook point name to iterate through.

            request (django.http.HttpRequest):
                The HTTP request from the client.

            context (django.template.Context):
                The context for the template.

        Yields:
            str or django.utils.safestring.SafeString:
            Each HTML-safe or unsafe content injected into the template
            hook point.
        """
        for injector in page_state_injectors:
            try:
                yield from injector.iter_page_state_data(point_name=point_name,
                                                         request=request,
                                                         context=context)
            except Exception as e:
                logger.exception('Error iterating through page state data '
                                 'for injector %r: %s',
                                 injector, e,
                                 extra={'request': request})

        yield from self._data.get(point_name, [])
