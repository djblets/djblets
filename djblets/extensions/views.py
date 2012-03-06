#
# views.py -- Views for the Admin UI.
#
# Copyright (c) 2010-2011  Beanbag, Inc.
# Copyright (c) 2008-2010  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render_to_response
from django.template.context import RequestContext


def _has_disabled_requirements(extension):
    """Returns whether an extension has one or more disabled requirements."""
    for requirement in extension.info.requirements:
        if not requirement.info.enabled:
            return True

    return False


@staff_member_required
def extension_list(request, extension_manager,
                   template_name='extensions/extension_list.html'):
    # Refresh the extension list.
    extension_manager.load()

    return render_to_response(template_name, RequestContext(request, {
        'extensions': [
            {
                'id': extension.id,
                'info': extension.info,
                'has_disabled_requirements':
                    _has_disabled_requirements(extension),
            }
            for extension in extension_manager.get_installed_extensions()
        ]
    }))


@staff_member_required
def configure_extension(request, ext_class, form_class, extension_manager,
                        template_name='extensions/configure_extension.html'):
    context = {}
    form = None
    extension = extension_manager.get_enabled_extension(ext_class.id)

    if extension:
        context['extension'] = extension
        context['enabled'] = True

        if extension.is_configurable:
            if request.method == 'POST':
                form = form_class(extension, request.POST, request.FILES)

                if form.is_valid():
                    form.save()
            else:
                form = form_class(extension)

            context['form'] = form
    else:
        context['enabled'] = False

    return render_to_response(template_name, RequestContext(request, context))
