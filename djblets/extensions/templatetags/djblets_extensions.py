from django import template
from django.contrib.staticfiles.templatetags.staticfiles import static

from djblets.extensions.hooks import TemplateHook
from djblets.extensions.manager import get_extension_managers
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


@register.tag
@basictag(takes_context=True)
def ext_static(context, extension, path):
    """Outputs the URL to the given static media file provided by an extension.

    This works like the {% static %} template tag, but takes an extension
    and generates a URL for the media file within the extension.

    This is meant to be used with
    :py:class:`djblets.extensions.staticfiles.ExtensionFinder`.
    """
    return static('ext/%s/%s' % (extension.id, path))


@register.inclusion_tag('extensions/init_js_extensions.html',
                        takes_context=True)
def init_js_extensions(context, key):
    """Initializes all JavaScript extensions.

    Each extension's required JavaScript files will be loaded in the page,
    and their JavaScript-side Extension subclasses will be instantiated.
    """
    for manager in get_extension_managers():
        if manager.key == key:
            return {
                'extension_manager': manager,
                'request': context['request'],
                'MEDIA_URL': context['MEDIA_URL'],
            }

    return {}
