"""Unit tests for the web API basic auth backend."""

from __future__ import unicode_literals

import base64
import logging

from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.middleware import SessionMiddleware
from django.test.client import RequestFactory
from kgb import SpyAgency

from djblets.testing.testcases import TestCase
from djblets.webapi.auth.backends.basic import WebAPIBasicAuthBackend


class WebAPIBasicAuthBackendTests(SpyAgency, TestCase):
    """Unit tests for the WebAPIBasicAuthBackend."""

    def setUp(self):
        super(WebAPIBasicAuthBackendTests, self).setUp()

        self.basic_auth_backend = WebAPIBasicAuthBackend()
        self.request = RequestFactory().get('/')
        SessionMiddleware().process_request(self.request)
        self.request.user = AnonymousUser()
        self.user = User.objects.create_user(
            username='testuser',
            email='testcase@test.com',
            password='testpassword')

    def test_get_credentials_no_basic_realm(self):
        """Testing Basic Auth get_credentials with non-basic realm"""
        self.request.META['HTTP_AUTHORIZATION'] = 'Token tokenHere'
        result = self.basic_auth_backend.get_credentials(self.request)
        self.assertIsNone(result)

    def test_get_credentials_valid_credentials(self):
        """Testing Basic Auth get_credentials with credentials"""
        encoded_credentials = base64.b64encode(b'my-username:my-password')
        header = 'Basic %s' % encoded_credentials.decode('utf-8')
        self.request.META['HTTP_AUTHORIZATION'] = header

        result = self.basic_auth_backend.get_credentials(self.request)

        self.assertEqual(result, {
            'username': 'my-username',
            'password': 'my-password',
        })

    def test_get_credentials_malformed_credentials(self):
        """Testing Basic Auth get_credentials with malformed credentials"""
        self.request.META['HTTP_AUTHORIZATION'] = (
            'Basic %s'
            % base64.b64encode(b'Some malfomred credentials').decode('utf-8')
        )

        logger = logging.getLogger('djblets.webapi.auth.backends.basic')
        self.spy_on(logger.warning)

        result = self.basic_auth_backend.get_credentials(self.request)
        warning_message = logger.warning.spy.last_call.args[0]

        self.assertIsNone(result)
        self.assertTrue(warning_message.startswith(
                        'Failed to parse HTTP_AUTHORIZATION header'))

    def test_authenticate_valid_credentials(self):
        """Testing Basic Auth authenicate with valid credentials"""
        header = ('Basic %s'
                  % base64.b64encode(b'testuser:testpassword').decode('utf-8'))
        self.request.META['HTTP_AUTHORIZATION'] = header

        result = self.basic_auth_backend.authenticate(self.request)

        self.assertEqual(result, (True, None, None))

    def test_authenticate_wrong_header(self):
        """Testing Basic Auth authenicate with wrong header"""
        header = ('Token %s'
                  % base64.b64encode(b'testuser:testpassword').decode('utf-8'))
        self.request.META['HTTP_AUTHORIZATION'] = header

        result = self.basic_auth_backend.authenticate(self.request)

        self.assertIsNone(result)

    def test_authenticate_wrong_password(self):
        """Testing Basic Auth authenicate with invalid credentials"""
        header = (
            'Basic %s'
            % base64.b64encode(b'testuser:wrongpassword').decode('utf-8'))
        self.request.META['HTTP_AUTHORIZATION'] = header

        result = self.basic_auth_backend.authenticate(self.request)

        self.assertEqual(result, (False, None, None))

    def test_login_with_credentials_valid_credentials(self):
        """Testing Basic Auth login_with_credentials with valid credentials"""
        encoded_credentials = base64.b64encode(b'testuser:testpassword')
        header = 'Basic %s' % encoded_credentials.decode('utf-8')
        self.request.META['HTTP_AUTHORIZATION'] = header

        result = self.basic_auth_backend.login_with_credentials(
            self.request,
            username='testuser',
            password='testpassword')

        self.assertEqual(result, (True, None, None))

    def test_login_bypass_authentication(self):
        """Testing Basic Auth login_with_credentials with currently logged in
        user
        """
        encoded_credentials = base64.b64encode(b'testuser:testpassword')
        header = 'Basic %s' % encoded_credentials.decode('utf-8')
        self.request.META['HTTP_AUTHORIZATION'] = header
        self.request.user = self.user

        result = self.basic_auth_backend.login_with_credentials(
            self.request,
            username='testuser',
            password='testpassword')

        self.assertEqual(result, (True, None, None))

    def test_login_with_credentials_incorrect_pass(self):
        """Testing Basic Auth login_with_credentials with incorrect password"""
        encoded_credentials = base64.b64encode(b'testuser:wrongpassword')
        header = 'Basic %s' % encoded_credentials.decode('utf-8')
        self.request.META['HTTP_AUTHORIZATION'] = header

        result = self.basic_auth_backend.login_with_credentials(
            self.request,
            username='testuser',
            password='wrongpassword')

        self.assertEqual(result, (False, None, None))

    def test_login_with_credentials_incorrect_user(self):
        """Testing Basic Auth login_with_credentials with invalid user"""
        encoded_credentials = base64.b64encode(b'wronguser:testpassword')
        header = 'Basic %s' % encoded_credentials.decode('utf-8')
        self.request.META['HTTP_AUTHORIZATION'] = header
        self.request.user = self.user

        result = self.basic_auth_backend.login_with_credentials(
            self.request,
            username='wronguser',
            password='testpassword')

        self.assertEqual(result, (False, None, None))

    def test_validate_credentials_valid(self):
        """Testing Basic Auth validate_credentials with valid credentials"""
        self.request.user = self.user
        result = self.basic_auth_backend.validate_credentials(
            self.request,
            username='testuser',
            password='testpassword')

        self.assertEqual(result, (True, None, None))

    def test_validate_credentials_invalid_user(self):
        """Testing Basic Auth validate_credentials with invalid user"""
        result = self.basic_auth_backend.validate_credentials(
            self.request,
            username='testuser',
            password='testpassword')

        self.assertIsNone(result)

    def test_validate_credentials_invalid_credentials(self):
        """Testing Basic Auth validate_credentials with invalid credentials"""
        self.request.user = self.user
        result = self.basic_auth_backend.validate_credentials(
            self.request,
            username='differentuser',
            password='testpassword')

        self.assertIsNone(result)

    def test_clean_credentials_for_display_removes_credentials(self):
        """Testing Basic Auth clean_credentials_for_display"""
        credentials = {
            'api': 'has exact match',
            'oauth2_token': 'has partial match',
            'apikey2': 'no match as word but contains match sub string',
            'secre': 'no match, similar only',
        }
        removed_credential = '************'
        clean_credentials = \
            self.basic_auth_backend.clean_credentials_for_display(credentials)

        self.assertEqual(clean_credentials['api'], removed_credential)
        self.assertEqual(clean_credentials['oauth2_token'], removed_credential)
        self.assertEqual(clean_credentials['apikey2'], removed_credential)
        self.assertEqual(clean_credentials['secre'], credentials['secre'])
