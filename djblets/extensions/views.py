"""Views for extensions (used in the admin UI)."""

from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.views.decorators.csrf import csrf_protect


@csrf_protect
@staff_member_required
def extension_list(request, extension_manager,
                   template_name='extensions/admin/extension_list.html'):
    if request.method == 'POST':
        if 'full-reload' in request.POST:
            extension_manager.load(full_reload=True)

        return HttpResponseRedirect('.')
    else:
        # Refresh the extension list.
        extension_manager.load()

        return render(request, template_name)


@csrf_protect
@staff_member_required
def configure_extension(request, ext_class, form_class, extension_manager,
                        template_name='extensions/configure_extension.html'):
    extension = extension_manager.get_enabled_extension(ext_class.id)

    if not extension or not extension.is_configurable:
        raise Http404

    if request.method == 'POST':
        form = form_class(extension, request.POST, request.FILES)

        if form.is_valid():
            form.save()

            return HttpResponseRedirect(request.path + '?saved=1')
    else:
        form = form_class(extension)

    return render(request, template_name, {
        'extension': extension,
        'form': form,
        'saved': request.GET.get('saved', 0),
    })
