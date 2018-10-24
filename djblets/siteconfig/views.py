"""Views for working with site configurations."""

from __future__ import unicode_literals

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseRedirect
from django.template.context import RequestContext
from django.views.decorators.csrf import csrf_protect

from djblets.siteconfig.forms import SiteSettingsForm
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.compat.django.shortcuts import render


@csrf_protect
@staff_member_required
def site_settings(request,
                  form_class=SiteSettingsForm,
                  template_name='siteconfig/settings.html',
                  extra_context={}):
    """A view for customizing the site configuration's settings.

    This will make use of the provided form class and template, handling
    loading and saving any site configuration settings.

    Args:
        request (django.http.HttpRequest):
            The HTTP request for the view.

        form_class (type, optional):
            The form class to use for editing the settings. This should be
            either :py:class:`~djblets.siteconfig.forms.SiteSettingsForm` or
            a subclass of it.

        template_name (unicode, optional):
            The template to render for the view.

        extra_context (dict, optional):
            Extra context variables to pass to the template.

    Returns:
        django.http.HttpResponse:
        The response containing the page.
    """
    siteconfig = SiteConfiguration.objects.get_current()

    if request.method == 'POST':
        form = form_class(siteconfig, request.POST, request.FILES,
                          request=request)

        if form.is_valid():
            form.save()
            return HttpResponseRedirect('.?saved=1')
    else:
        form = form_class(siteconfig, request=request)

    context = {
        'form': form,
        'saved': request.GET.get('saved', 0)
    }
    context.update(extra_context)

    return render(request, template_name, context)
