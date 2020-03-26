from __future__ import unicode_literals

from django.conf.urls import include, url


def dummy_view(request):
    pass


urlpatterns = [
    url(r'^$', dummy_view, name='test-url-name'),
    url(r'^admin/extensions/', include('djblets.extensions.urls')),
    url(r'^auth/', include('djblets.auth.urls')),
]
