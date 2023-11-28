"""Unit tests for the web API token auth backend."""

import datetime
import logging
import time

import kgb
from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.cache import cache
from django.http import HttpResponse
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.utils import timezone

from djblets.auth.ratelimit import _get_time_int
from djblets.testing.testcases import TestCase, TestModelsLoaderMixin
from djblets.webapi.auth.backends.api_tokens import (TokenAuthBackendMixin,
                                                     WebAPITokenAuthBackend)
from djblets.webapi.models import BaseWebAPIToken


class MyTestWebAPITokenModel(BaseWebAPIToken):
    """Mock WebAPI Token Model for testing purposes."""


class MyTestTokenAuthBackend(TokenAuthBackendMixin):
    """Mock Token Auth Backend for testing purposes."""

    api_token_model = MyTestWebAPITokenModel


@override_settings(AUTHENTICATION_BACKENDS=(
    'djblets.webapi.tests.test_api_auth_backend.MyTestTokenAuthBackend',
))

class WebAPITokenAuthBackendTests(kgb.SpyAgency,
                                  TestModelsLoaderMixin,
                                  TestCase):
    """Unit tests for the WebAPITokenAuthBackend."""

    def setUp(self):
        super(WebAPITokenAuthBackendTests, self).setUp()
        self.api_token_auth_backend = WebAPITokenAuthBackend()
        self.request = RequestFactory().get('/')

        middleware = SessionMiddleware(lambda request: HttpResponse(''))
        middleware(self.request)

    def tearDown(self):
        super(WebAPITokenAuthBackendTests, self).tearDown()
        cache.clear()

    def test_get_credentials_no_token_realm(self):
        """Testing Token Auth get_credentials with non-token realm"""
        self.request.META['HTTP_AUTHORIZATION'] = 'NotTokenRealm tokenHere'
        result = self.api_token_auth_backend.get_credentials(self.request)
        self.assertIsNone(result)

    def test_get_credentials_missing_credentials(self):
        """Testing Token Auth get_credentials with missing token"""
        self.request.META['HTTP_AUTHORIZATION'] = 'token'
        logger = logging.getLogger('djblets.webapi.auth.backends.api_tokens')
        self.spy_on(logger.warning)

        result = self.api_token_auth_backend.get_credentials(self.request)
        self.assertIsNone(result)

        warning_message = logger.warning.spy.last_call.args[0]
        self.assertTrue(warning_message.startswith(
            'WebAPITokenAuthBackend: Missing token in HTTP_AUTHORIZATION '
            'header'))

    def test_get_credentials_valid_credentials(self):
        """Testing Token Auth get_credentials with valid credentials"""
        token = 'myToken'
        self.request.META['HTTP_AUTHORIZATION'] = 'token %s' % token

        result = self.api_token_auth_backend.get_credentials(self.request)
        self.assertEqual(result, {'token': token})

    def test_authenticate_valid_credentials(self):
        """Testing Token Auth authenticate succeeds with valid credentials"""
        self.spy_on(timezone.now, op=kgb.SpyOpReturn(timezone.now()))

        token = 'invalidtoken123'
        self.user = User.objects.create_user(username='testuser')
        token_object = MyTestWebAPITokenModel.objects.create(user=self.user,
                                                             token=token)
        self.request.user = User()
        self.request.META['HTTP_AUTHORIZATION'] = 'token %s' % token

        result = self.api_token_auth_backend.authenticate(self.request)
        token_object.refresh_from_db(fields=('last_used',))

        self.assertEqual(result, (True, None, None))
        self.assertNotEqual(self.request.META['CSRF_COOKIE'], '')
        self.assertEqual(token_object.last_used, timezone.now())

    def test_authenticate_wrong_token(self):
        """Testing Token Auth authenticate failed with wrong token"""
        token = 'invalidtoken123'
        self.user = User.objects.create_user(username='testuser')
        MyTestWebAPITokenModel.objects.create(user=self.user, token=token)
        self.request.user = User()
        self.request.META['HTTP_AUTHORIZATION'] = 'token bad_token'

        result = self.api_token_auth_backend.authenticate(self.request)
        self.assertEqual(result, (False, None, None))

    @override_settings(LOGIN_LIMIT_RATE='5/m')
    def test_authenticate_rate_limit(self):
        """Testing Token Auth authenticate failed and exceeding
        number of failed login attempts allowed with default rate limit
        """
        token = 'myToken'
        self.user = User.objects.create_user(username='testratelimit')
        MyTestWebAPITokenModel.objects.create(user=self.user, token=token)
        self.request.user = self.user

        # Send invalid token to count number of failed login attempts
        self.request.META['HTTP_AUTHORIZATION'] = 'token bad_token'

        # Make sure that the time does not change during this test.
        self.spy_on(_get_time_int, op=kgb.SpyOpReturn(int(time.time())))

        # First 5 should be ok.
        for i in range(5):
            result = self.api_token_auth_backend.authenticate(self.request)
            self.assertEqual(result, (False, None, None))

        # The 6th should fail.
        result = self.api_token_auth_backend.authenticate(self.request)
        self.assertEqual(
            result,
            (False, 'Maximum number of login attempts exceeded.', None))

    @override_settings(LOGIN_LIMIT_RATE='3/s')
    def test_authenticate_custom_rate_limit_3_per_second(self):
        """Testing Token Auth authenticate failed and exceeding
        number of failed login attempts allowed with custom rate limit
        (3 failed attempts per second)
        """
        token = 'myRateLimitToken1'
        self.user = User.objects.create_user(username='testratelimit1')
        MyTestWebAPITokenModel.objects.create(user=self.user, token=token)
        self.request.user = self.user
        self.request.META['HTTP_AUTHORIZATION'] = 'token bad_token'

        # Make sure that the time does not change during this test.
        self.spy_on(_get_time_int, op=kgb.SpyOpReturn(int(time.time())))

        # First 3 should be ok.
        for i in range(3):
            result = self.api_token_auth_backend.authenticate(self.request)
            self.assertEqual(result, (False, None, None))

        # The 4th should fail.
        result = self.api_token_auth_backend.authenticate(self.request)
        self.assertEqual(
            result,
            (False, 'Maximum number of login attempts exceeded.', None))

    @override_settings(LOGIN_LIMIT_RATE='4/h')
    def test_authenticate_custom_rate_limit_4_per_hour(self):
        """Testing Token Auth authenticate failed and exceeding
        number of failed login attempts allowed with custom rate limit
        (4 failed attempts per hour)
        """
        token = 'myRateLimitToken2'
        self.user = User.objects.create_user(username='testratelimit2')
        MyTestWebAPITokenModel.objects.create(user=self.user, token=token)
        self.request.user = self.user
        self.request.META['HTTP_AUTHORIZATION'] = 'token bad_token'

        # Make sure that the time does not change during this test.
        self.spy_on(_get_time_int, op=kgb.SpyOpReturn(int(time.time())))

        # First 4 should be ok.
        for i in range(4):
            result = self.api_token_auth_backend.authenticate(self.request)
            self.assertEqual(result, (False, None, None))

        # 5th should fail.
        result = self.api_token_auth_backend.authenticate(self.request)
        self.assertEqual(
            result,
            (False, 'Maximum number of login attempts exceeded.', None))

    def test_authenticate_invalid_token(self):
        """Testing Token Auth authenticate fails when using an invalid token"""
        logger = logging.getLogger('djblets.webapi.auth.backends.api_tokens')
        self.spy_on(logger.debug)

        token = 'token123'
        self.user = User.objects.create_user(username='testuser')
        invalid_date = datetime.datetime(2022, 8, 2, 5, 45)

        MyTestWebAPITokenModel.objects.create(
            user=self.user,
            token=token,
            valid=False,
            invalid_date=timezone.make_aware(invalid_date))
        self.request.user = User()
        self.request.META['HTTP_AUTHORIZATION'] = 'token %s' % token

        result = self.api_token_auth_backend.authenticate(self.request)
        debug_message = logger.debug.spy.last_call.args[0]

        self.assertTrue(debug_message.endswith('The token is invalid.'))
        self.assertEqual(
            result,
            (
                False,
                (
                    'This API token became invalid on '
                    'Aug. 2, 2022, 10:45 a.m..'
                ),
                {
                    'WWW-Authenticate': 'Basic realm="Web API"',
                }
            ))

    def test_authenticate_invalid_token_with_reason(self):
        """Testing Token Auth authenticate fails when using an invalid token
        that has an invalid reason set
        """
        logger = logging.getLogger('djblets.webapi.auth.backends.api_tokens')
        self.spy_on(logger.debug)

        token = 'token123'
        self.user = User.objects.create_user(username='testuser')
        invalid_date = datetime.datetime(2022, 8, 2, 5, 45)

        token_object = MyTestWebAPITokenModel.objects.create(
            user=self.user,
            token=token,
            valid=False,
            invalid_date=timezone.make_aware(invalid_date),
            invalid_reason='Revoked.')
        self.request.user = User()
        self.request.META['HTTP_AUTHORIZATION'] = 'token %s' % token

        result = self.api_token_auth_backend.authenticate(self.request)
        debug_message = logger.debug.spy.last_call.args[0]

        self.assertTrue(debug_message.endswith('The token is invalid.'))
        self.assertEqual(
            result,
            (
                False,
                (
                    'This API token became invalid on '
                    'Aug. 2, 2022, 10:45 a.m.: %s'
                    % token_object.invalid_reason
                ),
                {
                    'WWW-Authenticate': 'Basic realm="Web API"',
                }
            ))

    def test_authenticate_expired_token(self):
        """Testing Token Auth authenticate fails when using an expired token"""
        logger = logging.getLogger('djblets.webapi.auth.backends.api_tokens')
        self.spy_on(logger.debug)

        token = 'token123'
        self.user = User.objects.create_user(username='testuser')
        invalid_date = datetime.datetime(2022, 8, 2, 5, 45)

        MyTestWebAPITokenModel.objects.create(
            user=self.user,
            token=token,
            expires=timezone.make_aware(invalid_date))
        self.request.user = User()
        self.request.META['HTTP_AUTHORIZATION'] = 'token %s' % token

        result = self.api_token_auth_backend.authenticate(self.request)
        debug_message = logger.debug.spy.last_call.args[0]

        self.assertTrue(debug_message.endswith('The token is expired.'))
        self.assertEqual(
            result,
            (
                False,
                (
                    'This API token expired on Aug. 2, 2022, 10:45 a.m..'
                ),
                {
                    'WWW-Authenticate': 'Basic realm="Web API"',
                }
            ))

    @override_settings(AUTHENTICATION_BACKENDS=(
        'djblets.webapi.tests.test_api_auth_backend.MyTestTokenAuthBackend',
        'djblets.webapi.auth.backends.oauth2_tokens.OAuth2TokenBackendMixin',
    ))
    def test_authenticate_valid_credentials_with_multiple_backends(self):
        """Testing Token Auth authenticate succeeds with valid credentials
        and having multiple authentication backends including one that does
        not implement a validate_token method
        """
        self.spy_on(timezone.now, op=kgb.SpyOpReturn(timezone.now()))

        token = 'token123'
        self.user = User.objects.create_user(username='testuser')
        token_object = MyTestWebAPITokenModel.objects.create(user=self.user,
                                                             token=token)
        self.request.user = User()
        self.request.META['HTTP_AUTHORIZATION'] = 'token %s' % token

        result = self.api_token_auth_backend.authenticate(self.request)
        token_object.refresh_from_db(fields=('last_used',))

        self.assertEqual(result, (True, None, None))
        self.assertNotEqual(self.request.META['CSRF_COOKIE'], '')
        self.assertEqual(token_object.last_used, timezone.now())

    def test_authenticate_deprecated_token(self):
        """Testing Token Auth authenticate succeeds and returns a deprecation
        notice in a response header when using a deprecated token
        """
        token = 'token123'
        self.user = User.objects.create_user(username='testuser')

        MyTestWebAPITokenModel.objects.create(
            user=self.user,
            token=token,
            token_generator_id='legacy_sha1')
        self.request.user = User()
        self.request.META['HTTP_AUTHORIZATION'] = 'token %s' % token

        result = self.api_token_auth_backend.authenticate(self.request)

        self.assertEqual(
            result,
            (
                True,
                None,
                {
                    'X-API-Token-Deprecated': (
                        'This token uses a deprecated format. The token can '
                        'still be used, but you should remove it and '
                        'generate a new one to take advantage of security '
                        'improvements.'
                    ),
                }
            ))
