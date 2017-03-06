from __future__ import unicode_literals

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models.signals import post_delete, post_save

from djblets.cache.synchronizer import GenerationSynchronizer
from djblets.integrations.errors import (IntegrationAlreadyRegisteredError,
                                         IntegrationNotRegisteredError,
                                         IntegrationRegistrationError)
from djblets.integrations.manager import (IntegrationManager,
                                          get_integration_managers,
                                          shutdown_integration_managers)
from djblets.integrations.integration import Integration
from djblets.integrations.tests.models import IntegrationConfig
from djblets.integrations.tests.testcases import IntegrationsTestCase


class BrokenIntegration(Integration):
    def __init__(self, *args, **kwargs):
        assert False


class DummyIntegration1(Integration):
    def initialize(self):
        pass


class DummyIntegration2(Integration):
    def initialize(self):
        pass


class IntegrationManagerTests(IntegrationsTestCase):
    """Unit tests for djblets.integrations.manager.IntegrationManager."""

    def setUp(self):
        super(IntegrationManagerTests, self).setUp()

        # Reset integration IDs, so we can check them appropriately in tests.
        DummyIntegration1.integration_id = None
        DummyIntegration2.integration_id = None

    def test_init_without_app(self):
        """Testing IntegrationManager initialization without INSTALLED_APPS"""
        msg = ('IntegrationManager requires djblets.integrations to be '
               'listed in settings.INSTALLED_APPS.')

        installed_apps = list(settings.INSTALLED_APPS)
        installed_apps.remove('djblets.integrations')

        with self.settings(INSTALLED_APPS=installed_apps):
            with self.assertRaisesMessage(ImproperlyConfigured, msg):
                IntegrationManager(IntegrationConfig)

    def test_init_without_middleware(self):
        """Testing IntegrationManager initialization without
        MIDDLEWARE_CLASSES
        """
        msg = ('IntegrationManager requires djblets.integrations.middleware.'
               'IntegrationsMiddleware to be listed in '
               'settings.MIDDLEWARE_CLASSES')

        middleware_classes = list(settings.MIDDLEWARE_CLASSES)
        middleware_classes.remove('djblets.integrations.middleware.'
                                  'IntegrationsMiddleware')

        with self.settings(MIDDLEWARE_CLASSES=middleware_classes):
            with self.assertRaisesMessage(ImproperlyConfigured, msg):
                IntegrationManager(IntegrationConfig)

    def test_shutdown(self):
        """Testing IntegrationManager.shutdown"""
        manager = IntegrationManager(IntegrationConfig)
        instance = manager.register_integration_class(DummyIntegration1)
        instance.enable_integration()

        self.assertTrue(instance.enabled)
        self.assertNotEqual(manager._integration_classes, {})
        self.assertNotEqual(manager._integration_instances, {})
        self.assertTrue(manager.is_expired())

        manager.shutdown()

        self.assertFalse(instance.enabled)
        self.assertEqual(manager._integration_classes, {})
        self.assertEqual(manager._integration_instances, {})
        self.assertFalse(manager.is_expired())

    def test_get_integration_classes(self):
        """Testing IntegrationManager.get_integration_classes"""
        manager = IntegrationManager(IntegrationConfig)
        manager.register_integration_class(DummyIntegration1)
        manager.register_integration_class(DummyIntegration2)

        classes = manager.get_integration_classes()
        self.assertEqual(set(classes), {DummyIntegration1, DummyIntegration2})

    def test_get_integration(self):
        """Testing IntegrationManager.get_integration"""
        manager = IntegrationManager(IntegrationConfig)
        manager.register_integration_class(DummyIntegration1)
        manager.register_integration_class(DummyIntegration2)

        integration = manager.get_integration(DummyIntegration1.integration_id)
        self.assertEqual(integration.__class__, DummyIntegration1)

        integration = manager.get_integration(DummyIntegration2.integration_id)
        self.assertEqual(integration.__class__, DummyIntegration2)

    def test_get_integration_with_invalid_id(self):
        """Testing IntegrationManager.get_integration with invalid ID"""
        manager = IntegrationManager(IntegrationConfig)

        with self.assertRaises(IntegrationNotRegisteredError):
            manager.get_integration('foobar')

    def test_get_integration_configs(self):
        """Testing IntegrationManager.get_integration_configs with all
        configurations
        """
        manager = IntegrationManager(IntegrationConfig)
        integration1 = manager.register_integration_class(DummyIntegration1)
        integration2 = manager.register_integration_class(DummyIntegration2)

        config1 = integration1.create_config(enabled=True, save=True)
        config2 = integration1.create_config(enabled=False, save=True)
        config3 = integration2.create_config(enabled=True, save=True)

        with self.assertNumQueries(1):
            configs = manager.get_integration_configs()

        self.assertEqual(set(configs), {config1, config2, config3})

    def test_get_integration_configs_with_class(self):
        """Testing IntegrationManager.get_integration_configs with instance
        class
        """
        manager = IntegrationManager(IntegrationConfig)
        integration1 = manager.register_integration_class(DummyIntegration1)
        integration2 = manager.register_integration_class(DummyIntegration2)

        config1 = integration1.create_config(enabled=True, save=True)
        config2 = integration1.create_config(enabled=False, save=True)
        integration2.create_config(enabled=True, save=True)

        with self.assertNumQueries(1):
            configs = manager.get_integration_configs(integration1)

        self.assertEqual(set(configs), {config1, config2})

    def test_get_integration_configs_with_filter(self):
        """Testing IntegrationManager.get_integration_configs with filter"""
        manager = IntegrationManager(IntegrationConfig)
        integration1 = manager.register_integration_class(DummyIntegration1)
        integration2 = manager.register_integration_class(DummyIntegration2)

        config1 = integration1.create_config(enabled=False, save=True)
        integration1.create_config(enabled=True, save=True)
        integration2.create_config(enabled=True, save=True)

        with self.assertNumQueries(1):
            configs = manager.get_integration_configs(integration1,
                                                      enabled=False)

        self.assertEqual(set(configs), {config1})

    def test_get_integration_configs_caches(self):
        """Testing IntegrationManager.get_integration_configs caches results"""
        manager = IntegrationManager(IntegrationConfig)
        integration1 = manager.register_integration_class(DummyIntegration1)

        config1 = integration1.create_config(enabled=True, save=True)
        config2 = integration1.create_config(enabled=False, save=True)

        with self.assertNumQueries(1):
            manager.get_integration_configs()

        with self.assertNumQueries(0):
            configs = manager.get_integration_configs()

        self.assertEqual(set(configs), {config1, config2})

    def test_clear_configs_cache(self):
        """Testing IntegrationManager.clear_configs_cache"""
        manager = IntegrationManager(IntegrationConfig)

        with self.assertNumQueries(1):
            manager.get_integration_configs()

        with self.assertNumQueries(0):
            manager.get_integration_configs()

        manager.clear_configs_cache()

        with self.assertNumQueries(1):
            manager.get_integration_configs()

    def test_clear_configs_cache_for_class(self):
        """Testing IntegrationManager.clear_configs_cache for class"""
        manager = IntegrationManager(IntegrationConfig)

        with self.assertNumQueries(1):
            manager.get_integration_configs(DummyIntegration1)

        with self.assertNumQueries(0):
            manager.get_integration_configs(DummyIntegration1)

        manager.clear_configs_cache(DummyIntegration1)

        with self.assertNumQueries(1):
            manager.get_integration_configs(DummyIntegration1)

    def test_clear_all_configs_cache(self):
        """Testing IntegrationManager.clear_all_configs_cache"""
        manager = IntegrationManager(IntegrationConfig)

        with self.assertNumQueries(1):
            manager.get_integration_configs(DummyIntegration1)

        with self.assertNumQueries(0):
            manager.get_integration_configs(DummyIntegration1)

        manager.clear_all_configs_cache()

        with self.assertNumQueries(1):
            manager.get_integration_configs(DummyIntegration1)

    def test_is_expired_new_instance(self):
        """Testing IntegrationManager.is_expired on a new instance"""
        manager = IntegrationManager(IntegrationConfig)

        self.assertFalse(manager.is_expired())

    def test_is_expired_after_registration(self):
        """Testing IntegrationManager.is_expired after new registration"""
        manager = IntegrationManager(IntegrationConfig)
        manager.register_integration_class(DummyIntegration1)

        self.assertTrue(manager.is_expired())

    def test_is_expired_after_config_saved(self):
        """Testing IntegrationManager.is_expired after config saved"""
        manager = IntegrationManager(IntegrationConfig)

        self.assertFalse(manager.is_expired())
        post_save.send(sender=IntegrationConfig)
        self.assertTrue(manager.is_expired())

    def test_is_expired_after_config_deleted(self):
        """Testing IntegrationManager.is_expired after config deleted"""
        manager = IntegrationManager(IntegrationConfig)

        self.assertFalse(manager.is_expired())
        post_delete.send(sender=IntegrationConfig)
        self.assertTrue(manager.is_expired())

    def test_is_expired_after_other_process_updates(self):
        """Testing IntegrationManager.is_expired after another process updates
        the configuration state
        """
        manager = IntegrationManager(IntegrationConfig)
        self.assertFalse(manager.is_expired())

        gen_sync = GenerationSynchronizer(manager._gen_sync.cache_key,
                                          normalize_cache_key=False)
        gen_sync.mark_updated()

        self.assertTrue(manager.is_expired())

    def test_check_expired_when_expired(self):
        """Testing IntegrationManager.check_expired when expired"""
        manager = IntegrationManager(IntegrationConfig)

        # Cache some state.
        integration1 = manager.register_integration_class(DummyIntegration1)
        integration1.create_config(enabled=True, save=True)
        manager.get_integration_configs(DummyIntegration1)

        integration2 = manager.register_integration_class(DummyIntegration2)
        manager.get_integration_configs(DummyIntegration1)

        # Make sure the integration isn't enabled. This would be because we
        # haven't refreshed yet.
        self.assertFalse(integration1.enabled)
        self.assertFalse(integration2.enabled)
        self.assertNotEqual(manager._integration_configs, {})

        # Check expired state.
        self.assertTrue(manager.is_expired())
        manager.check_expired()

        # Make sure state has been updated and caches cleared.
        self.assertFalse(manager.is_expired())
        self.assertTrue(integration1.enabled)
        self.assertFalse(integration2.enabled)
        self.assertEqual(manager._integration_configs, {})

    def test_check_expired_when_not_expired(self):
        """Testing IntegrationManager.check_expired when not expired"""
        manager = IntegrationManager(IntegrationConfig)

        # Cache some state.
        integration = manager.register_integration_class(DummyIntegration1)
        integration.create_config(enabled=True, save=True)
        manager.get_integration_configs(DummyIntegration1)

        # Make sure the integration isn't enabled. This would be because we
        # haven't refreshed yet.
        self.assertFalse(integration.enabled)
        self.assertNotEqual(manager._integration_configs, {})

        # Fake having the latest state.
        manager._needs_recalc = False

        # Check expired state, without actually expiring it.
        self.assertFalse(manager.is_expired())
        manager.check_expired()

        # Make sure state has not changed.
        self.assertFalse(manager.is_expired())
        self.assertFalse(integration.enabled)
        self.assertNotEqual(manager._integration_configs, {})

    def test_register_integration_class(self):
        """Testing IntegrationManager.register_integration_class"""
        manager = IntegrationManager(IntegrationConfig)

        integration = manager.register_integration_class(DummyIntegration1)
        self.assertEqual(integration.__class__, DummyIntegration1)

        integration_id = DummyIntegration1.integration_id
        self.assertEqual(
            integration_id,
            'djblets.integrations.tests.test_manager.DummyIntegration1')

        self.assertIn(integration_id, manager._integration_classes)
        self.assertEqual(manager._integration_classes[integration_id],
                         DummyIntegration1)
        self.assertIn(integration_id, manager._integration_instances)
        self.assertEqual(manager._integration_instances[integration_id],
                         integration)

    def test_register_integration_class_with_already_registered(self):
        """Testing IntegrationManager.register_integration_class with
        already registered class
        """
        manager = IntegrationManager(IntegrationConfig)
        manager.register_integration_class(DummyIntegration1)

        with self.assertRaises(IntegrationAlreadyRegisteredError):
            manager.register_integration_class(DummyIntegration1)

    def test_register_integration_class_with_construct_error(self):
        """Testing IntegrationManager.register_integration_class with
        construction error
        """
        manager = IntegrationManager(IntegrationConfig)

        with self.assertRaises(IntegrationRegistrationError):
            manager.register_integration_class(BrokenIntegration)

    def test_unregister_integration_class(self):
        """Testing IntegrationManager.unregister_integration_class"""
        manager = IntegrationManager(IntegrationConfig)
        manager.register_integration_class(DummyIntegration1)
        manager.unregister_integration_class(DummyIntegration1)

        integration_id = DummyIntegration1.integration_id

        self.assertNotIn(integration_id, manager._integration_classes)
        self.assertNotIn(integration_id, manager._integration_instances)

    def test_unregister_integration_class_with_enabled_integration(self):
        """Testing IntegrationManager.unregister_integration_class with
        enabled integration
        """
        manager = IntegrationManager(IntegrationConfig)
        integration = manager.register_integration_class(DummyIntegration1)

        integration_id = DummyIntegration1.integration_id
        integration.enabled = True

        manager.unregister_integration_class(DummyIntegration1)

        self.assertFalse(integration.enabled)
        self.assertNotIn(integration_id, manager._integration_classes)
        self.assertNotIn(integration_id, manager._integration_instances)

    def test_unregister_integration_class_with_unregistered(self):
        """Testing IntegrationManager.unregister_integration_class with
        unregistered integration
        """
        manager = IntegrationManager(IntegrationConfig)

        with self.assertRaises(IntegrationNotRegisteredError):
            manager.unregister_integration_class(DummyIntegration1)

    def test_get_integration_managers(self):
        """Testing get_integration_managers"""
        manager1 = IntegrationManager(IntegrationConfig)
        manager2 = IntegrationManager(IntegrationConfig)

        self.assertEqual(set(get_integration_managers()), {manager1, manager2})

    def test_shutdown_integration_managers(self):
        """Testing shutdown_integration_managers"""
        manager1 = IntegrationManager(IntegrationConfig)
        self.assertTrue(manager1.enabled)

        manager2 = IntegrationManager(IntegrationConfig)
        self.assertTrue(manager2.enabled)

        shutdown_integration_managers()

        self.assertEqual(get_integration_managers(), [])
        self.assertFalse(manager1.enabled)
        self.assertFalse(manager2.enabled)
