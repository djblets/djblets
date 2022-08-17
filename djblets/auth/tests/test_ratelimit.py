"""Tests for the utilities for rate-limiting login attempts."""

import kgb
from django.contrib.auth.models import AnonymousUser, User
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory
from django.test.utils import override_settings

from djblets.auth.ratelimit import (Rate,
                                    _get_time_int,
                                    get_usage_count,
                                    is_ratelimited)
from djblets.testing.testcases import TestCase


class RateLimitTests(kgb.SpyAgency, TestCase):
    """Unit tests for djblets.auth.ratelimit."""

    def setUp(self):
        super(RateLimitTests, self).setUp()
        self.request_factory = RequestFactory()

        self.spy_on(_get_time_int, op=kgb.SpyOpReturn(1659732041))

    def tearDown(self):
        super(RateLimitTests, self).tearDown()
        cache.clear()

    def test_rate_parsing(self):
        """Testing Rate.parse"""
        test_rates = (
            ('100/s', Rate(100, 1)),
            ('100/10s', Rate(100, 10)),
            ('100/10', Rate(100, 10)),
            ('100/m', Rate(100, 60)),
            ('400/10m', Rate(400, 600)),
            ('1000/h', Rate(1000, 3600)),
            ('800/d', Rate(800, 24 * 60 * 60)),
        )

        for rate_str, rate in test_rates:
            self.assertEqual(rate, Rate.parse(rate_str))

    @override_settings(LOGIN_LIMIT_RATE='7/m')
    def test_unauthenticated_user(self):
        """Testing is_ratelimited with unauthenticated user"""
        request = self.request_factory.get('/')
        request.user = AnonymousUser()

        self.assertFalse(is_ratelimited(request, increment=False))

    @override_settings(LOGIN_LIMIT_RATE='blah')
    def test_invalid_rate_limit(self):
        """Testing is_ratelimited with invalid rate limit parameter"""
        request = self.request_factory.get('/')
        request.user = User(pk=1)

        with self.assertRaises(ImproperlyConfigured) as context:
            is_ratelimited(request, increment=False)

        self.assertEqual(str(context.exception),
                         'LOGIN_LIMIT_RATE setting could not be parsed.')

    @override_settings(LOGIN_LIMIT_RATE='1/h')
    def test_rate_limit_exceeded(self):
        """Testing is_ratelimited when limit exceeded"""
        request = self.request_factory.get('/')
        request.user = User(pk=1)

        self.assertFalse(is_ratelimited(request, increment=True))
        self.assertTrue(is_ratelimited(request, increment=True))

    @override_settings(LOGIN_LIMIT_RATE='1/s')
    def test_get_usage_count_at_1s(self):
        """Testing get_usage_count at 1/s"""
        request = self.request_factory.get('/')
        request.user = User(pk=1)

        self.assertEqual(
            get_usage_count(request=request,
                            increment=True),

            {
                'count': 1,
                'limit': 1,
                'time_left': 0,
            })

        self.assertEqual(
            get_usage_count(request=request,
                            increment=True),

            {
                'count': 2,
                'limit': 1,
                'time_left': 0,
            })

    @override_settings(LOGIN_LIMIT_RATE='1/m')
    def test_get_usage_count_at_1m(self):
        """Testing get_usage_count at 1/m"""
        request = self.request_factory.get('/')
        request.user = User(pk=1)

        self.assertEqual(
            get_usage_count(request=request,
                            increment=True),

            {
                'count': 1,
                'limit': 1,
                'time_left': 19,
            })

        self.assertEqual(
            get_usage_count(request=request,
                            increment=True),

            {
                'count': 2,
                'limit': 1,
                'time_left': 19,
            })

    @override_settings(LOGIN_LIMIT_RATE='1/h')
    def test_get_usage_count_at_1h(self):
        """Testing get_usage_count at 1/h"""
        request = self.request_factory.get('/')
        request.user = User(pk=1)

        self.assertEqual(
            get_usage_count(request=request,
                            increment=True),

            {
                'count': 1,
                'limit': 1,
                'time_left': 1159,
            })

        self.assertEqual(
            get_usage_count(request=request,
                            increment=True),

            {
                'count': 2,
                'limit': 1,
                'time_left': 1159,
            })

    @override_settings(LOGIN_LIMIT_RATE='1/s')
    def test_get_usage_count_with_increment_false(self):
        """Testing get_usage_count with increment=False"""
        request = self.request_factory.get('/')
        request.user = User(pk=1)

        # First call will always have count=1, no matter what.
        self.assertEqual(
            get_usage_count(request=request,
                            increment=False),

            {
                'count': 1,
                'limit': 1,
                'time_left': 0,
            })

        self.assertEqual(
            get_usage_count(request=request,
                            increment=False),

            {
                'count': 1,
                'limit': 1,
                'time_left': 0,
            })
