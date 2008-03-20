from django.conf import settings
from django.conf.urls.defaults import patterns, include, handler404, handler500


urlpatterns = patterns('djblets.extensions.views',
    (r'^$', 'extension_list'),
    (r'^(?P<ext_class>([A-Za-z0-9_.])+)/enable/$', 'set_extension_enabled',
     {'enabled': True}),
    (r'^(?P<ext_class>([A-Za-z0-9_.])+)/disable/$', 'set_extension_enabled',
     {'enabled': False}),
)
