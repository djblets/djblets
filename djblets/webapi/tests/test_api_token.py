"""Unit tests for BaseWebAPIToken and WebAPITokenManager."""

import warnings
from datetime import timedelta

import kgb
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from djblets.secrets.token_generators.legacy_sha1 import \
    LegacySHA1TokenGenerator
from djblets.secrets.token_generators.vendor_checksum import \
    VendorChecksumTokenGenerator
from djblets.testing.testcases import TestCase
from djblets.webapi.errors import WebAPITokenGenerationError
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

        self.token_generator_id = \
            VendorChecksumTokenGenerator.token_generator_id
        self.token_info = {'token_type': 'test'}
        self.user = User.objects.create(username='test-user')

    def test_is_deprecated_with_deprecated(self):
        """Testing BaseWebAPIToken.is_deprecated with a token from a
        deprecated token generator
        """
        token_generator_id = LegacySHA1TokenGenerator.token_generator_id
        token_info = {
            'attempt': 0,
            'token_type': 'test',
            'user': self.user,
        }

        webapi_token = WebAPIToken.objects.generate_token(
            self.user,
            token_generator_id=token_generator_id,
            token_info=token_info)

        self.assertTrue(webapi_token.is_deprecated())

    def test_is_deprecated_with_non_deprecated(self):
        """Testing BaseWebAPIToken.is_deprecated with a token from a
        token generator that is not deprecated
        """
        token_generator_id = VendorChecksumTokenGenerator.token_generator_id
        token_info = {'token_type': 'test'}

        webapi_token = WebAPIToken.objects.generate_token(
            self.user,
            token_generator_id=token_generator_id,
            token_info=token_info)

        self.assertFalse(webapi_token.is_deprecated())

    def test_is_expired_with_expired(self):
        """Testing BaseWebAPIToken.is_expired with an expired token"""
        now = timezone.now()

        webapi_token = WebAPIToken.objects.generate_token(
            self.user,
            expires=(now - timedelta(hours=1)),
            token_generator_id=self.token_generator_id,
            token_info=self.token_info)

        self.assertTrue(webapi_token.is_expired())

    def test_is_expired_with_non_expired(self):
        """Testing BaseWebAPIToken.is_expired with a non expired token"""
        now = timezone.now()

        webapi_token = WebAPIToken.objects.generate_token(
            self.user,
            expires=(now + timedelta(hours=1)),
            token_generator_id=self.token_generator_id,
            token_info=self.token_info)

        self.assertFalse(webapi_token.is_expired())

    def test_is_expired_with_no_expiry(self):
        """Testing BaseWebAPIToken.is_expired with a token that has
        no expiration date set
        """
        webapi_token = WebAPIToken.objects.generate_token(
            self.user,
            token_generator_id=self.token_generator_id,
            token_info=self.token_info)

        self.assertFalse(webapi_token.is_expired())


