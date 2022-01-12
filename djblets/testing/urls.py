from __future__ import unicode_literals

from django.conf.urls import include, url
from django.http import HttpResponse


def dummy_view(request):
    return HttpResponse('')


urlpatterns = [
    url(r'^$', dummy_view, name='test-url-name'),
    url(r'^admin/extensions/', include('djblets.extensions.urls')),
    url(r'^auth/', include('djblets.auth.urls')),
]
