from django import template
from django.template.loader import render_to_string

from djblets.extensions.base import ExtensionManager
from djblets.extensions.hooks import TemplateHook
from djblets.util.decorators import basictag, blocktag


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
        s += render_to_string(hook.template_name, context)

    return s


@register.filter
def has_disabled_requirements(extension):
    """
    Returns whether or not an extension has one or more disabled
    requirements.
    """
    for requirement in extension.info.requirements:
        if not requirement.info.enabled:
            return True

    return False
