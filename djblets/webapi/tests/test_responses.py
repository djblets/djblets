from __future__ import unicode_literals

import json

from django.test.client import RequestFactory

from djblets.testing.testcases import TestCase
from djblets.webapi.resources.registry import unregister_resource
from djblets.webapi.resources.user import UserResource


class WebAPIResponsePaginatedTests(TestCase):
    """Unit tests for djblets.webapi.responses.WebAPIResponsePaginated."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user_resource = UserResource()

    def tearDown(self):
        unregister_resource(self.user_resource)

    def test_pagination_serialization_encoding(self):
        """Testing WebAPIResponsePaginated query parameter encoding"""
        # This test is for an issue when query parameters included unicode
        # characters. In this case, creating the 'self' or pagination links
        # would cause a KeyError. If this test runs fine without any uncaught
        # exceptions, then it means we're good.
        request = self.factory.get('/api/users/?q=%D0%B5')
        response = self.user_resource(request)

        rsp = json.loads(response.content)
        self.assertEqual(rsp['links']['self']['href'],
                         'http://testserver/api/users/?q=%D0%B5')
