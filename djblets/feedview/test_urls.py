import os

from django.urls import path

from djblets.feedview.views import view_feed


FEED_URL = "file://%s/testdata/sample.rss" % os.path.dirname(__file__)


urlpatterns = [
    path('feed/', view_feed, kwargs={
        'template_name': 'feedview/feed-page.html',
        'url': FEED_URL,
    }),
    path('feed-inline/', view_feed, kwargs={
        'template_name': 'feedview/feed-inline.html',
        'url': FEED_URL,
    }),
    path('feed-error/', view_feed, kwargs={
        'template_name': 'feedview/feed-inline.html',
        'url': 'http://example.fake/dummy.rss',
    }),
]
