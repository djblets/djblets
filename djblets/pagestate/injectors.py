"""Injectors for page state.

Version Added:
    5.3
"""

from __future__ import annotations

from typing import Protocol, TYPE_CHECKING

from djblets.registries.registry import OrderedRegistry

if TYPE_CHECKING:
    from collections.abc import Iterator

    from django.http import HttpRequest
    from django.template import Context

    from djblets.pagestate.state import PageStateData


class PageStateInjectorProtocol(Protocol):
    """Protocol describing page state injectors.

    Classes implementing this protocol can dynamically provide data for
    page state. They must be registered with :py:attr:`page_state_injectors`.

    Version Added:
        5.3
    """

    #: The unique ID of the injector.
    injector_id: str

    def iter_page_state_data(
        self,
        *,
        point_name: str,
        request: HttpRequest,
        context: Context,
    ) -> Iterator[PageStateData]:
        """Generate page state data.

        Implementations may yield zero or more
        :py:class:`~djblets.pagestate.state.PageStateData` for a given
        page hook point name. These will be made available in the page.

        Args:
            point_name (str):
                The page hook point name to populate.

            request (django.http.HttpRequest):
                The HTTP request from the client.

            context (django.template.Context):
                The context for the templates.

        Yields:
            djblets.pagestate.state.PageStateData:
            Data for provide for the page hook point.
        """
        ...


class PageStateInjectorRegistry(OrderedRegistry[PageStateInjectorProtocol]):
    """A registry for managing page state injectors.

    Version Added:
        5.3
    """

    lookup_attrs = ('injector_id',)


#: The main registry for managing page state injectors.
#:
#: Version Added:
#:     5.3
page_state_injectors = PageStateInjectorRegistry()
