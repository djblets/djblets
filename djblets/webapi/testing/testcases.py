"""Test case support for full API testing.

This provides a useful mixin, :py:class:`WebAPITestCaseMixin`, that can be
mixed into a base test case for an API testing suite. This mixin provides
a number of useful helpers for calling APIs and validating results, along
with generating consistent docstrings.
"""

from __future__ import print_function, unicode_literals

import json
import pprint
import warnings

from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from django.utils import six
from django.utils.encoding import force_text

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
            unicode:
            The description of the test.
        """
        desc = super(WebAPITestCaseMixin, self).shortDescription()

        if self.sample_api_url:
            test_method = getattr(self, self._testMethodName)

            if getattr(test_method, 'is_test_template', False):
                desc = desc.replace('<URL>', self.sample_api_url)

        return desc

    def api_get(self, *args, **kwargs):
        """Perform and check a HTTP GET request, returning additional data.

        This will perform the request to the resource and validate that all
        the results are what the caller expects.

        This method is a wrapper around :py:meth:`api_get_with_response`. See
        that method for the arguments.

        Args:
            *args (tuple):
                Positional arguments to pass to
                :py:meth:`api_get_with_response`.

            **kwargs (dict):
                Keyword arguments to pass to :py:meth:`api_get_with_response`.

        Returns:
            dict or bytes:
            The parsed payload data as a dictionary, if ``expected_json`` is
            ``True`` and the response isn't a HTTP 302. Otherwise, the
            raw payload contents.
        """
        return self.api_get_with_response(*args, **kwargs)[0]

    def api_get_with_response(self, path, data={}, **kwargs):
        """Perform and check a HTTP GET request to an API resource.

        This will perform the request to the resource and validate that all the
        results are what the caller expects.

        Args:
            path (unicode):
                The path to the resource to request.

            data (object, optional):
                The request query string.

            *args (tuple):
                Positional arguments to pass to :py:meth:`api_call`.

            **kwargs (dict):
                Keyword arguments to pass to :py:meth:`api_call`.

        Returns:
            tuple:
            A 2-item tuple containing the parsed response and the original
            :py:class:`HttpResponse`.
        """
        return self.api_call(client_http_method=self.client.get,
                             path=path,
                             data=data,
                             **kwargs)

    def api_post(self, *args, **kwargs):
        """Perform and check an HTTP POST to an API resource.

        This will perform the request to the resource and validate that all
        the results are what the caller expects.

        This method is a wrapper around :py:meth:`api_post_with_response`. See
        that method for the arguments.

        Args:
            *args (tuple):
                Positional arguments to pass to
                :py:meth:`api_post_with_response`.

            **kwargs (dict):
                Keyword arguments to pass to :py:meth:`api_post_with_response`.

        Returns:
            dict or bytes:
            The parsed payload data as a dictionary, if ``expected_json`` is
            ``True`` and the response isn't a HTTP 302. Otherwise, the
            raw payload contents.
        """
        return self.api_post_with_response(*args, **kwargs)[0]

    def api_post_with_response(self, path, data={}, expected_status=201,
                               **kwargs):
        """Perform an HTTP POST to an API resource, returning additional data.

        This works like :py:meth:`api_post`, but returns the resulting payload
        and the original :py:class:`HttpResponse`.

        This will perform the request to the resource and validate that all
        the results are what the caller expects.

        Args:
            path (unicode):
                The path to the resource to request.

            data (object, optional):
                The request payload.

            expected_status (int, optional):
                The expected HTTP status.

            *args (tuple):
                Positional arguments to pass to :py:meth:`api_call`.

            **kwargs (dict):
                Keyword arguments to pass to :py:meth:`api_call`.

        Returns:
            tuple:
            A 2-item tuple containing the parsed response and the original
            :py:class:`HttpResponse`.
        """
        return self.api_call(client_http_method=self.client.post,
                             path=path,
                             data=data,
                             expected_status=expected_status,
                             **kwargs)

    def api_put(self, *args, **kwargs):
        """Perform and check an HTTP PUT to an API resource.

        This will perform the request to the resource and validate that all
        the results are what the caller expects.

        This method is a wrapper around :py:meth:`api_put_with_response`. See
        that method for the arguments.

        Args:
            *args (tuple):
                Positional arguments to pass to
                :py:meth:`api_put_with_response`.

            **kwargs (dict):
                Keyword arguments to pass to :py:meth:`api_put_with_response`.

        Returns:
            dict or bytes:
            The parsed payload data as a dictionary, if ``expected_json`` is
            ``True`` and the response isn't a HTTP 302. Otherwise, the
            raw payload contents.
        """
        return self.api_put_with_response(*args, **kwargs)[0]

    def api_put_with_response(self, path, data={},
                              content_type=MULTIPART_CONTENT,
                              **kwargs):
        """Perform an HTTP PUT to an API resource, returning additional data.

        This will perform the request to the resource and validate that all
        the results are what the caller expects.

        Args:
            path (unicode):
                The path to the resource to request.

            data (object, optional):
                The request payload.

            *args (tuple):
                Positional arguments to pass to :py:meth:`api_call`.

            **kwargs (dict):
                Keyword arguments to pass to :py:meth:`api_call`.

        Returns:
            A 2-item tuple containing the parsed response and the original
            :py:class:`HttpResponse`.
        """
        return self.api_call(client_http_method=self.client.put,
                             path=path,
                             data=data,
                             content_type=content_type,
                             **kwargs)

    def api_delete(self, *args, **kwargs):
        """Perform and check an HTTP DELETE to an API resource.

        This will perform the request to the resource and validate that all
        the results are what the caller expects.

        This method is a wrapper around :py:meth:`api_delete_with_response`.
        See that method for the arguments.

        Args:
            *args (tuple):
                Positional arguments to pass to
                :py:meth:`api_delete_with_response`.

            **kwargs (dict):
                Keyword arguments to pass to
                :py:meth:`api_delete_with_response`.

        Returns:
            bytes:
            The HTTP response payload. This won't have any content if the
            delete was successful.
        """
        return self.api_delete_with_response(*args, **kwargs)[0]

    def api_delete_with_response(self, path, expected_status=204, **kwargs):
        """Perform an HTTP DELETE to an API resource, returning additional data.

        This will perform the request to the resource and validate that all
        the results are what the caller expects.

        Args:
            path (unicode):
                The path to the resource to request.

            expected_status (int, optional):
                The expected HTTP status.

            *args (tuple):
                Positional arguments to pass to :py:meth:`api_call`.

            **kwargs (dict):
                Keyword arguments to pass to :py:meth:`api_call`.

        Returns:
            tuple:
            A 2-item tuple containing the parsed response and the original
            :py:class:`HttpResponse`.
        """
        return self.api_call(client_http_method=self.client.delete,
                             path=path,
                             expected_status=expected_status,
                             **kwargs)

    def assertHttpOK(self, response, check_last_modified=False,
                     check_etag=False):
        """Assert that a response was OK and optionally has caching headers.

        Args:
            response (django.http.HttpResponse):
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
            response (django.http.HttpResponse):
                The HTTP response from the API.
        """
        self.assertEquals(response.status_code, 304)
        self.assertEquals(response.content, b'')

    def api_call(self, client_http_method, path, data=None,
                 follow_redirects=False, expected_status=200,
                 expected_redirects=[], expected_headers={},
                 expected_mimetype=None, expected_num_queries=None,
                 expected_json=True, return_http_response=True, **extra):
        """Perform an API call using a client API method.

        This will invoke an API function with all the necessary parameters,
        and check the results for the expected values.

        Args:
            api_func (callable):
                The API function to call.

            path (unicode):
                The path to the resource to request.

            data (dict, optional):
                The data to pass in the request. For an HTTP GET, this will
                be used as a query string. For other requests, this will be
                the request body.

            follow_redirects (bool, optional):
                Whether to expect and follow redirects to another URL.

            expected_status (int, optional):
                The expected HTTP status.

            expected_redirects (list of unicode, optional):
                The list of expected redirects performed by the resource(s),
                in order.

            expected_headers (dict, optional):
                Expected HTTP headers and their values from the
                response.

            expected_num_queries (int, optional):
                The number of queries this API call is expected to make.

            expected_mimetype (unicode, optional):
                The expected mimetype for the response payload.

            expected_json (bool):
                Whether JSON-parsable content is expected in the response.

            return_http_response (bool, optional):
                Whether to return the :py:class:`~django.http.HttpResponse`
                as part of the result.

            **extra (dict):
                Extra data to pass to the client HTTP method.

        Returns:
            object:
            By default, this returns the payload content, which may be a
            raw byte string result or a deserialized JSON body (depending on
            ``expected_json``).

            If passing ``return_http_response=True``, this will return a
            tuple in the form of ``(payload_content, http_response)``,
            where ``http_response`` is the
            :py:class:`~django.http.HttpResponse` object.
        """
        def _call_api():
            return client_http_method(path=path,
                                      data=data,
                                      follow=follow_redirects,
                                      HTTP_X_REQUESTED_WITH='XMLHttpRequest',
                                      **extra)

        # Normalize the API path so that the base URL containing the hostname
        # is stripped.
        if path.startswith(self.base_url):
            path = path[len(self.base_url):]

        # If the caller is explicitly requested multipart content, ensure we've
        # encoded the data.
        if extra.get('content_type') == MULTIPART_CONTENT:
            data = encode_multipart(BOUNDARY, data)

        # Log some details about the API request that's about to be performed.
        print('Performing HTTP %s for API %s'
              % (client_http_method.__name__.upper(), path))

        if data is not None:
            print('Request data = %r' % data)

        if expected_num_queries is None:
            response = _call_api()
        else:
            with self.assertNumQueries(expected_num_queries):
                response = _call_api()

        print('Raw API response: %r' % response.content)

        rsp = response.content

        self.assertEqual(response.status_code, expected_status)

        if expected_status in (204, 405):
            self.assertEqual(response.content, b'')
            rsp = None
        else:
            if expected_status != 302 and expected_json:
                rsp = json.loads(force_text(response.content))
            else:
                rsp = response.content

            print('Parsed API response:')
            pprint.pprint(rsp)

            if expected_status >= 400:
                # Error responses should be using the test's error mimetype
                # and not some valid response mimetype.
                self.assertIsNone(expected_mimetype)

                if expected_status != 405:
                    self.assertEqual(response['Content-Type'],
                                     self.error_mimetype)
            elif expected_status != 302:
                # All status codes other than the few above should have a
                # response payload matching the expected mimetype.
                self.assertIsNotNone(expected_mimetype)
                self.assertEqual(response['Content-Type'], expected_mimetype)

        # Check if the response redirected the way the caller expected.
        if expected_redirects:
            self.assertEqual(len(response.redirect_chain),
                             len(expected_redirects))

            for redirect in expected_redirects:
                self.assertEqual(response.redirect_chain[0][0],
                                 self.base_url + expected_redirects[0])

        # Check that all the expected headers are present in the response.
        for header, value in six.iteritems(expected_headers):
            self.assertIn(header, response)
            self.assertEqual(response[header], value)

        if return_http_response:
            return rsp, response
        else:
            return rsp
