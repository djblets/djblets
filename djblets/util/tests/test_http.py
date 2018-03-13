"""Unit tests for djblets.util.http."""

from __future__ import unicode_literals

from django.http import HttpRequest, HttpResponse, HttpResponseNotModified

from djblets.testing.testcases import TestCase
from djblets.util.http import (build_not_modified_from_response,
                               get_http_accept_lists,
                               get_http_requested_mimetype,
                               is_mimetype_a)


class HttpTests(TestCase):
    """Unit tests for djblets.util.http."""

    def setUp(self):
        self.request = HttpRequest()
        self.request.META['HTTP_ACCEPT'] = \
            'application/json;q=0.5,application/xml,text/plain;q=0.0,*/*;q=0.0'

    def test_http_accept_lists(self):
        """Testing get_http_accept_lists"""
        acceptable_mimetypes, unacceptable_mimetypes = \
            get_http_accept_lists(self.request)

        self.assertEqual(acceptable_mimetypes,
                         ['application/xml', 'application/json'])
        self.assertEqual(unacceptable_mimetypes, ['text/plain', '*/*'])

    def test_get_requested_mimetype_with_supported_mimetype(self):
        """Testing get_requested_mimetype with supported mimetype"""
        self.assertEqual(
            get_http_requested_mimetype(self.request, ['foo/bar',
                                                       'application/json']),
            'application/json')
        self.assertEqual(
            get_http_requested_mimetype(self.request, ['application/xml']),
            'application/xml')
        self.assertEqual(
            get_http_requested_mimetype(self.request, ['application/json',
                                                       'application/xml']),
            'application/xml')

    def test_get_requested_mimetype_with_no_consensus(self):
        """Testing get_requested_mimetype with no consensus between client and
        server
        """
        self.request.META['HTTP_ACCEPT'] = ('text/html,application/xhtml+xml,'
                                            'application/xml;q=0.9,*/*;q=0.8')

        self.assertEqual(
            get_http_requested_mimetype(self.request, ['application/json',
                                                       'application/x-foo']),
            'application/json')

    def test_get_requested_mimetype_with_wildcard_supported_mimetype(self):
        """Testing get_requested_mimetype with supported */* mimetype"""
        self.request.META['HTTP_ACCEPT'] = '*/*'
        self.assertEqual(
            get_http_requested_mimetype(self.request, ['application/json',
                                                       'application/xml']),
            'application/json')

    def test_get_requested_mimetype_with_unsupported_mimetype(self):
        """Testing get_requested_mimetype with unsupported mimetype"""
        self.assertIsNone(get_http_requested_mimetype(self.request,
                                                      ['text/plain']))
        self.assertIsNone(get_http_requested_mimetype(self.request,
                                                      ['foo/bar']))

    def test_is_mimetype_a(self):
        """Testing is_mimetype_a"""
        self.assertTrue(is_mimetype_a('application/json',
                                      'application/json'))
        self.assertTrue(is_mimetype_a('application/vnd.foo+json',
                                      'application/json'))
        self.assertFalse(is_mimetype_a('application/xml',
                                       'application/json'))
        self.assertFalse(is_mimetype_a('foo/vnd.bar+json',
                                       'application/json'))

    def test_build_not_modified_from_response_with_headers(self):
        """Testing build_not_modified_from_response with copyable headers
        in response
        """
        response = HttpResponse()
        response['Cache-Control'] = 'max-age=10000'
        response['Content-Location'] = '/foo/'
        response['Date'] = 'Mon, 12 Mar 2018 20:17:00 GMT'
        response['ETag'] = 'abc123'
        response['Expires'] = 'Wed, 14 Mar 2018 13:00:00 GMT'
        response['Vary'] = 'Cookie'

        new_response = build_not_modified_from_response(response)
        self.assertIsInstance(new_response, HttpResponseNotModified)
        self.assertEqual(new_response['Cache-Control'], 'max-age=10000')
        self.assertEqual(new_response['Content-Location'], '/foo/')
        self.assertEqual(new_response['Date'], 'Mon, 12 Mar 2018 20:17:00 GMT')
        self.assertEqual(new_response['ETag'], 'abc123')
        self.assertEqual(new_response['Expires'],
                         'Wed, 14 Mar 2018 13:00:00 GMT')
        self.assertEqual(new_response['Vary'], 'Cookie')

    def test_build_not_modified_from_response_without_headers(self):
        """Testing build_not_modified_from_response without copyable headers
        in response
        """
        new_response = build_not_modified_from_response(HttpResponse())
        self.assertIsInstance(new_response, HttpResponseNotModified)
        self.assertNotIn('Cache-Control', new_response)
        self.assertNotIn('Content-Location', new_response)
        self.assertNotIn('Date', new_response)
        self.assertNotIn('ETag', new_response)
        self.assertNotIn('Expires', new_response)
        self.assertNotIn('Vary', new_response)
