from django.conf.urls.defaults import patterns, url, include


urlpatterns = patterns('djblets.extensions.tests',
    url(r'^$', 'test_view_method', name="test-url-name"),
    url(r'^admin/extensions/', include('djblets.extensions.urls')),
)
