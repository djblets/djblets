from django import template

from djblets.extensions.hooks import TemplateHook
from djblets.util.decorators import basictag


register = template.Library()


@register.tag
@basictag(takes_context=True)
def template_hook_point(context, name):
    """
    Registers a template hook point that TemplateHook instances can
    attach to.
    """
    s = ""
    for hook in TemplateHook.by_name(name):
        if hook.applies_to(context):
            s += hook.render_to_string(context.get('request', None), context)

    return s
