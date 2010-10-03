from django.conf.urls.defaults import patterns, url


urlpatterns = patterns('djblets.extensions.tests',
    url(r'^$', 'test_view_method', name="test-url-name")
)
