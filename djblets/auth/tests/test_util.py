"""Unit tests for djblets.auth.util."""

from __future__ import unicode_literals

from django import forms
from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware
from django.test.client import RequestFactory

from djblets.auth.util import validate_old_password, validate_test_cookie
from djblets.testing.testcases import TestCase


class ValidateOldPasswordTests(TestCase):
    """Unit tests for djblets.auth.util.validate_old_password."""

    class DummyForm(forms.Form):
        password = forms.CharField(required=False)
        alt_password = forms.CharField(required=False)

    def setUp(self):
        super(ValidateOldPasswordTests, self).setUp()

        self.user = User.objects.create_user(username='test-user',
                                             email='user@example.com',
                                             password='password')

    def test_with_password_matches(self):
        """Testing validate_old_password with password matching User's
        current password
        """
        form = self.DummyForm({
            'password': 'password',
        })
        validate_old_password(form, self.user)

        self.assertNotIn('password', form.errors)

    def test_with_password_does_not_match(self):
        """Testing validate_old_password with password not matching User's
        current password
        """
        form = self.DummyForm({
            'password': 'bad-password',
        })
        validate_old_password(form, self.user)

        self.assertIn('password', form.errors)
        self.assertEqual(form.errors['password'], ['Incorrect password.'])

    def test_with_existing_errors(self):
        """Testing validate_old_password with field already containing errors
        """
        form = self.DummyForm({
            'password': 'bad-password',
        })
        form.errors['password'] = form.error_class(['Something went wrong.'])
        validate_old_password(form, self.user)

        self.assertIn('password', form.errors)
        self.assertEqual(form.errors['password'], ['Something went wrong.'])

    def test_with_field_name_and_password_matches(self):
        """Testing validate_old_password with explicit field_name and
        password matching User's current password
        """
        form = self.DummyForm({
            'alt_password': 'password',
        })
        validate_old_password(form, self.user, field_name='alt_password')

        self.assertNotIn('alt_password', form.errors)

    def test_with_field_name_and_password_does_not_match(self):
        """Testing validate_old_password with explicit field name and password
        not matching User's current password
        """
        form = self.DummyForm({
            'alt_password': 'bad-password',
        })
        validate_old_password(form, self.user, field_name='alt_password')

        self.assertIn('alt_password', form.errors)
        self.assertEqual(form.errors['alt_password'], ['Incorrect password.'])

    def test_with_field_name_and_existing_errors(self):
        """Testing validate_old_password with explicit field name and field
        already containing errors
        """
        form = self.DummyForm({
            'alt_password': 'bad-password',
        })
        form.errors['alt_password'] = form.error_class(
            ['Something went wrong.'])
        validate_old_password(form, self.user, field_name='alt_password')

        self.assertIn('alt_password', form.errors)
        self.assertEqual(form.errors['alt_password'],
                         ['Something went wrong.'])


class ValidateTestCookieTests(TestCase):
    """Unit tests for djblets.auth.util.validate_test_cookie."""

    def setUp(self):
        super(ValidateTestCookieTests, self).setUp()

        class DummyForm(forms.Form):
            pass

        self.form = DummyForm()

        self.request = RequestFactory().post('/')
        SessionMiddleware().process_request(self.request)

    def test_with_test_cookie(self):
        """Testing validate_test_cookie with test cookie set"""
        self.request.session.set_test_cookie()

        validate_test_cookie(self.form, self.request)

        self.assertNotIn('submit', self.form.errors)

    def test_without_test_cookie(self):
        """Testing validate_test_cookie without test cookie set"""
        validate_test_cookie(self.form, self.request)

        self.assertIn('submit', self.form.errors)
        self.assertEqual(self.form.errors['submit'],
                         ['Cookies must be enabled.'])
