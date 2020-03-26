"""Unit tests for djblets.integrations.forms.IntegrationConfigForm."""

from __future__ import unicode_literals

from django.test.client import RequestFactory

from djblets.integrations.forms import IntegrationConfigForm
from djblets.integrations.integration import Integration
from djblets.integrations.manager import IntegrationManager
from djblets.integrations.tests.models import IntegrationConfig
from djblets.integrations.tests.testcases import IntegrationsTestCase


class DummyIntegration(Integration):
    def initialize(self):
        pass

    def shutdown(self):
        pass

    def _on_callback(self, **kwargs):
        pass


class IntegrationConfigFormTests(IntegrationsTestCase):
    """Unit tests for djblets.integrations.forms.IntegrationConfigForm."""

    def setUp(self):
        super(IntegrationConfigFormTests, self).setUp()

        self.manager = IntegrationManager(IntegrationConfig)
        self.integration = \
            self.manager.register_integration_class(DummyIntegration)
        request_factory = RequestFactory()
        self.request = request_factory.get('/getSomeForm/')

        self.form = IntegrationConfigForm(
            integration=self.integration,
            request=self.request,
            instance=None,
            data={
                'enabled': True,
                'name': 'FakeName',
            })
        self.form.full_clean()
        self.form.save()

    def test_config(self):
        """Testing IntegrationConfigForm.config returns the config instance"""
        self.assertIsInstance(self.form.config, IntegrationConfig)

    def test_get_key_value_model_field(self):
        """Testing IntegrationConfigForm.get_key_value() returns values from
        form data"""
        self.assertEqual(self.form.get_key_value('name'), 'FakeName')
        self.assertTrue(self.form.get_key_value('enabled'))

    def test_set_key_value_model_field(self):
        """Testing IntegrationConfigForm.set_key_value() overrides form
        data"""
        name_field = 'name'
        expected_value = 'NewName'
        self.form.set_key_value(name_field, expected_value)
        self.assertEqual(self.form.get_key_value(name_field), expected_value)

    def test_set_key_value_non_model_field(self):
        """Testing IntegrationConfigForm.set_key_value() sets custom non-field
        data"""
        test_field = 'new_non_model_field'
        self.form.set_key_value(test_field, True)
        self.assertTrue(self.form.get_key_value(test_field))
