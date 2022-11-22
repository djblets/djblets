import logging
import warnings

from django import template
from django.utils.html import format_html_join
from django.utils.inspect import func_accepts_kwargs
from django.utils.safestring import mark_safe
from pipeline.conf import settings as pipeline_settings
from pipeline.templatetags.pipeline import JavascriptNode, StylesheetNode

from djblets.extensions.hooks import TemplateHook
from djblets.extensions.manager import get_extension_managers


logger = logging.getLogger(__name__)
register = template.Library()


class ExtensionStaticMediaNodeMixin(object):
    """Mixin for extension-specific static media rendering logic.

    This is used to change the behavior for how static media in extensions
    are rendered, allowing us to work with both development setups and
    installed packages.
    """

    def render_compressed(self, *args, **kwargs):
        """Render an extension media bundle to HTML.

        If Pipeline is disabled (typically on development setups), this will
        attempt to render the compressed files, as normal. However, if that
        fails (due to the source files not being available in a package) or
        Pipeline is enabled (typically on a production setup), the bundle's
        output file will be rendered instead.

        Args:
            *args (tuple):
                Positional arguments to pass to the rendering function.

            **kwargs (dict):
                Keyword arguments to pass to the rendering function.

        Returns:
            django.utils.safestring.SafeText:
            The HTML for loading the static media.
        """
        rendered = ''

        if not pipeline_settings.PIPELINE_ENABLED:
            rendered = self.render_compressed_sources(*args, **kwargs)

        if not rendered:
            rendered = self.render_compressed_output(*args, **kwargs)

        return mark_safe(rendered)


class ExtensionJavascriptNode(ExtensionStaticMediaNodeMixin, JavascriptNode):
    """Template node for including extension-specific JavaScript.

    This will allow both extensions in development mode or installed via a
    package to be used on a page.
    """


class ExtensionStylesheetNode(ExtensionStaticMediaNodeMixin, StylesheetNode):
    """Template node for including extension-specific CSS.

    This will allow both extensions in development mode or installed via a
    package to be used on a page.
    """


@register.simple_tag(takes_context=True)
def template_hook_point(context, name):
    """Register a place where TemplateHooks can render to.

    Args:
        context (dict):
            The template rendering context.

        name (unicode):
            The name of the CSS bundle to render.

    Returns:
        django.utils.safetext.SafeText:
        The rendered HTML.
    """
    def _render_hooks():
        request = context['request']

        for hook in TemplateHook.by_name(name):
            try:
                if hook.applies_to(request):
                    context.push()

                    try:
                        yield (hook.render_to_string(request, context),)
                    except Exception as e:
                        logger.exception('Error rendering TemplateHook %r: %s',
                                         hook, e,
                                         extra={'request': request})

                    context.pop()

            except Exception as e:
                logger.exception('Error when calling applies_to for '
                                 'TemplateHook %r: %s',
                                 hook, e,
                                 extra={'request': request})

    return format_html_join('', '{0}', _render_hooks())


@register.simple_tag(takes_context=True)
def ext_static(context, extension, path):
    """Outputs the URL to the given static media file provided by an extension.

    This works like the {% static %} template tag, but takes an extension
    and generates a URL for the media file within the extension.

    This is meant to be used with
    :py:class:`djblets.extensions.staticfiles.ExtensionFinder`.
    """
    return extension.get_static_url(path)


def _render_bundle(context, node_cls, extension, name, bundle_type):
    try:
        return node_cls('"%s"' % extension.get_bundle_id(name)).render(context)
    except Exception:
        logger.error('Unable to render %s bundle "%s" for extension "%s" '
                     '(%s). The extension may not be installed correctly. '
                     'Try disabling and re-installing the extension, and '
                     'checking the log for related errors.',
                     bundle_type, name, extension.info.name, extension.id)
        return ''


def _render_css_bundle(context, extension, name):
    """Render a given CSS bundle.

    Args:
        context (dict):
            The template rendering context.

        extension (djblets.extensions.extension.Extension):
            The extension instance.

        name (unicode):
            The name of the CSS bundle to render.

    Returns:
        django.utils.safetext.SafeText:
        The rendered HTML.
    """
    return _render_bundle(context, ExtensionStylesheetNode, extension,
                          name, 'CSS')


def _render_js_bundle(context, extension, name):
    """Render a given JavaScript bundle.

    Args:
        context (dict):
            The template rendering context.

        extension (djblets.extensions.extension.Extension):
            The extension instance.

        name (unicode):
            The name of the JS bundle to render.

    Returns:
        django.utils.safetext.SafeText:
        The rendered HTML.
    """
    return _render_bundle(context, ExtensionJavascriptNode, extension,
                          name, 'JS')


@register.simple_tag(takes_context=True)
def ext_css_bundle(context, extension, name):
    """Return HTML to import an extension's CSS bundle.

    Args:
        context (dict):
            The template rendering context.

        extension (djblets.extensions.extension.Extension):
            The extension instance.

        name (unicode):
            The name of the CSS bundle to render.

    Returns:
        django.utils.safetext.SafeText:
        The rendered HTML.
    """
    return _render_css_bundle(context, extension, name)


@register.simple_tag(takes_context=True)
def ext_js_bundle(context, extension, name):
    """Return HTML to import an extension's JavaScript bundle.

    Args:
        context (dict):
            The template rendering context.

        extension (djblets.extensions.extension.Extension):
            The extension instance.

        name (unicode):
            The name of the CSS bundle to render.

    Returns:
        django.utils.safetext.SafeText:
        The rendered HTML.
    """
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
        tuple of (unicode or django.utils.safetext.SafeText):
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

            for bundle_name, bundle in bundles.items():
                if (bundle_name in default_bundles or
                    requested_url_name in bundle.get('apply_to', [])):
                    for include_bundle in bundle.get('include_bundles', []):
                        yield renderer(context, extension, include_bundle)

                    yield (renderer(context, extension, bundle_name),)

        break


@register.simple_tag(takes_context=True)
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
        django.utils.safestring.SafeText:
        The HTML used to include the bundled content.
    """
    return format_html_join('', '{0}\n', _get_extension_bundles(
        extension_manager_key=extension_manager_key,
        context=context,
        bundle_attr='css_bundles',
        default_bundles=default_bundles,
        renderer=_render_css_bundle))


@register.simple_tag(takes_context=True)
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
        django.utils.safestring.SafeText:
        The HTML used to include the bundled content.
    """
    return format_html_join('', '{0}\n', _get_extension_bundles(
        extension_manager_key=extension_manager_key,
        context=context,
        bundle_attr='js_bundles',
        default_bundles=default_bundles,
        renderer=_render_js_bundle))


@register.inclusion_tag('extensions/init_js_extensions.html',
                        takes_context=True)
def init_js_extensions(context, extension_manager_key):
    """Initializes all JavaScript extensions.

    Each extension's required JavaScript files will be loaded in the page,
    and their JavaScript-side Extension subclasses will be instantiated.
    """
    request = context['request']

    if not getattr(request, 'resolver_match', None):
        # In some cases, this can get called from within middleware (typically
        # if the middleware is bailing out of the usual call chain for some
        # reason). In that case, we don't have access to the resolver match,
        # but we also almost certainly don't want to be enabling JS extensions.
        return {}

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
