"""Unit tests for djblets.extensions.views."""

from django import forms
from django.contrib import admin
from django.contrib.auth.models import User
from django.test.utils import override_settings
from django.urls import path

from djblets.extensions.extension import Extension
from djblets.extensions.forms import SettingsForm
from djblets.extensions.testing import ExtensionTestCaseMixin
from djblets.extensions.views import configure_extension
from djblets.testing.testcases import TestCase


class MyTestExtension(Extension):
    admin_urlconf = []
    is_configurable = True


class ViewTests(ExtensionTestCaseMixin, TestCase):
    """Unit tests for djblets.extensions.views."""

    extension_class = MyTestExtension

    def test_configure_extension_saving(self):
        """Testing configure_extension with saving settings"""
        class TestSettingsForm(SettingsForm):
            mykey = forms.CharField(max_length=100)

        urlpatterns[:] = [
            path('config/', configure_extension, kwargs={
                'ext_class': type(self.extension),
                'form_class': TestSettingsForm,
                'extension_manager': self.extension_mgr,
            }),
            path('', admin.site.urls),
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
