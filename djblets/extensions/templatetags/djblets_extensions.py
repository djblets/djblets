from __future__ import unicode_literals

from django import template
from django.contrib.staticfiles.templatetags.staticfiles import static
from pipeline.templatetags.compressed import (CompressedCSSNode,
                                              CompressedJSNode)

from djblets.extensions.hooks import TemplateHook
from djblets.extensions.manager import get_extension_managers
from djblets.util.compat import six
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


def _render_css_bundle(context, extension, name):
    return CompressedCSSNode(
        '"%s"' % extension.get_bundle_id(name)).render(context)


def _render_js_bundle(context, extension, name):
    return CompressedJSNode(
        '"%s"' % extension.get_bundle_id(name)).render(context)


@register.tag
@basictag(takes_context=True)
def ext_css_bundle(context, extension, name):
    """Outputs HTML to import an extension's CSS bundle."""
    return _render_css_bundle(context, extension, name)


@register.tag
@basictag(takes_context=True)
def ext_js_bundle(context, extension, name):
    """Outputs HTML to import an extension's JavaScript bundle."""
    return _render_js_bundle(context, extension, name)


def _get_extension_bundles(extension_manager_key, context, bundle_attr,
                           renderer):
    """Returns media bundles that can be rendered on the current page.

    This will look through all enabled extensions and find any with static
    media bundles that should be included on the current page, as indicated
    by the context.

    All bundles marked "default" will be included, as will any with an
    ``apply_to`` field containing a URL name matching the current page.
    """
    request = context['request']

    for manager in get_extension_managers():
        if manager.key != extension_manager_key:
            continue

        for extension in manager.get_enabled_extensions():
            bundles = getattr(extension, bundle_attr, {})

            for bundle_name, bundle in six.iteritems(bundles):
                if (bundle_name == 'default' or
                    requested_url_name in bundles.get('apply_to', [])):
                    yield renderer(context, extension, bundle_name)

        break


@register.tag
@basictag(takes_context=True)
def load_extensions_css(context, extension_manager_key):
    """Loads all CSS bundles that can be rendered on the current page.

    This will include all "default" bundles and any with an ``apply_to``
    containing a URL name matching the current page.
    """
    return ''.join(_get_extension_bundles(
        extension_manager_key, context, 'css_bundles', _render_css_bundle))


@register.tag
@basictag(takes_context=True)
def load_extensions_js(context, extension_manager_key):
    """Loads all JavaScript bundles that can be rendered on the current page.

    This will include all "default" bundles and any with an ``apply_to``
    containing a URL name matching the current page.
    """
    return ''.join(_get_extension_bundles(
        extension_manager_key, context, 'js_bundles', _render_js_bundle))


@register.inclusion_tag('extensions/init_js_extensions.html',
                        takes_context=True)
def init_js_extensions(context, extension_manager_key):
    """Initializes all JavaScript extensions.

    Each extension's required JavaScript files will be loaded in the page,
    and their JavaScript-side Extension subclasses will be instantiated.
    """
    for manager in get_extension_managers():
        if manager.key == extension_manager_key:
            return {
                'extensions': [
                    extension
                    for extension in manager.get_enabled_extensions()
                    if extension.js_model_class
                ],
            }

    return {}
