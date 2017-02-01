from __future__ import unicode_literals

import os

from django.conf.urls import url

from djblets.feedview.views import view_feed


FEED_URL = "file://%s/testdata/sample.rss" % os.path.dirname(__file__)


urlpatterns = [
    url(r'^feed/$', view_feed, {
        'template_name': 'feedview/feed-page.html',
        'url': FEED_URL
    }),
    url(r'^feed-inline/$', view_feed, {
        'template_name': 'feedview/feed-inline.html',
        'url': FEED_URL
     }),
    url(r'^feed-error/$', view_feed, {
        'template_name':
        'feedview/feed-inline.html',
        'url': 'http://example.fake/dummy.rss'
    }),
]
