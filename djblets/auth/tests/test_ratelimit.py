"""Tests for the utilities for rate-limiting login attempts."""

from __future__ import unicode_literals

from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory
from django.test.utils import override_settings
from django.utils import six

from djblets.auth.ratelimit import is_ratelimited, Rate
from djblets.testing.testcases import TestCase


class RateLimitTests(TestCase):
    """Unit tests for djblets.auth.ratelimit."""

    def setUp(self):
        super(RateLimitTests, self).setUp()
        self.request_factory = RequestFactory()

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

        self.assertEqual(six.text_type(context.exception),
                         'LOGIN_LIMIT_RATE setting could not be parsed.')

    @override_settings(LOGIN_LIMIT_RATE='1/h')
    def test_rate_limit_exceeded(self):
        """Testing is_ratelimited when limit exceeded"""
        request = self.request_factory.get('/')
        request.user = User(pk=1)

        self.assertFalse(is_ratelimited(request, increment=True))
        self.assertTrue(is_ratelimited(request, increment=True))
