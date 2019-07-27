"""Unit tests for djblets.extensions.views."""

from __future__ import unicode_literals

from django import forms
from django.conf.urls import url
from django.contrib import admin
from django.contrib.auth.models import User
from django.test.utils import override_settings
from kgb import SpyAgency

from djblets.extensions.extension import Extension
from djblets.extensions.forms import SettingsForm
from djblets.extensions.tests.base import ExtensionTestsMixin
from djblets.extensions.views import configure_extension
from djblets.testing.testcases import TestCase


class ViewTests(SpyAgency, ExtensionTestsMixin, TestCase):
    """Unit tests for djblets.extensions.views."""

    def setUp(self):
        class TestExtension(Extension):
            admin_urlconf = []
            is_configurable = True

        super(ViewTests, self).setUp()

        self.extension = self.setup_extension(TestExtension)

    def test_configure_extension_saving(self):
        """Testing configure_extension with saving settings"""
        class TestSettingsForm(SettingsForm):
            mykey = forms.CharField(max_length=100)

        self.spy_on(self.manager.get_enabled_extension,
                    call_fake=lambda *args: self.extension)

        urlpatterns[:] = [
            url('^config/$', configure_extension,
                {
                    'ext_class': type(self.extension),
                    'form_class': TestSettingsForm,
                    'extension_manager': self.manager,
                }),
            url('', admin.site.urls),
        ]

        User.objects.create_superuser(username='admin',
                                      password='admin',
                                      email='admin@example.com')

        with override_settings(ROOT_URLCONF=__name__):
            self.client.login(username='admin', password='admin')

            # Fetch once for the CSRF token.
            response = self.client.get('/config/')
            self.assertEqual(response.status_code, 200)

            # Save new settings in the form.
            response = self.client.post('/config/', data={
                'mykey': 'myvalue',
            })
            self.assertEqual(response.status_code, 302)

        self.assertEqual(self.extension.settings.get('mykey'), 'myvalue')


# A placeholder for any urlpatterns that need to be set for tests.
urlpatterns = []
