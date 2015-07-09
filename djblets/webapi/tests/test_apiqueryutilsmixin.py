from __future__ import print_function, unicode_literals

from django.db.models import Q
from django.test.client import RequestFactory

from djblets.webapi.resources.mixins.queries import APIQueryUtilsMixin
from djblets.testing.testcases import TestCase


class APIQueryUtilsMixinTests(TestCase):
    """Unit tests for djblets.webapi.resources.mixins.queries."""

    def setUp(self):
        self.query_utils = APIQueryUtilsMixin()
        self.request_factory = RequestFactory()

    def test_build_queries_for_int_field_with_lt(self):
        """Testing APIQueryUtilsMixin.build_queries_for_int_field with -lt="""
        request = self.request_factory.get('/api/test/?myfield-lt=10')
        q = self.query_utils.build_queries_for_int_field(request, 'myfield')

        self.assertQEqual(q, Q(myfield__lt=10))

    def test_build_queries_for_int_field_with_lte(self):
        """Testing APIQueryUtilsMixin.build_queries_for_int_field with -lte="""
        request = self.request_factory.get('/api/test/?myfield-lte=10')
        q = self.query_utils.build_queries_for_int_field(request, 'myfield')

        self.assertQEqual(q, Q(myfield__lte=10))

    def test_build_queries_for_int_field_with_gt(self):
        """Testing APIQueryUtilsMixin.build_queries_for_int_field with -gt="""
        request = self.request_factory.get('/api/test/?myfield-gt=10')
        q = self.query_utils.build_queries_for_int_field(request, 'myfield')

        self.assertQEqual(q, Q(myfield__gt=10))

    def test_build_queries_for_int_field_with_gte(self):
        """Testing APIQueryUtilsMixin.build_queries_for_int_field with -gte="""
        request = self.request_factory.get('/api/test/?myfield-gte=10')
        q = self.query_utils.build_queries_for_int_field(request, 'myfield')

        self.assertQEqual(q, Q(myfield__gte=10))

    def test_build_queries_for_int_field_with_query_param_name(self):
        """Testing APIQueryUtilsMixin.build_queries_for_int_field
        with query_param_name
        """
        request = self.request_factory.get('/api/test/?foo-gte=10')
        q = self.query_utils.build_queries_for_int_field(request, 'myfield',
                                                         'foo')

        self.assertQEqual(q, Q(myfield__gte=10))

    def assertQEqual(self, q1, q2):
        self.assertEqual(q1.connector, q2.connector)
        self.assertEqual(q1.children, q2.children)
