from __future__ import unicode_literals

from djblets.integrations.integration import Integration
from djblets.integrations.manager import IntegrationManager
from djblets.integrations.tests.models import IntegrationConfig
from djblets.integrations.tests.testcases import IntegrationsTestCase


class DummyIntegration1(Integration):
    default_settings = {
        'foo': 'default-foo',
    }

    def initialize(self):
        pass


class IntegrationConfigTests(IntegrationsTestCase):
    """Unit tests for djblets.integrations.models.BaseIntegrationConfig."""

    def setUp(self):
        super(IntegrationConfigTests, self).setUp()

        self.manager = IntegrationManager(IntegrationConfig)
        self.integration = \
            self.manager.register_integration_class(DummyIntegration1)
        self.config = self.integration.create_config()
        self.config.manager = self.manager

    def test_integration(self):
        """Testing BaseIntegrationConfig.integration"""
        self.assertEqual(self.config.integration, self.integration)

    def test_get(self):
        """Testing BaseIntegrationConfig.get"""
        self.config.settings['foo'] = 'bar'
        self.assertEqual(self.config.get('foo'), 'bar')

    def test_get_with_integration_defaults(self):
        """Testing BaseIntegrationConfig.get with integration defaults"""
        self.assertEqual(self.config.get('foo'), 'default-foo')

    def test_get_with_default(self):
        """Testing BaseIntegrationConfig.get with default"""
        self.assertEqual(self.config.get('new-key', 'my-default'),
                         'my-default')

    def test_set(self):
        """Testing BaseIntegrationConfig.set"""
        self.config.set('my-key', 'my-value')
        self.assertEqual(self.config.settings.get('my-key'), 'my-value')
