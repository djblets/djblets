"""Template tags for using gravatars."""

from django import template
from django.utils.html import format_html

from djblets.gravatars import (get_gravatar_url,
                               get_gravatar_url_for_email)


register = template.Library()


@register.simple_tag
def gravatar(user, size=None):
    """Return HTML for displaying a user's Gravatar.

    This is also influenced by the following Django settings:

    ``GRAVATAR_SIZE``:
        The default size for Gravatars.

    ``GRAVATAR_RATING``:
        The maximum allowed rating (one of ``'g'``, ``'pg'``, ``'r'``, or
        ``'x'``).

    ``GRAVATAR_DEFAULT``:
        The default image to show if the user hasn't specified a Gravatar (one
        of ``identicon``, ``monsterid``, or ``wavatar``).

    See https://gravatar.com for more information.

    Note that callers adhering to the GDPR should check for a user's consent
    before displaying a Gravatar on their behalf. This is checked automatically
    if using :py:mod:`djblets.avatars`.

    Args:
        user (django.contrib.auth.models.User):
            The user whose gravatar is to be displayed.

        size (int):
            An optional height and width for the image (in pixels). This will
            default to 80 if not specified.

    Returns:
        django.utils.safestring.SafeText:
        HTML for rendering the Gravatar.
    """
    url = get_gravatar_url(user=user, size=size)

    if url:
        return format_html(
            '<img src="{0}" width="{1}" height="{1}" alt="{2}" '
            'class="gravatar"/>',
            url, size, user.get_full_name() or user.username)
    else:
        return ''


@register.simple_tag
def gravatar_url(email, size=None):
    """Return a Gravatar URL for an e-mail address.

    This is also influenced by the following Django settings:

    ``GRAVATAR_SIZE``:
        The default size for Gravatars.

    ``GRAVATAR_RATING``:
        The maximum allowed rating (one of ``'g'``, ``'pg'``, ``'r'``, or
        ``'x'``).

    ``GRAVATAR_DEFAULT``:
        The default image to show if the user hasn't specified a Gravatar (one
        of ``identicon``, ``monsterid``, or ``wavatar``).

    See https://gravatar.com for more information.

    Note that callers adhering to the GDPR should check for a user's consent
    before displaying a Gravatar on their behalf. This is checked automatically
    if using :py:mod:`djblets.avatars`.

    Args:
        email (unicode):
            The e-mail address.

        size (int):
            An optional height and width of the image (in pixels). This will
            default to 80 if not specified.

    Returns:
        django.utils.safestring.SafeText:
        HTML for rendering the Gravatar.
    """
    return get_gravatar_url_for_email(email=email, size=size)
