"""Unit tests for djblets.auth.forms.RegistrationForm."""

from __future__ import unicode_literals

from django.contrib.auth.models import User

from djblets.auth.forms import RegistrationForm
from djblets.testing.testcases import TestCase


class RegistrationFormTests(TestCase):
    """Unit tests for djblets.auth.forms.RegistrationForm."""

    def test_clean_password2_with_match(self):
        """Testing RegistrationForm.clean_password2 with password2 field
        matching password1 field
        """
        form = RegistrationForm(data={
            'username': 'test',
            'email': 'test@example.com',
            'password1': 'password',
            'password2': 'password',
        })
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['password1'], 'password')
        self.assertEqual(form.cleaned_data['password2'], 'password')

    def test_clean_password2_without_match(self):
        """Testing RegistrationForm.clean_password2 with password2 field
        not matching password1 field
        """
        form = RegistrationForm(data={
            'username': 'test',
            'email': 'test@example.com',
            'password1': 'password',
            'password2': 'bad-password',
        })
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {
            'password2': ['Passwords must match'],
        })

    def test_save(self):
        """Testing RegistrationForm.save"""
        form = RegistrationForm(data={
            'username': 'test',
            'email': 'test@example.com',
            'password1': 'password',
            'password2': 'password',
            'first_name': 'Test',
            'last_name': 'User',
        })
        self.assertTrue(form.is_valid())

        user = form.save()

        self.assertIsNotNone(user)
        self.assertIsNotNone(user.pk)
        self.assertEqual(user.username, 'test')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.last_name, 'User')
        self.assertTrue(user.check_password('password'))

    def test_save_with_username_taken(self):
        """Testing RegistrationForm.save with username already taken"""
        User.objects.create(username='test')

        form = RegistrationForm(data={
            'username': 'test',
            'email': 'test@example.com',
            'password1': 'password',
            'password2': 'password',
            'first_name': 'Test',
            'last_name': 'User',
        })
        self.assertTrue(form.is_valid())

        user = form.save()

        self.assertIsNone(user)
        self.assertIn('username', form.errors)
        self.assertEqual(form.errors['username'],
                         ['Sorry, this username is taken.'])
