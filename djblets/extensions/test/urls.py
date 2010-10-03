from django.conf.urls.defaults import patterns


urlpatterns = patterns('djblets.extensions.views',
    (r'^$', 'test_url')
)
