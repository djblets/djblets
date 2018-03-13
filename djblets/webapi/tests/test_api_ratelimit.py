"""Unit tests for API rate limiting."""

from __future__ import unicode_literals

import json

from django.test.utils import override_settings
from django.test.client import RequestFactory
from django.utils.encoding import force_text

from djblets.testing.testcases import TestCase
from djblets.webapi.errors import RATE_LIMIT_EXCEEDED
from djblets.webapi.resources.registry import unregister_resource
from djblets.webapi.resources.user import UserResource


class WebAPIRateLimitTests(TestCase):
    """Unit tests for API rate limiting."""

    def setUp(self):
        super(WebAPIRateLimitTests, self).setUp()

        self.factory = RequestFactory()
        self.user_resource = UserResource()

    def tearDown(self):
        super(WebAPIRateLimitTests, self).tearDown()

        unregister_resource(self.user_resource)

    @override_settings(API_ANONYMOUS_LIMIT_RATE='2/h')
    def test_api_rate_limit(self):
        """Testing API rate limiting."""
        request = self.factory.get('/api/')

        # First two should succeed
        response = self.user_resource(request)
        self.assertEqual(response.status_code, 200)

        response = self.user_resource(request)
        self.assertEqual(response.status_code, 200)

        # Third one should fail
        response = self.user_resource(request)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response['X-RateLimit-Limit'], '2')

        rsp = json.loads(force_text(response.content))
        self.assertEqual(rsp['err']['code'], RATE_LIMIT_EXCEEDED.code)
