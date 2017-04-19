"""Unit tests for the web API token auth backend."""

from __future__ import unicode_literals

import logging

from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware
from django.db import models
from django.test.client import RequestFactory
from django.test.utils import override_settings
from kgb import SpyAgency

from djblets.testing.testcases import TestCase, TestModelsLoaderMixin
from djblets.webapi.auth.backends.api_tokens import (TokenAuthBackendMixin,
                                                     WebAPITokenAuthBackend)


class TestWebAPITokenModel(models.Model):
    """Mock WebAPI Token Model for testing purposes."""

    user = models.ForeignKey(User, related_name='webapi_tokens')
    token = models.CharField(max_length=40, unique=True)


class TestTokenAuthBackend(TokenAuthBackendMixin):
    """Mock Token Auth Backend for testing purposes."""

    api_token_model = TestWebAPITokenModel


@override_settings(AUTHENTICATION_BACKENDS=(
    'djblets.webapi.tests.test_api_auth_backend.TestTokenAuthBackend',
))
class WebAPITokenAuthBackendTests(SpyAgency, TestModelsLoaderMixin, TestCase):
    """Unit tests for the WebAPITokenAuthBackend."""

    tests_app = 'djblets.webapi.tests'

    def setUp(self):
        super(WebAPITokenAuthBackendTests, self).setUp()

        self.api_token_auth_backend = WebAPITokenAuthBackend()
        self.request = RequestFactory().get('/')
        SessionMiddleware().process_request(self.request)

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
        """Testing Token Auth authenticate succeeds"""
        token = 'invalidtoken123'
        self.user = User.objects.create_user(username='testuser')
        TestWebAPITokenModel.objects.create(user=self.user, token=token)
        self.request.user = User()
        self.request.META['HTTP_AUTHORIZATION'] = 'token %s' % token

        result = self.api_token_auth_backend.authenticate(self.request)
        self.assertEqual(result, (True, None, None))
        self.assertNotEqual(self.request.META['CSRF_COOKIE'], '')

    def test_authenticate_wrong_token(self):
        """Testing Token Auth authenticate failed with wrong token"""
        token = 'invalidtoken123'
        self.user = User.objects.create_user(username='testuser')
        TestWebAPITokenModel.objects.create(user=self.user, token=token)
        self.request.user = User()
        self.request.META['HTTP_AUTHORIZATION'] = 'token bad_token'

        result = self.api_token_auth_backend.authenticate(self.request)
        self.assertEqual(result, (False, None, None))
