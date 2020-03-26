from __future__ import unicode_literals

from django.conf.urls import url

from djblets.auth.views import register

urlpatterns = [
    url(r'register/', register, kwargs={
        'next_page': 'test',
    }, name='register')
]
