"""Unit tests for djblets.privacy.pii."""

from __future__ import unicode_literals

from django.http import QueryDict
from django.test.client import RequestFactory

try:
    # Django >= 1.10
    from django.urls import ResolverMatch
except ImportError:
    # Django < 1.10
    from django.core.urlresolvers import ResolverMatch

from djblets.privacy.pii import (build_pii_safe_page_url,
                                 build_pii_safe_page_url_for_request)
from djblets.testing.testcases import TestCase


class BuildPIISafePageURLTests(TestCase):
    """Unit tests for build_pii_safe_page_url."""

    def test_with_pii_keyword_in_path(self):
        """Testing build_pii_safe_page_url_for_request with PII
        keyword-matching in URL path
        """
        self.assertEqual(
            build_pii_safe_page_url(
                url='/users/test/',
                url_kwargs={
                    'user': 'test',
                }),
            '/users/<REDACTED>/')

        self.assertEqual(
            build_pii_safe_page_url(
                url='/users/test/',
                url_kwargs={
                    'username': 'test',
                }),
            '/users/<REDACTED>/')

        self.assertEqual(
            build_pii_safe_page_url(
                url='/users/test/',
                url_kwargs={
                    'email': 'test',
                }),
            '/users/<REDACTED>/')

    def test_with_pii_keyword_in_querystring(self):
        """Testing build_pii_safe_page_url with PII
        keyword-matching in URL query string
        """
        self.assertEqual(
            build_pii_safe_page_url(
                url='/',
                query_dict=QueryDict('user=test')),
            '/?user=<REDACTED>')

        self.assertEqual(
            build_pii_safe_page_url(
                url='/',
                query_dict=QueryDict('username=test')),
            '/?username=<REDACTED>')

        self.assertEqual(
            build_pii_safe_page_url(
                url='/',
                query_dict=QueryDict('email=test')),
            '/?email=<REDACTED>')

    def test_with_pii_email_in_path(self):
        """Testing build_pii_safe_page_url with email-like value
        in URL path
        """
        self.assertEqual(
            build_pii_safe_page_url(
                url='/test/a@b.com/',
                url_kwargs={
                    'foo': 'a@b.com',
                }),
            '/test/<REDACTED>/')

    def test_with_pii_email_in_querystring(self):
        """Testing build_pii_safe_page_url with email-like value
        in URL query string
        """
        self.assertEqual(
            build_pii_safe_page_url(
                url='/',
                query_dict=QueryDict('foo=a@b.com')),
            '/?foo=<REDACTED>')

    def test_with_non_string_in_path(self):
        """Testing build_pii_safe_page_url with non-string value in URL path"""
        self.assertEqual(
            build_pii_safe_page_url(
                url='/test/',
                url_kwargs={
                    'type': object,
                }),
            '/test/')

    def test_with_no_pii(self):
        """Testing build_pii_safe_page_url with no PII"""
        self.assertEqual(
            build_pii_safe_page_url(
                url='/groups/test/',
                url_kwargs={
                    'groupname': 'test',
                }),
            '/groups/test/')

    def test_with_no_keywords(self):
        """Testing build_pii_safe_page_url with no keywords in URL
        pattern
        """
        self.assertEqual(
            build_pii_safe_page_url(url='/groups/test/'),
            '/groups/test/')


class BuildPIISafePageURLForRequestTests(TestCase):
    """Unit tests for build_pii_safe_page_url_for_request."""

    def test_with_pii_keyword_in_path(self):
        """Testing build_pii_safe_page_url_for_request with PII
        keyword-matching in URL path
        """
        self.assertEqual(
            build_pii_safe_page_url_for_request(
                self._build_request('/users/test/', {
                    'user': 'test',
                })),
            '/users/<REDACTED>/')

        self.assertEqual(
            build_pii_safe_page_url_for_request(
                self._build_request('/users/test/', {
                    'username': 'test',
                })),
            '/users/<REDACTED>/')

        self.assertEqual(
            build_pii_safe_page_url_for_request(
                self._build_request('/users/test/', {
                    'email': 'test',
                })),
            '/users/<REDACTED>/')

    def test_with_pii_keyword_in_querystring(self):
        """Testing build_pii_safe_page_url_for_request with PII
        keyword-matching in URL query string
        """
        self.assertEqual(
            build_pii_safe_page_url_for_request(
                self._build_request('/?user=test')),
            '/?user=<REDACTED>')

        self.assertEqual(
            build_pii_safe_page_url_for_request(
                self._build_request('/?username=test')),
            '/?username=<REDACTED>')

        self.assertEqual(
            build_pii_safe_page_url_for_request(
                self._build_request('/?email=test')),
            '/?email=<REDACTED>')

    def test_with_pii_email_in_path(self):
        """Testing build_pii_safe_page_url_for_request with email-like value
        in URL path
        """
        self.assertEqual(
            build_pii_safe_page_url_for_request(
                self._build_request('/test/a@b.com/', {
                    'foo': 'a@b.com',
                })),
            '/test/<REDACTED>/')

    def test_with_pii_email_in_querystring(self):
        """Testing build_pii_safe_page_url_for_request with email-like value
        in URL query string
        """
        self.assertEqual(
            build_pii_safe_page_url_for_request(
                self._build_request('/?foo=a@b.com')),
            '/?foo=<REDACTED>')

    def test_with_no_pii(self):
        """Testing build_pii_safe_page_url_for_request with no PII"""
        self.assertEqual(
            build_pii_safe_page_url_for_request(
                self._build_request('/groups/test/', {
                    'groupname': 'test',
                })),
            '/groups/test/')

    def test_with_no_keywords(self):
        """Testing build_pii_safe_page_url_for_request with no keywords in URL
        pattern
        """
        self.assertEqual(
            build_pii_safe_page_url_for_request(
                self._build_request('/groups/test/')),
            '/groups/test/')

    def test_with_no_resolver_match(self):
        """Testing build_pii_safe_page_url_for_request with no resolver match
        """
        self.assertEqual(
            build_pii_safe_page_url_for_request(
                RequestFactory().get('/groups/test/')),
            '/groups/test/')

    def _build_request(self, path, kwargs={}):
        request = RequestFactory().get(path)
        request.resolver_match = ResolverMatch(func=lambda: None,
                                               args=(),
                                               kwargs=kwargs)

        return request
