from __future__ import unicode_literals

from django.conf.urls import url


def test_url(request):
    pass


urlpatterns = [
    url(r'^$', test_url),
]
