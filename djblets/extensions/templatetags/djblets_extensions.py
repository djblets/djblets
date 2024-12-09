"""Template tags for loading extension static media."""

from __future__ import annotations

import logging
from typing import Any, Callable, Iterator, TYPE_CHECKING, Union

from django.template import Library, RequestContext
from django.utils.html import format_html_join
from django.utils.safestring import mark_safe
from pipeline.conf import settings as pipeline_settings
from pipeline.templatetags.pipeline import JavascriptNode, StylesheetNode
from typing_extensions import TypeAlias

from djblets.extensions.hooks import TemplateHook
from djblets.extensions.manager import get_extension_managers

if TYPE_CHECKING:
    from django.http import HttpRequest
    from django.template import Context
    from django.utils.safestring import SafeString
    from pipeline.templatetags.pipeline import PipelineMixin

    from djblets.extensions.extension import (BaseStaticBundleConfig,
                                              Extension,
                                              JSExtension)

    _RenderBundleFunc: TypeAlias = Callable[[Context, Extension, str],
                                            SafeString]
    _ExtensionStaticMediaNodeMixinBase = PipelineMixin
else:
    _ExtensionStaticMediaNodeMixinBase = object


logger = logging.getLogger(__name__)
register = Library()


class ExtensionStaticMediaNodeMixin(_ExtensionStaticMediaNodeMixinBase):
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
def template_hook_point(
    context: Union[Context, RequestContext],
    name: str,
) -> SafeString:
    """Register a place where TemplateHooks can render to.

    Args:
        context (dict):
            The template rendering context.

        name (str):
            The name of the CSS bundle to render.

    Returns:
        django.utils.safetext.SafeString:
        The rendered HTML.
    """
    def _render_hooks() -> Iterator[tuple[Union[str, SafeString]]]:
        request: HttpRequest

        if isinstance(context, RequestContext):
            request = context.request
        else:
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
def ext_static(
    context: Context,
    extension: Extension,
    path: str,
) -> str:
    """Return the URL to the given static media file provided by an extension.

    This works like the ``{% static %}`` template tag, but takes an extension
    and generates a URL for the media file within the extension.

    This is meant to be used with
    :py:class:`djblets.extensions.staticfiles.ExtensionFinder`.

    Args:
        context (django.template.Context):
            The current template context.

        extension (djblets.extensions.extension.Extension):
            The extension that owns the static media file.

        path (str):
            The relative path to the static media file.

    Returns:
        str:
        The resulting URL to the static media file.
    """
    return extension.get_static_url(path)


def _render_bundle(
    *,
    context: Context,
    node_cls: type[Union[ExtensionJavascriptNode, ExtensionStylesheetNode]],
    extension: Extension,
    name: str,
    bundle_type: str,
) -> SafeString:
    """Render an extension bundle, catching and logging any errors.

    This will attempt to render the named bundle for the given extension.
    The result will be HTML that loads in the bundle, compiling it first if
    necessary.

    If there's any error during this process, the error will be logged and
    the bundle will be skipped.

    Args:
        context (django.template.Context):
            The current template context.

        node_cls (type):
            The template tag node used to render the bundle.

        extension (djblets.extensions.extension.Extension):
            The extension that owns the bundle.

        name (str):
            The name of the bundle to render.

        bundle_type (str):
            The type of bundle.

            This is only used for logging purposes when indicating the type
            of bundle that failed.

    Returns:
        django.utils.safestring.SafeString:
        The HTML used to load the bundle.
    """
    try:
        return node_cls('"%s"' % extension.get_bundle_id(name)).render(context)
    except Exception:
        logger.exception('Unable to render %s bundle "%s" for extension "%s" '
                         '(%s). The extension may not be installed correctly. '
                         'Try disabling and re-installing the extension, and '
                         'checking the log for related errors.',
                         bundle_type, name, extension.info.name, extension.id,
                         extra={'request': context['request']})

        return mark_safe('')


def _render_css_bundle(
    context: Context,
    extension: Extension,
    name: str,
) -> SafeString:
    """Render a given CSS bundle.

    Args:
        context (django.template.Context):
            The current template context.

        extension (djblets.extensions.extension.Extension):
            The extension that owns the bundle.

        name (str):
            The name of the CSS bundle to render.

    Returns:
        django.utils.safestring.SafeString:
        The rendered HTML.
    """
    return _render_bundle(context=context,
                          node_cls=ExtensionStylesheetNode,
                          extension=extension,
                          name=name,
                          bundle_type='CSS')


def _render_js_bundle(
    context: Context,
    extension: Extension,
    name: str,
) -> SafeString:
    """Render a given JavaScript bundle.

    Args:
        context (django.template.Context):
            The current template context.

        extension (djblets.extensions.extension.Extension):
            The extension instance.

        name (str):
            The name of the JavaScript bundle to render.

    Returns:
        django.utils.safestring.SafeString:
        The rendered HTML.
    """
    return _render_bundle(context=context,
                          node_cls=ExtensionJavascriptNode,
                          extension=extension,
                          name=name,
                          bundle_type='JavaScript')


