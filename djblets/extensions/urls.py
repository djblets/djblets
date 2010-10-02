from django.conf import settings
from django.conf.urls.defaults import patterns, include, url, \
                                      handler404, handler500


urlpatterns = patterns('djblets.extensions.views',
    (r'^$', 'extension_list')
)
