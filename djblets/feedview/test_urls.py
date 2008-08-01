import os.path
from django.conf.urls.defaults import patterns, handler500


FEED_URL = "file://%s/testdata/sample.rss" % os.path.dirname(__file__)


urlpatterns = patterns('djblets.feedview.views',
    ('^feed/$', 'view_feed',
     {'template_name': 'feedview/feed-page.html',
      'url': FEED_URL}),
    ('^feed-inline/$', 'view_feed',
     {'template_name': 'feedview/feed-inline.html',
      'url': FEED_URL}),
    ('^feed-error/$', 'view_feed',
     {'template_name': 'feedview/feed-inline.html',
      'url': "http://example.fake/dummy.rss"}),
)