@register.simple_tag(takes_context=True)
def ext_css_bundle(
    context: Context,
    extension: Extension,
    name: str,
) -> SafeString:
    """Return HTML to import an extension's CSS bundle.

    Args:
        context (django.template.Context):
            The current template context.

        extension (djblets.extensions.extension.Extension):
            The extension instance.

        name (str):
            The name of the CSS bundle to render.

    Returns:
        django.utils.safestring.SafeString:
        The rendered HTML.
    """
    return _render_css_bundle(context=context,
                              extension=extension,
                              name=name)


@register.simple_tag(takes_context=True)
def ext_js_bundle(
    context: Context,
    extension: Extension,
    name: str,
) -> SafeString:
    """Return HTML to import an extension's JavaScript bundle.

    Args:
        context (django.template.Context):
            The current template context.

        extension (djblets.extensions.extension.Extension):
            The extension instance.

        name (unicode):
            The name of the CSS bundle to render.

    Returns:
        django.utils.safestring.SafeString:
        The rendered HTML.
    """
    return _render_js_bundle(context=context,
                             extension=extension,
                             name=name)


def _get_extension_bundles(
    *,
    extension_manager_key: str,
    context: Context,
    bundle_attr: str,
    default_bundles: str,
    renderer: _RenderBundleFunc,
) -> Iterator[tuple[SafeString]]:
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
        extension_manager_key (str):
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
        tuple of django.utils.safetext.SafeText:
        A 1-tuple of HTML used to include the bundled content.
    """
    request = context['request']

    if not getattr(request, 'resolver_match', None):
        return

    requested_url_name = request.resolver_match.url_name
    default_bundles_set = set(default_bundles.split(','))

    for manager in get_extension_managers():
        if manager.key != extension_manager_key:
            continue

        for extension in manager.get_enabled_extensions():
            try:
                bundles: dict[str, BaseStaticBundleConfig] = \
                    getattr(extension, bundle_attr)
            except AttributeError:
                logger.error(
                    'Could not access bundle attribute "%s" on extension '
                    '"%s". Skipping this bundle.',
                    bundle_attr, extension.id,
                    extra={'request': request})
                continue

            for bundle_name, bundle in bundles.items():
                if (bundle_name in default_bundles_set or
                    requested_url_name in bundle.get('apply_to', [])):

                    for include_bundle in bundle.get('include_bundles', []):
                        yield (renderer(context, extension, include_bundle),)

                    yield (renderer(context, extension, bundle_name),)

        break


@register.simple_tag(takes_context=True)
def load_extensions_css(
    context: Context,
    extension_manager_key: str,
    default_bundles: str = 'default',
) -> SafeString:
    """Load all CSS bundles that can be rendered on the current page.

    This will include all "default" bundles and any with an ``apply_to``
    containing a URL name matching the current page.

    Args:
        context (django.template.Context):
            The template context.

        extension_manager_key (str):
            The key for the extension manager for these bundles.

        default_bundles (str):
            A string containing a comma-separated list of bundles to always
            include. Defaults to ``"default"``.

    Returns:
        django.utils.safestring.SafeString:
        The HTML used to include the bundled content.
    """
    return format_html_join('', '{0}\n', _get_extension_bundles(
        extension_manager_key=extension_manager_key,
        context=context,
        bundle_attr='css_bundles',
        default_bundles=default_bundles,
        renderer=_render_css_bundle))


@register.simple_tag(takes_context=True)
def load_extensions_js(
    context: Context,
    extension_manager_key: str,
    default_bundles: str = 'default',
) -> SafeString:
    """Load all JavaScript bundles that can be rendered on the current page.

    This will include all "default" bundles and any with an ``apply_to``
    containing a URL name matching the current page.

    Args:
        context (django.template.Context):
            The template context.

        extension_manager_key (str):
            The key for the extension manager for these bundles.

        default_bundles (str):
            A string containing a comma-separated list of bundles to always
            include. Defaults to ``"default"``.

    Returns:
        django.utils.safestring.SafeString:
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
def init_js_extensions(
    context: Context,
    extension_manager_key: str,
) -> dict[str, Any]:
    """Initializes all JavaScript extensions.

    Each extension's required JavaScript files will be loaded in the page,
    and their JavaScript-side Extension subclasses will be instantiated.

    Args:
        context (django.template.Context):
            The current template context.

        extension_manager_key (str):
            The key for the extension manager for these bundles.

    Returns:
        dict:
        Context variables to include for the
        :file:`extensions/init_js_extensions.html` template.
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
            js_extensions: list[JSExtension] = []

            for extension in manager.get_enabled_extensions():
                for js_extension_cls in extension.js_extensions:
                    js_extension = js_extension_cls(extension)

                    if js_extension.applies_to(url_name):
                        js_extensions.append(js_extension)

            js_extension_items: list[dict[str, Any]] = []

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
