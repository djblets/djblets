from django.conf import settings
from django.conf.urls.defaults import patterns, include

urlpatterns = patterns('',
    (r'^%s' % settings.SITE_ROOT[1:], include(settings.SITE_ROOT_URLCONF)),
)
