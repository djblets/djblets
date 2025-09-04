"""Views for extensions (used in the admin UI)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.views.decorators.csrf import csrf_protect
from housekeeping import deprecate_non_keyword_only_args

from djblets.deprecation import RemovedInDjblets70Warning

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any

    from django.http import HttpRequest, HttpResponse

    from djblets.extensions.extension import Extension
    from djblets.extensions.forms import SettingsForm
    from djblets.extensions.manager import ExtensionManager


@csrf_protect
@staff_member_required
@deprecate_non_keyword_only_args(RemovedInDjblets70Warning)
def extension_list(
    request: HttpRequest,
    *,
    extension_manager: ExtensionManager,
    template_name: str = 'extensions/admin/extension_list.html',
    extra_context: (Mapping[str, Any] | None) = None,
) -> HttpResponse:
    """A view for listing available extensions.

    This will load the list of extensions and render them in the provided
    template.

    It will also handle certain actions, such as forcing a reload of available
    extensions. The actions are not considered public API, and are internal
    to the page.

    Version Changed:
        5.3:
        * Added the ``extra_context`` argument.
        * All arguments except for ``request`` must be included as
          keyword-only arguments. This will be enforced in Djblets 7.

    Args:
        request (django.http.HttpRequest):
            The HTTP request from the client.

        extension_manager (djblets.extensions.manager.ExtensionManager):
            The extension manager managing the extensions shown on the page.

        template_name (str, optional):
            The name of the template to render.

        extra_context (dict, optional):
            Extra context to provide for the template.

            Version Added:
                5.3

    Returns:
        django.http.HttpResponse:
        The HTTP response to send to the client.

    Raises:
        django.http.Http404:
            The extension does not support configuration.
    """
    if request.method == 'POST':
        if 'full-reload' in request.POST:
            extension_manager.load(full_reload=True)

        return HttpResponseRedirect('.')
    else:
        # Refresh the extension list.
        extension_manager.load()

        return render(request, template_name, extra_context)


@csrf_protect
@staff_member_required
@deprecate_non_keyword_only_args(RemovedInDjblets70Warning)
def configure_extension(
    request: HttpRequest,
    *,
    ext_class: type[Extension],
    form_class: type[SettingsForm],
    extension_manager: ExtensionManager,
    template_name: str = 'extensions/configure_extension.html',
    extra_context: (Mapping[str, Any] | None) = None,
) -> HttpResponse:
    """A view for configuring an extension.

    This can be used to provide a configuration page for an extension. The
    extension can include this in its list of URL patterns, or it can wrap
    it in another function.

    The view will take care of fetching the appropriate extension, check if
    it's configurable, render it, and handle results.

    Version Changed:
        5.3:
        * Added the ``extra_context`` argument.
        * All arguments except for ``request`` must be included as
          keyword-only arguments. This will be enforced in Djblets 7.

    Args:
        request (django.http.HttpRequest):
            The HTTP request from the client.

        ext_class (type):
            The class for the extension.

        form_class (type):
            The class for the settings form.

        extension_manager (djblets.extensions.manager.ExtensionManager):
            The extension manager that manages the extension.

        template_name (str, optional):
            The name of the template to render.

        extra_context (dict, optional):
            Extra context to provide for the template.

            Version Added:
                5.3

    Returns:
        django.http.HttpResponse:
        The HTTP response to send to the client.

    Raises:
        django.http.Http404:
            The extension does not support configuration.
    """
    extension = extension_manager.get_enabled_extension(ext_class.id)

    if not extension or not extension.is_configurable:
        raise Http404

    if request.method == 'POST':
        form = form_class(extension, request.POST, request.FILES)

        if form.is_valid():
            form.save()

            return HttpResponseRedirect(f'{request.path}?saved=1')
    else:
        form = form_class(extension)

    return render(request, template_name, {
        'extension': extension,
        'form': form,
        'saved': request.GET.get('saved', 0),
        **(extra_context or {}),
    })
