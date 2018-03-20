"""Unit tests for ETagViewMixin."""

from __future__ import unicode_literals

from django.http import HttpResponse, HttpResponseNotModified
from django.test.client import RequestFactory
from django.views.generic.base import View

from djblets.testing.testcases import TestCase
from djblets.util.http import encode_etag
from djblets.views.generic.etag import ETagViewMixin


class ETagViewMixinTests(TestCase):
    """Unit tests for ETagViewMixin."""

    def test_get_with_matching_etag(self):
        """Testing ETagViewMixin.get with matching ETag"""
        self._test_with_matching_etag('GET')

    def test_get_without_matching_etag(self):
        """Testing ETagViewMixin.get without matching ETag"""
        self._test_without_matching_etag('GET')

    def test_head_with_matching_etag(self):
        """Testing ETagViewMixin.head with matching ETag"""
        self._test_with_matching_etag('HEAD')

    def test_head_without_matching_etag(self):
        """Testing ETagViewMixin.head without matching ETag"""
        self._test_without_matching_etag('HEAD')

    def test_post_ignores_etags(self):
        """Testing ETagViewMixin.post ignores ETags"""
        self._test_ignore_etag('POST')

    def test_put_ignores_etags(self):
        """Testing ETagViewMixin.put ignores ETags"""
        self._test_ignore_etag('PUT')

    def test_patch_ignores_etags(self):
        """Testing ETagViewMixin.patch ignores ETags"""
        self._test_ignore_etag('PATCH')

    def test_delete_ignores_etags(self):
        """Testing ETagViewMixin.delete ignores ETags"""
        self._test_ignore_etag('DELETE')

    def _test_with_matching_etag(self, method):
        class MyView(ETagViewMixin, View):
            def get_etag_data(self, *args, **kwargs):
                return 'test123'

        setattr(MyView, method.lower(), lambda *args, **kwargs: HttpResponse())

        view = MyView.as_view()
        request = RequestFactory().request(REQUEST_METHOD='HEAD')
        request.META['HTTP_IF_NONE_MATCH'] = encode_etag('test123')

        response = view(request)
        self.assertIsInstance(response, HttpResponseNotModified)
        self.assertFalse(response.has_header('ETag'))

    def _test_without_matching_etag(self, method):
        class MyView(ETagViewMixin, View):
            def get_etag_data(self, *args, **kwargs):
                return 'test123'

            def head(self, *args, **kwargs):
                return HttpResponse()

        setattr(MyView, method.lower(), lambda *args, **kwargs: HttpResponse())

        view = MyView.as_view()
        request = RequestFactory().request(REQUEST_METHOD=method)
        request.META['HTTP_IF_NONE_MATCH'] = encode_etag('nope')

        response = view(request)
        self.assertNotIsInstance(response, HttpResponseNotModified)
        self.assertTrue(response.has_header('ETag'))
        self.assertEqual(response['ETag'], encode_etag('test123'))

    def _test_ignore_etag(self, method):
        class MyView(ETagViewMixin, View):
            def get_etag_data(self, *args, **kwargs):
                return 'test123'

        setattr(MyView, method.lower(),
                lambda *args, **kwargs: HttpResponse('hi there'))

        view = MyView.as_view()
        request = RequestFactory().request(REQUEST_METHOD=method)
        request.META['HTTP_IF_NONE_MATCH'] = encode_etag('test123')

        response = view(request)
        self.assertNotIsInstance(response, HttpResponseNotModified)
        self.assertEqual(response.content, b'hi there')
        self.assertFalse(response.has_header('ETag'))
