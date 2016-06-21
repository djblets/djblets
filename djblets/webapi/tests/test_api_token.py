from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.db import models

from djblets.testing.testcases import TestCase
from djblets.webapi.models import BaseWebAPIToken
from kgb import SpyAgency


class WebAPIToken(BaseWebAPIToken):
    my_field = models.BooleanField(default=False)


class WebAPITokenManagerTests(SpyAgency, TestCase):
    def setUp(self):
        super(WebAPITokenManagerTests, self).setUp()

        self.user = User.objects.create(username='test-user')
        self.spy_on(WebAPIToken.save, call_original=False)

    def test_generate_token_with_defaults(self):
        """Testing WebAPITokenManager.generate_token with default arguments"""
        webapi_token = WebAPIToken.objects.generate_token(self.user)

        self.assertEqual(webapi_token.user, self.user)
        self.assertEqual(webapi_token.policy, {})
        self.assertEqual(webapi_token.note, '')
        self.assertEqual(webapi_token.my_field, False)
        self.assertIsNotNone(webapi_token.token)

    def test_generate_token_with_custom_field(self):
        """Testing WebAPITokenManager.generate_token with custom field"""
        webapi_token = WebAPIToken.objects.generate_token(self.user,
                                                          my_field=True)

        self.assertEqual(webapi_token.my_field, True)
