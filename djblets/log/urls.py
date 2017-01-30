from __future__ import unicode_literals

from django.conf.urls import url

from djblets.log.views import server_log


urlpatterns = [
    url(r'^server/$', server_log, name='server-log'),
]
