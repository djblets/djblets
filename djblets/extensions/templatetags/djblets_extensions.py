from __future__ import unicode_literals

import inspect
import logging
import warnings

from django import template
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.utils import six
from pipeline.templatetags.compressed import (CompressedCSSNode,
                                              CompressedJSNode)

from djblets.extensions.hooks import TemplateHook
from djblets.extensions.manager import get_extension_managers
from djblets.util.decorators import basictag


logger = logging.getLogger(__name__)
register = template.Library()


@register.tag
@basictag(takes_context=True)
def template_hook_point(context, name):
    """Registers a place where TemplateHooks can render to."""
    def _render_hooks():
        request = context['request']

        for hook in TemplateHook.by_name(name):
            try:
                if hook.applies_to(request):
                    context.push()

                    try:
                        yield hook.render_to_string(request, context)
                    except Exception as e:
                        logger.exception('Error rendering TemplateHook %r: %s',
                                         hook, e)

                    context.pop()

            except Exception as e:
                logger.exception('Error when calling applies_to for '
                                 'TemplateHook %r: %s',
                                 hook, e)

    return ''.join(_render_hooks())


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


def _render_bundle(context, node_cls, extension, name, bundle_type):
    try:
        return node_cls('"%s"' % extension.get_bundle_id(name)).render(context)
    except Exception as e:
        logger.critical("Unable to load %s bundle '%s' for "
                        "extension '%s' (%s): %s",
                        bundle_type, name, extension.info.name,
                        extension.id, e, exc_info=1)
        return ''


def _render_css_bundle(context, extension, name):
    return _render_bundle(context, CompressedCSSNode, extension, name, 'CSS')


def _render_js_bundle(context, extension, name):
    return _render_bundle(context, CompressedJSNode, extension, name,
                          'JavaScript')


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
                           default_bundles, renderer):
    """Yield media bundles that can be rendered on the current page.

    This will look through all enabled extensions and find any with static
    media bundles that should be included on the current page, as indicated
    by the context.

    All bundles marked "default" will be included, as will any with an
    ``apply_to`` field containing a URL name matching the current page.

    If a bundle has an ``include_bundles`` key, the referenced bundles will
    also be outputted. Note that this does not check for duplicates, and is
    not recursive.

    Args:
        extension_manager_key (unicode):
            The key for the extension manager for these bundles.

        context (django.template.Context):
            The template context.

        bundle_attr (unicode):
            The attribute name for the bundle on the extension class.

        default_bundles (unicode):
            A string containing a comma-separated list of bundles to always
            include.

        renderer (callable):
            The renderer function to call for each applicable bundle.

    Yields:
        unicode:
        The HTML used to include the bundled content.
    """
    request = context['request']

    if not getattr(request, 'resolver_match', None):
        return

    requested_url_name = request.resolver_match.url_name
    default_bundles = set(default_bundles.split(','))

    for manager in get_extension_managers():
        if manager.key != extension_manager_key:
            continue

        for extension in manager.get_enabled_extensions():
            bundles = getattr(extension, bundle_attr, {})

            for bundle_name, bundle in six.iteritems(bundles):
                if (bundle_name in default_bundles or
                    requested_url_name in bundle.get('apply_to', [])):
                    for include_bundle in bundle.get('include_bundles', []):
                        yield renderer(context, extension, include_bundle)

                    yield renderer(context, extension, bundle_name)

        break


@register.tag
@basictag(takes_context=True)
def load_extensions_css(context, extension_manager_key,
                        default_bundles='default'):
    """Load all CSS bundles that can be rendered on the current page.

    This will include all "default" bundles and any with an ``apply_to``
    containing a URL name matching the current page.

    Args:
        context (django.template.Context):
            The template context.

        extension_manager_key (unicode):
            The key for the extension manager for these bundles.

        default_bundles (unicode):
            A string containing a comma-separated list of bundles to always
            include. Defaults to ``"default"``.

    Returns:
        unicode:
        The HTML used to include the bundled content.
    """
    return ''.join(_get_extension_bundles(
        extension_manager_key, context, 'css_bundles', default_bundles,
        _render_css_bundle))


@register.tag
@basictag(takes_context=True)
def load_extensions_js(context, extension_manager_key,
                       default_bundles='default'):
    """Load all JavaScript bundles that can be rendered on the current page.

    This will include all "default" bundles and any with an ``apply_to``
    containing a URL name matching the current page.

    Args:
        context (django.template.Context):
            The template context.

        extension_manager_key (unicode):
            The key for the extension manager for these bundles.

        default_bundles (unicode):
            A string containing a comma-separated list of bundles to always
            include. Defaults to ``"default"``.

    Returns:
        unicode:
        The HTML used to include the bundled content.
    """
    return ''.join(_get_extension_bundles(
        extension_manager_key, context, 'js_bundles', default_bundles,
        _render_js_bundle))


@register.inclusion_tag('extensions/init_js_extensions.html',
                        takes_context=True)
def init_js_extensions(context, extension_manager_key):
    """Initializes all JavaScript extensions.

    Each extension's required JavaScript files will be loaded in the page,
    and their JavaScript-side Extension subclasses will be instantiated.
    """
    request = context['request']
    url_name = request.resolver_match.url_name

    for manager in get_extension_managers():
        if manager.key == extension_manager_key:
            js_extensions = []

            for extension in manager.get_enabled_extensions():
                for js_extension_cls in extension.js_extensions:
                    js_extension = js_extension_cls(extension)

                    if js_extension.applies_to(url_name):
                        js_extensions.append(js_extension)

            js_extension_items = []

            for js_extension in js_extensions:
                arg_spec = inspect.getargspec(js_extension.get_model_data)

                if arg_spec.keywords is None:
                    warnings.warn(
                        '%s.get_model_data will need to take keyword '
                        'arguments. The old function signature is deprecated.'
                        % js_extension_cls.__name__)

                    model_data = js_extension.get_model_data()
                else:
                    model_data = js_extension.get_model_data(request=request)

                js_extension_items.append({
                    'js_extension': js_extension,
                    'model_data': model_data,
                })

            return {
                'url_name': url_name,
                'js_extension_items': js_extension_items,
            }

    return {}