class WebAPITokenManagerTests(kgb.SpyAgency, TestCase):
    """Unit tests for WebAPITokenManager."""

    def setUp(self):
        super(WebAPITokenManagerTests, self).setUp()

        self.token_generator_id = \
            VendorChecksumTokenGenerator.token_generator_id
        self.token_info = {'token_type': 'test'}
        self.user = User.objects.create(username='test-user')

    def test_generate_token_with_defaults(self):
        """Testing WebAPITokenManager.generate_token with default arguments"""
        self.spy_on(WebAPIToken.save, call_original=False)
        self.spy_on(timezone.now, op=kgb.SpyOpReturn(timezone.now()))

        webapi_token = WebAPIToken.objects.generate_token(
            self.user,
            token_generator_id=self.token_generator_id,
            token_info=self.token_info)

        self.assertEqual(webapi_token.user, self.user)

        self.assertEqual(webapi_token.time_added, timezone.now())
        self.assertEqual(webapi_token.last_updated, timezone.now())
        self.assertIsNone(webapi_token.last_used)
        self.assertIsNone(webapi_token.expires)

        self.assertTrue(webapi_token.valid)
        self.assertIsNone(webapi_token.invalid_date)
        self.assertEqual(webapi_token.invalid_reason, '')

        self.assertEqual(webapi_token.policy, {})
        self.assertEqual(webapi_token.note, '')
        self.assertIsNotNone(webapi_token.token)
        self.assertEqual(webapi_token.token_generator_id,
                         self.token_generator_id)
        self.assertFalse(webapi_token.my_field)

    def test_generate_token_with_custom_field(self):
        """Testing WebAPITokenManager.generate_token with custom field"""
        webapi_token = WebAPIToken.objects.generate_token(
            self.user,
            my_field=True,
            token_generator_id=self.token_generator_id,
            token_info=self.token_info)

        self.assertTrue(webapi_token.my_field)

    def test_last_updated(self):
        """Testing WebAPITokenManager.save updates the last updated field"""
        self.spy_on(timezone.now, op=kgb.SpyOpReturn(timezone.now()))

        webapi_token = WebAPIToken.objects.generate_token(
            self.user,
            last_updated=(timezone.now() - timedelta(hours=1)),
            time_added=(timezone.now() - timedelta(hours=1)),
            token_generator_id=self.token_generator_id,
            token_info=self.token_info)

        webapi_token.save()

        self.assertEqual(webapi_token.last_updated, timezone.now())

    def test_generate_token_with_specific_generator(self):
        """Testing WebAPITokenManager.generate_token with specifying a
        token generator
        """
        webapi_token = WebAPIToken.objects.generate_token(
            self.user,
            token_generator_id=self.token_generator_id,
            token_info=self.token_info)

        self.assertEqual(webapi_token.token_generator_id,
                         self.token_generator_id)
        self.assertTrue(
            webapi_token.token.startswith(self.token_info['token_type']))

    def test_generate_token_with_nonexistant_generator(self):
        """Testing WebAPITokenManager.generate_token with specifying a
        token generator that does not exist in the registry
        """
        token_generator_id = 'missing_generator'
        token_info = {'token_type': 'test'}
        expected_message = ('Could not find the token generator '
                            'to generate the token.')
        expected_log = ('Could not find the missing_generator token '
                        'generator in the registry.')

        with self.assertRaisesMessage(WebAPITokenGenerationError,
                                      expected_message):
            with self.assertLogs() as logs:
                WebAPIToken.objects.generate_token(
                    self.user,
                    token_generator_id=token_generator_id,
                    token_info=token_info)

                self.assertEqual(logs.records[0].getMessage(),
                                 expected_log)

    def test_invalidate_token(self):
        """Testing WebAPITokenManager.invalidate_token"""
        self.spy_on(timezone.now, op=kgb.SpyOpReturn(timezone.now()))

        webapi_token1 = WebAPIToken.objects.generate_token(
            self.user,
            token_generator_id=self.token_generator_id,
            token_info=self.token_info)

        user2 = User.objects.create(username='test-user2')
        webapi_token2 = WebAPIToken.objects.generate_token(
            user2,
            token_generator_id=self.token_generator_id,
            token_info=self.token_info)

        WebAPIToken.objects.invalidate_token(token=webapi_token1.token)

        self._assert_token_is_invalid(webapi_token1)

        webapi_token2.refresh_from_db()
        self.assertTrue(webapi_token2.valid)

    def test_invalidate_token_with_reason(self):
        """Testing WebAPITokenManager.invalidate_token with an invalid
        reason given
        """
        self.spy_on(timezone.now, op=kgb.SpyOpReturn(timezone.now()))

        webapi_token1 = WebAPIToken.objects.generate_token(
            self.user,
            token_generator_id=self.token_generator_id,
            token_info=self.token_info)

        WebAPIToken.objects.invalidate_token(token=webapi_token1.token,
                                             invalid_reason='Revoked.')

        self._assert_token_is_invalid(webapi_token1, 'Revoked.')

    def test_invalidate_tokens(self):
        """Testing WebAPITokenManager.invalidate_tokens with a list of users"""
        self.spy_on(timezone.now, op=kgb.SpyOpReturn(timezone.now()))

        webapi_token1 = WebAPIToken.objects.generate_token(
            self.user,
            token_generator_id=self.token_generator_id,
            token_info=self.token_info)

        user2 = User.objects.create(username='test-user2')
        webapi_token2 = WebAPIToken.objects.generate_token(
            user2,
            token_generator_id=self.token_generator_id,
            token_info=self.token_info)

        user3 = User.objects.create(username='test-user3')
        webapi_token3 = WebAPIToken.objects.generate_token(
            user3,
            token_generator_id=self.token_generator_id,
            token_info=self.token_info)

        WebAPIToken.objects.invalidate_tokens(users=[self.user, user2],
                                              invalid_reason='Revoked.')

        self._assert_token_is_invalid(webapi_token1, 'Revoked.')
        self._assert_token_is_invalid(webapi_token2, 'Revoked.')

        webapi_token3.refresh_from_db()
        self.assertTrue(webapi_token3.valid)

    def test_invalidate_tokens_with_extra_query(self):
        """Testing WebAPITokenManager.invalidate_tokens with passing
        extra query parameters
        """
        self.spy_on(timezone.now, op=kgb.SpyOpReturn(timezone.now()))

        webapi_token1 = WebAPIToken.objects.generate_token(
            self.user,
            note='test',
            token_generator_id=self.token_generator_id,
            token_info=self.token_info)

        user2 = User.objects.create(username='test-user2')
        webapi_token2 = WebAPIToken.objects.generate_token(
            user2,
            token_generator_id=self.token_generator_id,
            token_info=self.token_info)

        user3 = User.objects.create(username='test-user3')
        webapi_token3 = WebAPIToken.objects.generate_token(
            user3,
            token_generator_id=self.token_generator_id,
            token_info=self.token_info)

        extra_query = models.Q(note='test')

        WebAPIToken.objects.invalidate_tokens(users=[self.user, user2],
                                              extra_query=extra_query,
                                              invalid_reason='Revoked.')

        self._assert_token_is_invalid(webapi_token1, 'Revoked.')

        webapi_token2.refresh_from_db()
        self.assertTrue(webapi_token2.valid)

        webapi_token3.refresh_from_db()
        self.assertTrue(webapi_token3.valid)

    def _assert_token_is_invalid(self, token, invalid_reason=''):
        """Assert that the given token is invalid.

        Args:
            token (djblets.webapi.models.BaseWebAPIToken):
                The token.

            invalid_reason (str):
                The invalid reason that should be set on the token. This
                defaults to an empty string.

        Raises:
            AssertionError:
                The token is not invalid.
        """
        token.refresh_from_db()

        self.assertFalse(token.valid)
        self.assertEqual(token.invalid_date, timezone.now())
        self.assertEqual(token.invalid_reason, invalid_reason)
