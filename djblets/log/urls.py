from django.urls import path

from djblets.log.views import server_log


urlpatterns = [
    path('server/', server_log, name='server-log'),
]
