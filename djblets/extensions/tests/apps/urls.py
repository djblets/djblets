from __future__ import unicode_literals

from django.urls import path


def test_url(request):
    pass


urlpatterns = [
    path('', test_url),
]
