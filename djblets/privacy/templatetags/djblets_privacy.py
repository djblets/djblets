"""Privacy-related template tags."""

from __future__ import unicode_literals

from django import template
from django.utils.html import format_html

from djblets.privacy.pii import build_pii_safe_page_url_for_request


register = template.Library()


@register.simple_tag(takes_context=True)
def pii_safe_page_url(context):
    """Inject the current page URL with personal information redacted.

    This makes use of :py:func:`djblets.privacy.pii.build_pii_safe_page_url`
    to inject a version of the current page URL with usernames or e-mail
    addresses redacted.

    Args:
        context (django.templates.RequestContext):
            The context for the page, containing a ``request`` variable.

    Returns:
        unicode:
        The safe URL to inject into the page.

    Example:
        .. code-block:: html+django

           ga('set', 'location', '{% pii_safe_page_url %}');
    """
    return format_html(
        '{}',
        build_pii_safe_page_url_for_request(context['request']))
