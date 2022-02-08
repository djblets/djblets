"""Unit tests for classes in djblets.feedview."""

from django.test.utils import override_settings

from djblets.testing.testcases import TestCase


@override_settings(ROOT_URLCONF='djblets.feedview.test_urls')
class FeedViewTests(TestCase):
    def testViewFeedPage(self):
        """Testing view_feed with the feed-page.html template"""
        response = self.client.get('/feed/')
        self.assertContains(response, "Django 1.0 alpha released", 1)
        self.assertContains(response, "Introducing Review Board News", 1)

    def testViewFeedInline(self):
        """Testing view_feed with the feed-inline.html template"""
        response = self.client.get('/feed-inline/')
        self.assertContains(response, "Django 1.0 alpha released", 1)
        self.assertContains(response, "Introducing Review Board News", 1)

    def testViewFeedError(self):
        """Testing view_feed with a URL error"""
        response = self.client.get('/feed-error/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('error' in response.context)
