from __future__ import unicode_literals

from django.db.models.signals import post_save

from djblets.extensions.hooks import SignalHook
from djblets.integrations.integration import Integration
from djblets.integrations.manager import IntegrationManager
from djblets.integrations.tests.models import IntegrationConfig
from djblets.integrations.tests.testcases import IntegrationsTestCase


class DummyIntegration1(Integration):
    def initialize(self):
        self.dummy_initted = True
        self.hook = SignalHook(self, post_save, self._on_callback)

    def shutdown(self):
        self.dummy_initted = False

    def _on_callback(self, **kwargs):
        pass


class DummyIntegration2(Integration):
    def initialize(self):
        pass


class IntegrationTests(IntegrationsTestCase):
    """Unit tests for djblets.integrations.integration.Integration."""

    def setUp(self):
        super(IntegrationTests, self).setUp()

        self.manager = IntegrationManager(IntegrationConfig)
        self.integration = \
            self.manager.register_integration_class(DummyIntegration1)

    def test_init(self):
        """Testing Integration initialization"""
        self.assertEqual(self.integration.hooks, set())
        self.assertFalse(self.integration.enabled)
        self.assertFalse(hasattr(self.integration, 'dummy_initted'))

    def test_id(self):
        """Testing Integration.id"""
        self.assertEqual(self.integration.id, self.integration.integration_id)

    def test_enable_integration(self):
        """Testing Integration.enable_integration"""
        self.integration.enable_integration()

        self.assertTrue(self.integration.enabled)
        self.assertTrue(hasattr(self.integration, 'dummy_initted'))
        self.assertTrue(self.integration.dummy_initted)
        self.assertEqual(self.integration.hooks, {self.integration.hook})

    def test_disable_integration(self):
        """Testing Integration.disable_integration"""
        self.integration.enable_integration()
        self.integration.disable_integration()

        self.assertFalse(self.integration.enabled)
        self.assertTrue(hasattr(self.integration, 'dummy_initted'))
        self.assertFalse(self.integration.dummy_initted)
        self.assertEqual(self.integration.hooks, set())

    def test_get_configs(self):
        """Testing Integration.get_configs"""
        config1 = self.integration.create_config(name='Config 1',
                                                 enabled=True,
                                                 save=True)
        config2 = self.integration.create_config(name='Config 2',
                                                 enabled=True,
                                                 save=True)

        # Add some configs that shouldn't be returned.
        integration2 = \
            self.manager.register_integration_class(DummyIntegration2)
        self.integration.create_config(name='Config 3', save=True)
        integration2.create_config(name='Config 4', save=True)

        self.assertEqual(self.integration.get_configs(), [config1, config2])

    def test_get_configs_with_filter(self):
        """Testing Integration.get_configs with filter"""
        config1 = self.integration.create_config(name='Config 1',
                                                 enabled=True,
                                                 save=True)
        self.integration.create_config(name='Config 2',
                                       enabled=True,
                                       save=True)

        # Add some configs that shouldn't be returned.
        integration2 = \
            self.manager.register_integration_class(DummyIntegration2)
        self.integration.create_config(name='Config 3', save=True)
        integration2.create_config(name='Config 4', save=True)

        self.assertEqual(self.integration.get_configs(name='Config 1'),
                         [config1])

    def test_create_config(self):
        """Testing Integration.create_config"""
        config = self.integration.create_config(name='Config 1')
        self.assertFalse(config.enabled)
        self.assertIsNone(config.pk)

    def test_create_config_with_save(self):
        """Testing Integration.create_config with save=True"""
        config = self.integration.create_config(name='Config 1', save=True)
        self.assertFalse(config.enabled)
        self.assertIsNotNone(config.pk)
