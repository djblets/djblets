"""Decorative template tags."""

from django import template
from django.template.loader import render_to_string

from djblets.util.decorators import blocktag


register = template.Library()


@register.tag
@blocktag
def box(context, nodelist, classname=None):
    """
    Displays a box container around content, with an optional class name.
    """
    return render_to_string('deco/box.html', {
        'classname': classname or "",
        'content': nodelist.render(context)
    })


@register.tag
@blocktag
def errorbox(context, nodelist, box_id=None):
    """
    Displays an error box around content, with an optional ID.
    """
    return render_to_string('deco/errorbox.html', {
        'box_id': box_id or "",
        'content': nodelist.render(context)
    })
