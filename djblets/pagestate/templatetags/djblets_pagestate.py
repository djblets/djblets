"""Template tags for working with page states.

Version Added:
    5.3
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.http import HttpRequest
from django.template import Library, RequestContext
from django.utils.html import format_html_join
from django.utils.safestring import mark_safe

from djblets.pagestate.state import PageState

if TYPE_CHECKING:
    from django.template import Context
    from django.utils.safestring import SafeString


register = Library()


@register.simple_tag(takes_context=True)
def page_hook_point(
    context: Context,
    point_name: str,
) -> SafeString:
    """Register a place where content can be injected into.

    This will render any content provided by :py:mod:`page state injectors
    <djblets.pagestate.injectors>` (such as any registered
    :py:class:`~djblets.extensions.hooks.TemplateHook` for extensions) or
    by manual calls to :py:meth:`PageState.inject()
    <djblets.pagestate.state.PageState.inject>`.

    Version Added:
        5.3

    Args:
        context (django.template.Context):
            The template rendering context.

        point_name (str):
            The name of the CSS bundle to render.

    Returns:
        django.utils.safetext.SafeString:
        The rendered HTML.

    Example:
        .. code-block:: html+django

           {% load djblets_pagestate %}

           {% page_hook_point "scripts" %}
    """
    request: HttpRequest | None

    if isinstance(context, RequestContext):
        request = context.request
    else:
        request = context.get('request')

    assert request is None or isinstance(request, HttpRequest)

    if request is None:
        return mark_safe('')

    page_state = PageState.for_request(request)

    return format_html_join(
        '',
        '{}',
        (
            (page_state_data,)
            for page_state_data in page_state.iter_content(
                point_name=point_name,
                request=request,
                context=context)
        ))
