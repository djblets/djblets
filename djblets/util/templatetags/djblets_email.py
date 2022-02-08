"""E-mail formatting template tags."""

import re

from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from djblets.util.decorators import blocktag


register = template.Library()


@register.simple_tag(takes_context=True)
def quoted_email(context, template_name):
    """
    Renders a specified template as a quoted reply, using the current context.
    """
    return quote_text(render_to_string(template_name, context.flatten()))


@register.tag
@blocktag
def condense(context, nodelist, max_newlines=3):
    """Condenses a block of text.

    This will ensure that there are never more than the given number of
    consecutive newlines. It's particularly useful when formatting plain text
    output, to avoid issues with template tags adding unwanted newlines.
    """
    text = nodelist.render(context).strip()
    text = re.sub(r'\n{%d,}' % (max_newlines + 1), '\n' * max_newlines, text)
    return text


@register.filter
def quote_text(text, level=1):
    """
    Quotes a block of text the specified number of times.
    """
    lines = text.split("\n")
    quoted = ""

    for line in lines:
        quoted += "%s%s\n" % ("> " * level, line)

    return mark_safe(quoted.rstrip())
