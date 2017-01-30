from __future__ import unicode_literals

from django.conf.urls import include, url

from djblets.extensions.tests import test_view_method


urlpatterns = [
    url(r'^$', test_view_method, name='test-url-name'),
    url(r'^admin/extensions/', include('djblets.extensions.urls')),
]
