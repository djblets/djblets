"""Tests for authentication-related views."""

from __future__ import unicode_literals

from django.core.cache import cache
from django.http import HttpResponseRedirect
from djblets.util.compat.django.shortcuts import render
from django.test.client import Client
from kgb import SpyAgency

from djblets.auth.forms import RegistrationForm
from djblets.testing.testcases import TestCase


class ViewsTests(SpyAgency, TestCase, Client):
    """Tests for djblets.auth.views"""

    def tearDown(self):
        super(ViewsTests, self).tearDown()
        cache.clear()

    def test_register_without_post_method(self):
        """Testing register view when request is not a post method"""
        self.spy_on(render)

        response = self.client.get('/auth/register/')

        self.assertIsNotNone(response.context)
        self.assertIsInstance(response.context['form'], RegistrationForm)
        self.assertTrue(render.called)

    def test_register_with_valid_form(self):
        """Testing register view when a valid form is received"""
        request_headers = {
            'username': 'user123',
            'password1': 'password1',
            'password2': 'password1',
            'email': 'test@mailinator.com',
        }
        # Make a get request first to ensure we have a csrf token
        # generated. By doing so, we can ensure our post request and form
        # are valid.
        self.client.get('/auth/register/')

        self.spy_on(render)

        response = self.client.post('/auth/register/', request_headers)

        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertIsNone(response.context)
        self.assertFalse(render.called)

    def test_register_with_invalid_form(self):
        """Testing register view when an invalid form is received"""
        request_headers = {
            'username': 'user123',
            'password1': 'password1',
            'password2': 'password1',
            'email': 'invalid email',
        }
        self.client.get('/auth/register/')

        self.spy_on(render)

        response = self.client.post('/auth/register/', request_headers)

        self.assertIsNotNone(response.context)
        self.assertIsInstance(response.context['form'], RegistrationForm)
        self.assertTrue(render.called)
