"""Unit tests for BaseWebAPIToken and WebAPITokenManager."""

from datetime import timedelta

import kgb
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from djblets.testing.testcases import TestCase
from djblets.webapi.models import BaseWebAPIToken


class WebAPIToken(BaseWebAPIToken):
    my_field = models.BooleanField(default=False)


class WebAPITokenTests(TestCase):
    """Unit tests for BaseWebAPIToken.

    Version Added:
        3.0
    """

    def setUp(self):
        super(WebAPITokenTests, self).setUp()

        self.user = User.objects.create(username='test-user')

    def test_is_expired_with_expired(self):
        """Testing BaseWebAPIToken.is_expired with an expired token"""
        now = timezone.now()

        webapi_token = WebAPIToken.objects.generate_token(
            self.user,
            expires=(now - timedelta(hours=1)))

        self.assertTrue(webapi_token.is_expired())

    def test_is_expired_with_non_expired(self):
        """Testing BaseWebAPIToken.is_expired with a non expired token"""
        now = timezone.now()

        webapi_token = WebAPIToken.objects.generate_token(
            self.user,
            expires=(now + timedelta(hours=1)))

        self.assertFalse(webapi_token.is_expired())

    def test_is_expired_with_no_expiry(self):
        """Testing BaseWebAPIToken.is_expired with a token that has
        no expiration date set
        """
        webapi_token = WebAPIToken.objects.generate_token(self.user)

        self.assertFalse(webapi_token.is_expired())


class WebAPITokenManagerTests(kgb.SpyAgency, TestCase):
    """Unit tests for WebAPITokenManager."""

    def setUp(self):
        super(WebAPITokenManagerTests, self).setUp()

        self.user = User.objects.create(username='test-user')

    def test_generate_token_with_defaults(self):
        """Testing WebAPITokenManager.generate_token with default arguments"""
        self.spy_on(WebAPIToken.save, call_original=False)
        self.spy_on(timezone.now, op=kgb.SpyOpReturn(timezone.now()))

        webapi_token = WebAPIToken.objects.generate_token(self.user)

        self.assertEqual(webapi_token.user, self.user)

        self.assertIsNotNone(webapi_token.token)
        self.assertEqual(webapi_token.time_added, timezone.now())
        self.assertEqual(webapi_token.last_updated, timezone.now())
        self.assertIsNone(webapi_token.last_used)
        self.assertIsNone(webapi_token.expires)

        self.assertTrue(webapi_token.valid)
        self.assertIsNone(webapi_token.invalid_date)
        self.assertEqual(webapi_token.invalid_reason, '')

        self.assertEqual(webapi_token.policy, {})
        self.assertEqual(webapi_token.note, '')
        self.assertFalse(webapi_token.my_field)

    def test_generate_token_with_custom_field(self):
        """Testing WebAPITokenManager.generate_token with custom field"""
        webapi_token = WebAPIToken.objects.generate_token(self.user,
                                                          my_field=True)

        self.assertTrue(webapi_token.my_field)

    def test_last_updated(self):
        """Testing WebAPITokenManager.save updates the last updated field"""
        self.spy_on(timezone.now, op=kgb.SpyOpReturn(timezone.now()))

        webapi_token = WebAPIToken.objects.generate_token(
            self.user,
            time_added=(timezone.now() - timedelta(hours=1)),
            last_updated=(timezone.now() - timedelta(hours=1)))

        webapi_token.save()

        self.assertEqual(webapi_token.last_updated, timezone.now())
