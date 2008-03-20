from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.context import RequestContext

from djblets.extensions.base import ExtensionManager


@staff_member_required
def extension_list(request, extension_manager,
                   template_name='extensions/extension_list.html'):
    return render_to_response(template_name, RequestContext(request, {
        'extensions': extension_manager.get_installed_extensions(),
    }))


@staff_member_required
def set_extension_enabled(request, ext_class, enabled, extension_manager):
    if enabled:
        extension_manager.enable_extension(ext_class)
    else:
        extension_manager.disable_extension(ext_class)

    return HttpResponseRedirect("../../")
