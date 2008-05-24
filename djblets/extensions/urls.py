from django.conf import settings
from django.conf.urls.defaults import patterns, include, url, \
                                      handler404, handler500


urlpatterns = patterns('djblets.extensions.views',
    (r'^$', 'extension_list'),

    url(r'^(?P<ext_class>[A-Za-z0-9_.]+)/enable/$', 'set_extension_enabled',
        {'enabled': True},
        name="enable_extension"),
    url(r'^(?P<ext_class>[A-Za-z0-9_.]+)/disable/$', 'set_extension_enabled',
        {'enabled': False},
        name="disable_extension"),
)
