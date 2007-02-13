from django.conf.urls.defaults import *
from cia.apps.images import views
from django.conf import settings
import os

urlpatterns = patterns('',
    (r'^upload/$', views.upload),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^db/(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': os.path.join(settings.CIA_DATA_PATH, "db/images"),
            'show_indexes': True,
        })
    )
