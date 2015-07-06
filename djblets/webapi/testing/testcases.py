"""Test case support for full API testing.

This provides a useful mixin, :py:class:`WebAPITestCaseMixin`, that can be
mixed into a base test case for an API testing suite. This mixin provides
a number of useful helpers for calling APIs and validating results, along
with generating consistent docstrings.
"""

from __future__ import print_function, unicode_literals

import json

from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from django.utils import six

from djblets.testing.testcases import TestCase


class WebAPITestCaseMixin(TestCase):
    """Mixin for test cases for thoroughly testing APIs.

    This helps with the testing of APIs by providing convenient methods for
    performing HTTP requests and checking their response payloads, redirects,
    mimetypes, and more.

    Any test methods in a subclass that have the ``is_test_template`` flag set
    to ``True`` can include ``<URL>`` in their docstring. When the test is
    run, the ``<URL>`` will be replaced by the contents of the subclass's
    :py:attr:`sample_api_url`.

    WebAPITestCaseMixin is meant to be mixed into a new base class that all
    API test suites would inherit from. Subclasses must provide values for
    :py:attr:`sample_api_url` and :py:attr:`error_mimetype`.
    """

    #: The path to the resource, which may be placed into the docstring.
    sample_api_url = None

    #: The mimetype representing an error for this API.
    error_mimetype = None

    #: A fake base URL for API operations.
    base_url = 'http://testserver'

    def shortDescription(self):
        """Return a description for a particular test.

        If the test has the ``is_test_template`` attribute set, and
        contains ``<URL>`` in the docstring, the URL will be replaced by
        the contents of :py:attr:`sample_api_url`.

        Returns:
            unicode: The description of the test.
        """
        desc = super(WebAPITestCaseMixin, self).shortDescription()

        if self.sample_api_url:
            test_method = getattr(self, self._testMethodName)

            if getattr(test_method, 'is_test_template', False):
                desc = desc.replace('<URL>', self.sample_api_url)

        return desc

    def api_get(self, path, query={}, follow_redirects=False,
                expected_status=200, expected_redirects=[],
                expected_headers={}, expected_mimetype=None,
                expected_json=True):
        """Perform and check a HTTP GET request to an API resource.

        This will perform the request to the resource and validate that all
        the results are what the caller expects.

        Args:
            path (unicode):
                The path to the resource to request.

            query (dict):
                The query string.

            expected_status (int):
                The expected HTTP status.

            follow_redirects (bool):
                Whether to expect and follow redirects to another URL.

            expected_redirects (list of unicode):
                The list of expected redirects performed by the resource(s),
                in order.

            expected_headers (dict):
                Expected HTTP headers and their values from the response.

            expected_mimetype (unicode):
                The expected mimetype for the response payload.

            expected_json (bool):
                Whether the response is expected to be in JSON format.

        Returns:
            The parsed payload data as a dictionary, if ``expected_json`` is
            ``True`` and the response isn't a HTTP 302. Otherwise, the
            raw payload contents.
        """
        path = self._normalize_path(path)

        print('GETing %s' % path)
        print("Query data: %s" % query)

        response = self._api_func_wrapper(
            self.client.get, path, query, expected_status, follow_redirects,
            expected_redirects, expected_mimetype,
            content_type='text/html; charset=utf-8')

        for header, value in six.iteritems(expected_headers):
            self.assertIn(header, response)
            self.assertEqual(response[header], value)

        if expected_status != 302 and expected_json:
            rsp = json.loads(response.content)
        else:
            rsp = response.content

        print("Response: %s" % rsp)

        return rsp

    def api_post_with_response(self, path, query={}, expected_status=201,
                               expected_mimetype=None):
        """Perform an HTTP POST to an API resource, returning additional data.

        This works like :py:meth:`api_post`, but returns the resulting payload
        and the original :py:class:`HttpResponse`.

        This will perform the request to the resource and validate that all
        the results are what the caller expects.

        Args:
            path (unicode):
                The path to the resource to request.

            query (dict):
                The form data to post.

            expected_status (int):
                The expected HTTP status.

            expected_mimetype (unicode):
                The expected mimetype for the response payload.

        Returns:
            tuple:
            A 2-item tuple containing the parsed response and the original
            :py:class:`HttpResponse`.
        """
        path = self._normalize_path(path)

        print('POSTing to %s' % path)
        print("Post data: %s" % query)
        response = self.client.post(path, query,
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        print("Raw response: %s" % response.content)
        self.assertEqual(response.status_code, expected_status)

        if expected_status >= 400:
            self.assertEqual(expected_mimetype, None)

            if expected_status != 405:
                self.assertEqual(response['Content-Type'], self.error_mimetype)
        else:
            self.assertNotEqual(expected_mimetype, None)
            self.assertEqual(response['Content-Type'], expected_mimetype)

        return self._get_result(response, expected_status), response

    def api_post(self, *args, **kwargs):
        """Perform and check an HTTP POST to an API resource.

        This will perform the request to the resource and validate that all
        the results are what the caller expects.

        Args:
            path (unicode):
                The path to the resource to request.

            query (dict):
                The form data to post.

            expected_status (int):
                The expected HTTP status.

            expected_mimetype (unicode):
                The expected mimetype for the response payload.

        Returns:
            The parsed payload data.
        """
        return self.api_post_with_response(*args, **kwargs)[0]

    def api_put(self, path, query={}, expected_status=200,
                follow_redirects=False, expected_redirects=[],
                expected_mimetype=None):
        """Perform and check an HTTP PUT to an API resource.

        This will perform the request to the resource and validate that all
        the results are what the caller expects.

        Args:
            path (unicode):
                The path to the resource to request.

            query (dict):
                The form data to post.

            expected_status (int):
                The expected HTTP status.

            follow_redirects (bool):
                Whether to expect and follow redirects to another URL.

            expected_redirects (list of unicode):
                The list of expected redirects performed by the resource(s),
                in order.

            expected_mimetype (unicode):
                The expected mimetype for the response payload.

        Returns:
            The parsed payload data.
        """
        path = self._normalize_path(path)

        print('PUTing to %s' % path)
        print("Post data: %s" % query)
        data = encode_multipart(BOUNDARY, query)

        response = self._api_func_wrapper(
            self.client.put, path, data, expected_status, follow_redirects,
            expected_redirects, expected_mimetype,
            content_type=MULTIPART_CONTENT)

        return self._get_result(response, expected_status)

    def api_delete(self, path, expected_status=204):
        """Perform and check an HTTP DELETE to an API resource.

        This will perform the request to the resource and validate that all
        the results are what the caller expects.

        Args:
            path (unicode):
                The path to the resource to request.

            expected_status (int):
                The expected HTTP status.

        Returns:
            HttpResponse:
            The HTTP respons of the payload. This won't have any content if
            the delete was successful.
        """
        path = self._normalize_path(path)

        print('DELETEing %s' % path)
        response = self.client.delete(path)
        print("Raw response: %s" % response.content)
        self.assertEqual(response.status_code, expected_status)

        return self._get_result(response, expected_status)

    def assertHttpOK(self, response, check_last_modified=False,
                     check_etag=False):
        """Assert that a response was OK and optionally has caching headers.

        Args:
            response (HttpResponse):
                The HTTP response from the API.

            check_last_modified (bool):
                If set, this will assert that the response has a
                ``Last-Modified`` header.

            check_etag (bool):
                If set, this will assert that the response has a
                ``ETag`` header.
        """
        self.assertEquals(response.status_code, 200)

        if check_last_modified:
            self.assertIn('Last-Modified', response)

        if check_etag:
            self.assertIn('ETag', response)

    def assertHttpNotModified(self, response):
        """Assert that the response was HTTP 304 Not Modified.

        Args:
            response (HttpResponse): The HTTP response from the API.
        """
        self.assertEquals(response.status_code, 304)
        self.assertEquals(response.content, '')

    def _api_func_wrapper(self, api_func, path, query, expected_status,
                          follow_redirects, expected_redirects,
                          expected_mimetype, content_type='', extra={}):
        """Wrapper around API functions.

        This will invoke an API function with all the necessary parameters,
        and check the results for the expected values.

        Args:
            api_func (callable):
                The API function to call.

            path (unicode):
                The path to the resource to request.

            query (dict):
                The GET query data or POST form data.

            expected_status (int):
                The expected HTTP status.

            follow_redirects (bool):
                Whether to expect and follow redirects to another URL.

            expected_redirects (list of unicode):
                The list of expected redirects performed by the resource(s),
                in order.

            expected_mimetype (unicode):
                The expected mimetype for the response payload.

            content_type (unicode):
                The content type of the request data.

            extra (dict):
                Extra data to pass to the function.

        Returns:
            HttpResponse: The HTTP response from the API resource.
        """
        response = api_func(path, query, follow=follow_redirects,
                            content_type=content_type, extra=extra,
                            HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        print("Raw response: %s" % response.content)

        self.assertEqual(response.status_code, expected_status)

        if expected_status >= 400:
            self.assertEqual(expected_mimetype, None)

            if expected_status != 405:
                self.assertEqual(response['Content-Type'], self.error_mimetype)
        elif expected_status != 302:
            self.assertNotEqual(expected_mimetype, None)
            self.assertEqual(response['Content-Type'], expected_mimetype)

        if expected_redirects:
            self.assertEqual(len(response.redirect_chain),
                             len(expected_redirects))

            for redirect in expected_redirects:
                self.assertEqual(response.redirect_chain[0][0],
                                 self.base_url + expected_redirects[0])

        return response

    def _normalize_path(self, path):
        """Normalize a path, removing the base URL if found.

        Args:
            path (unicode): The path or full URL.

        Returns:
            unicode: The path without the base server URL.
        """
        if path.startswith(self.base_url):
            return path[len(self.base_url):]
        else:
            return path

    def _get_result(self, response, expected_status):
        """Return the parsed result from a response.

        If the expected HTTP status is a 204 (No Content) or 405 (Method not
        allowed), the response will be asserted to be empty and the function
        will return ``None``. Otherwise, the parsed JSON response will be
        returned.

        Args:
            response (HttpResponse):
                The HTTP response from the API.

            expected_status (int):
                The expected HTTP status.

        Returns:
            The parsed JSON response from the payload, or ``None``.
        """
        if expected_status in (204, 405):
            self.assertEqual(response.content, '')
            rsp = None
        else:
            rsp = json.loads(response.content)
            print("Response: %s" % rsp)

        return rsp
