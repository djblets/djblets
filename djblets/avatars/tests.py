"""Tests for djblets.avatars."""

from __future__ import unicode_literals

import logging

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.test.client import RequestFactory
from django.utils.html import mark_safe
from kgb import SpyAgency

from djblets.avatars.errors import DisabledServiceError
from djblets.avatars.registry import AvatarServiceRegistry
from djblets.avatars.settings import AvatarSettingsManager
from djblets.avatars.services import (AvatarService,
                                      GravatarService,
                                      URLAvatarService)
from djblets.gravatars import get_gravatar_url_for_email
from djblets.registries.errors import ItemLookupError
from djblets.siteconfig.models import SiteConfiguration
from djblets.testing.testcases import TestCase


class DummySettingsManager(AvatarSettingsManager):
    """A dummy settings manager that always returns the same settings."""

    @property
    def avatar_service_id(self):
        return self._avatar_service_id

    @avatar_service_id.setter
    def avatar_service_id(self, value):
        self._avatar_service_id = value

    @property
    def configuration(self):
        """The configuration.

        Returns:
            dict: The configuration."""
        return self._settings

    def __init__(self, avatar_service_id, settings):
        """Initialize the settings manager.

        Args:
            avatar_service_id (unicode):
                The avatar service ID.

            settings (dict):
                The avatar services configuration.
        """
        super(DummySettingsManager, self).__init__(None)

        self._avatar_service_id = avatar_service_id
        self._settings = settings

    def configuration_for(self, avatar_service_id):
        """Return the configuration for the specified service.

        Args:
            avatar_service_id (unicode):
                The unique ID for the avatar service.

        Returns:
            dict: Configuration for the given avatar service.
        """
        return self._settings.setdefault(avatar_service_id, {})

    def save(self):
        """Save the configuration.

        This method intentionally left blank.
        """
        pass

    def __call__(self, *args, **kwargs):
        """Return the avatar settings manager.

        The :py:class:`~djblets.avatars.registry.AvatarServiceRegistry
        expects a ``type`` instead of an instance, so we override ``call()`` to
        pretend to be one.

        Args:
            *args (tuple):
                Ignored positional arguments.

            **kwargs (dict)
                Ignored keyword arguments.

        Returns:
            DummySettingsManager:
            This instance.
        """
        return self


class DummyAvatarService(AvatarService):
    """An Avatar service for testing."""

    avatar_service_id = 'dummy'
    name = 'Dummy Avatar Service'

    def get_avatar_urls_uncached(self, request, user, size=None):
        """Return the avatar urls.

        Args:
            request (django.http.HttpRequest):
                The HTTP request.

            user (django.contrib.auth.models.User):
                The user.

            size (int, optional):
                The requested avatar size.

        Returns:
            dict:
            A dictionary of avatars.
        """
        return {
            '1x': mark_safe('http://example.com/avatar.png'),
            '2x': None,
        }


class DummyHighDPIAvatarService(DummyAvatarService):
    """An avatar service for testing that includes high DPI avatars."""

    avatar_service_id = 'dummy-hidpi'
    name = 'Dummy Avatar Service (High DPI)'

    def get_avatar_urls_uncached(self, request, user, size=None):
        """Return the avatar urls.

        Args:
            request (django.http.HttpRequest):
                The HTTP request.

            user (django.contrib.auth.models.User):
                The user.

            size (int, optional):
                The requested avatar size.

        Returns:
            dict:
            A dictionary of avatars.
        """
        urls = super(DummyHighDPIAvatarService, self).get_avatar_urls_uncached(
            request, user, size)
        urls['2x'] = mark_safe('http://example.com/avatar@2x.png')

        return urls


class AvatarServiceTests(SpyAgency, TestCase):
    """Tests for djblets.avatars.services.base."""

    @classmethod
    def setUpClass(cls):
        super(AvatarServiceTests, cls).setUpClass()
        cls._request_factory = RequestFactory()

    def setUp(self):
        super(AvatarServiceTests, self).setUp()

        self.request = self._request_factory.get('/')
        self.user = User(username='username',
                         email='username@example.com',
                         first_name='User',
                         last_name='Name')

    def test_default_urls(self):
        """Testing AvatarService.get_avatar_urls default implementation"""
        service = AvatarService(DummySettingsManager)

        with self.assertRaises(NotImplementedError):
            service.get_avatar_urls(self.request, self.user, 32)

    def test_render(self):
        """Testing AvatarService.render at 1x resolution."""
        service = DummyAvatarService(DummySettingsManager)
        self.assertHTMLEqual(
            service.render(self.request, self.user, 24),
            '<img src="http://example.com/avatar.png" alt="User Name"'
            ' width="24" height="24"'
            ' srcset="http://example.com/avatar.png 1x" class="avatar">\n')

    def test_render_2x(self):
        """Testing AvatarService.render at 2x resolution."""
        service = DummyHighDPIAvatarService(DummySettingsManager)
        self.assertHTMLEqual(
            service.render(self.request, self.user, 24),
            '<img src="http://example.com/avatar.png" alt="User Name"'
            ' width="24" height="24"'
            ' srcset="http://example.com/avatar.png 1x,'
            ' http://example.com/avatar@2x.png 2x" class="avatar">\n')

    def test_get_avatar_urls_caching(self):
        """Testing AvatarService.get_avatar_urls caching"""
        service = DummyAvatarService(DummySettingsManager)
        self.spy_on(service.get_avatar_urls_uncached)

        self.assertIs(service.get_avatar_urls(self.request, self.user, 48),
                      service.get_avatar_urls(self.request, self.user, 48))
        self.assertEqual(len(service.get_avatar_urls_uncached.calls), 1)

        self.assertIs(service.get_avatar_urls(self.request, self.user, 32),
                      service.get_avatar_urls(self.request, self.user, 32))
        self.assertEqual(len(service.get_avatar_urls_uncached.calls), 2)


class GravatarServiceTests(TestCase):
    """Tests for djblets.avatars.services.gravatar."""

    @classmethod
    def setUpClass(cls):
        super(GravatarServiceTests, cls).setUpClass()
        cls._request_factory = RequestFactory()

    def setUp(self):
        super(GravatarServiceTests, self).setUp()

        self.service = GravatarService(DummySettingsManager)
        self.request = self._request_factory.get('/')
        self.user = User(username='username',
                         email='username@example.com',
                         first_name='User',
                         last_name='Name')

    def test_urls(self):
        """Testing GravatarService.get_avatar_urls"""
        urls = self.service.get_avatar_urls(self.request, self.user, 48)

        self.assertEqual(
            urls['1x'],
            get_gravatar_url_for_email(email=self.user.email, size=48))
        self.assertEqual(
            urls['2x'],
            get_gravatar_url_for_email(email=self.user.email, size=96))

    def test_render_safely(self):
        """Testing GravatarService.render renders to HTML safely"""
        with self.settings(GRAVATAR_RATING='G'):
            urls = self.service.get_avatar_urls(self.request, self.user, 48)

        self.assertIn('&', urls['1x'])
        self.assertNotIn('&amp;', urls['1x'])
        self.assertIn('&', urls['2x'])
        self.assertNotIn('&amp;', urls['2x'])


class URLAvatarServiceTests(SpyAgency, TestCase):
    """Tests for djblets.avatars.services.url."""

    def setUp(self):
        super(URLAvatarServiceTests, self).setUp()
        self.settings_manager = DummySettingsManager(
            URLAvatarService.avatar_service_id, {})
        self.service = URLAvatarService(self.settings_manager)

    def test_setup(self):
        """Testing URLAvatarService.setup"""
        urls = {
            '1x': 'http://example.com/foo.jpg',
            '2x': 'http://example.com/bar@2x.jpg',
        }
        self.service.setup(User(), urls)
        self.assertEqual(urls,
                         self.settings_manager.configuration_for(
                             URLAvatarService.avatar_service_id))
        self.assertIsNot(urls,
                         self.settings_manager.configuration_for(
                             URLAvatarService.avatar_service_id))

    def test_get_urls_uncached(self):
        """Testing URLAvatarService.get_urls_uncached"""
        urls = {
            '1x': 'http://example.com/foo.jpg',
            '2x': 'http://example.com/bar@2x.jpg',
        }
        self.settings_manager.configuration_for(
            URLAvatarService.avatar_service_id).update(urls)

        self.assertEqual(
            urls,
            self.service.get_avatar_urls_uncached(User(), None))


class AvatarServiceRegistryTests(SpyAgency, TestCase):
    """Tests for djblets.avatars.registry."""

    def setUp(self):
        super(AvatarServiceRegistryTests, self).setUp()
        site = Site.objects.get_current()
        self.siteconfig = SiteConfiguration.objects.create(site=site)

    def tearDown(self):
        super(AvatarServiceRegistryTests, self).tearDown()
        self.siteconfig.delete()

    def test_enable_service(self):
        """Testing AvatarServiceRegistry.enable_service"""
        registry = AvatarServiceRegistry()
        registry.register(DummyAvatarService)
        self.assertFalse(registry.is_enabled(DummyAvatarService))
        self.assertSetEqual(set(registry.enabled_services), set())

        registry.enable_service(DummyAvatarService)
        self.assertTrue(registry.is_enabled(DummyAvatarService))
        self.assertSetEqual(
            registry.enabled_services,
            {DummyAvatarService})

    def test_disable_service(self):
        """Testing AvatarServiceRegistry.disable_service"""
        registry = AvatarServiceRegistry()
        self.assertFalse(registry.is_enabled(GravatarService))
        registry.enable_service(GravatarService)

        self.assertTrue(registry.is_enabled(GravatarService))
        self.assertSetEqual(set(registry.enabled_services),
                            {GravatarService})

        registry.disable_service(GravatarService)
        self.assertFalse(registry.is_enabled(GravatarService))
        self.assertSetEqual(set(registry.enabled_services), set())

    def test_set_enabled_services(self):
        """Testing AvatarServiceRegistry.enabled_services setter"""
        registry = AvatarServiceRegistry()

        registry.register(DummyAvatarService)

        registry.enabled_services = [DummyAvatarService, GravatarService]

        self.assertEqual(registry.enabled_services,
                         {DummyAvatarService, GravatarService})

    def test_get_enabled_services_populated(self):
        """Testing AvatarServiceRegistry.enabled_services getter calls
        populate()
        """
        class TestRegistry(AvatarServiceRegistry):
            settings_manager_class = DummySettingsManager

            def populate(self):
                if self.populated:
                    return

                super(TestRegistry, self).populate()
                self.enabled_services = [DummyAvatarService]

            def get_defaults(self):
                yield DummyAvatarService

        registry = TestRegistry()
        self.assertFalse(registry.populated)

        enabled_services = set(registry.enabled_services)
        self.assertTrue(registry.populated)
        self.assertSetEqual(enabled_services, {DummyAvatarService})

    def test_set_enabled_services_invalid_service(self):
        """Testing AvatarServiceRegistry.enabled_services setter with an
        unregistered service
        """
        registry = AvatarServiceRegistry()

        with self.assertRaises(ItemLookupError):
            registry.enabled_services = [DummyAvatarService, GravatarService]

        self.assertEqual(registry.enabled_services, set())

    def test_default_service(self):
        """Testing AvatarServiceRegistry.default_service"""
        registry = AvatarServiceRegistry()
        registry.register(DummyAvatarService)

        registry.enabled_services = [DummyAvatarService, GravatarService]

        self.assertIsNone(registry.default_service)

        registry.set_default_service(DummyAvatarService)
        self.assertIsInstance(registry.default_service, DummyAvatarService)

        registry.set_default_service(GravatarService)
        self.assertIsInstance(registry.default_service, GravatarService)

        registry.set_default_service(None)
        self.assertIsNone(registry.default_service)

    def test_set_default_service_invalid(self):
        """Testing AvatarServiceRegistry.set_default_service setter with an
        unregistered service
        """
        registry = AvatarServiceRegistry()

        self.assertIsNone(registry.default_service)

        with self.assertRaises(ItemLookupError):
            registry.set_default_service(DummyAvatarService)

        self.assertIsNone(registry.default_service)

    def test_set_default_service_disabled(self):
        """Testing AvatarServiceRegistry.set_default_service setter with a
        disabled service
        """
        registry = AvatarServiceRegistry()
        gravatar_service = registry.get('avatar_service_id',
                                        GravatarService.avatar_service_id)

        self.assertIsNone(registry.default_service)

        with self.assertRaises(DisabledServiceError):
            registry.set_default_service(gravatar_service)

        self.assertIsNone(registry.default_service)

    def test_populate(self):
        """Testing AvatarServiceRegistry.populate with site configuration
        settings
        """
        self.spy_on(logging.error)

        self.siteconfig.set(AvatarServiceRegistry.ENABLED_SERVICES_KEY,
                            [GravatarService.avatar_service_id])
        self.siteconfig.set(AvatarServiceRegistry.DEFAULT_SERVICE_KEY,
                            GravatarService.avatar_service_id)
        self.siteconfig.save()

        registry = AvatarServiceRegistry()
        registry.populate()

        self.assertTrue(registry.populated)
        self.assertIsInstance(registry.default_service, GravatarService)
        self.assertEqual(registry.enabled_services, {GravatarService})

        self.assertFalse(logging.error.spy.called)

    def test_populate_invalid_default(self):
        """Testing AvatarServiceRegistry.populate with an invalid default
        registry in the site configuration
        """
        self.spy_on(logging.error)

        self.siteconfig.set(AvatarServiceRegistry.DEFAULT_SERVICE_KEY,
                            DummyAvatarService.avatar_service_id)
        self.siteconfig.save()

        registry = AvatarServiceRegistry()

        self.assertEqual(registry.default_service, None)
        self.assertEqual(registry.enabled_services, set())

        self.assertTrue(logging.error.spy.called)

        siteconfig = SiteConfiguration.objects.get_current()
        self.assertIsNone(
            siteconfig.get(AvatarServiceRegistry.DEFAULT_SERVICE_KEY))

    def test_populate_disabled_default(self):
        """Testing AvatarServiceRegistry.populate with a disabled default
        registry in the site configuration
        """
        self.spy_on(logging.error)

        self.siteconfig.set(AvatarServiceRegistry.DEFAULT_SERVICE_KEY,
                            GravatarService.avatar_service_id)
        self.siteconfig.save()

        registry = AvatarServiceRegistry()

        self.assertEqual(registry.default_service, None)
        self.assertEqual(registry.enabled_services, set())

        self.assertTrue(logging.error.spy.called)

        siteconfig = SiteConfiguration.objects.get_current()
        self.assertIsNone(
            siteconfig.get(AvatarServiceRegistry.DEFAULT_SERVICE_KEY))

    def test_populate_invalid_enabled_services(self):
        """Testing AvatarServiceRegistry.populate with an unregistered
        service
        """
        self.spy_on(logging.error)
        self.siteconfig.set(AvatarServiceRegistry.ENABLED_SERVICES_KEY,
                            [DummyAvatarService.avatar_service_id])
        self.siteconfig.save()

        registry = AvatarServiceRegistry()

        self.assertEqual(registry.default_service, None)
        self.assertEqual(registry.enabled_services, set())

        self.assertTrue(logging.error.spy.called)

        siteconfig = SiteConfiguration.objects.get_current()
        self.assertListEqual(
            siteconfig.get(AvatarServiceRegistry.ENABLED_SERVICES_KEY),
            [])

    def test_populate_custom_services(self):
        """Testing AvatarServiceRegistry.populate for subclasses with custom
        default registrations
        """
        class TestRegistry(AvatarServiceRegistry):
            settings_manager_class = DummySettingsManager(None, {})
            default_avatar_service_classes = [DummyAvatarService,
                                              GravatarService]

        self.spy_on(logging.error)
        self.siteconfig.set(AvatarServiceRegistry.ENABLED_SERVICES_KEY,
                            [DummyAvatarService.avatar_service_id])
        self.siteconfig.set(AvatarServiceRegistry.DEFAULT_SERVICE_KEY,
                            DummyAvatarService.avatar_service_id)
        self.siteconfig.save()

        registry = TestRegistry()
        self.assertIsInstance(registry.default_service, DummyAvatarService)
        self.assertFalse(logging.error.spy.called)

    def test_unregister(self):
        """Testing AvatarServiceRegistry.unregister"""
        registry = AvatarServiceRegistry()
        gravatar_service = registry.get('avatar_service_id',
                                        GravatarService.avatar_service_id)

        registry.enable_service(GravatarService)

        self.assertSetEqual(registry.enabled_services, {gravatar_service})
        registry.unregister(gravatar_service)
        self.assertSetEqual(registry.enabled_services, set())

    def test_disable_default(self):
        """Testing AvatarServiceRegistry.disable_service unsets the default
        service
        """
        registry = AvatarServiceRegistry()
        registry.enable_service(GravatarService)
        registry.set_default_service(GravatarService)

        registry.disable_service(GravatarService)
        self.assertIsNone(registry.default_service)

    def test_disable_default_from_setter(self):
        """Testing AvatarServiceRegistry.enabled_services setter unsets the
        default services
        """
        registry = AvatarServiceRegistry()
        registry.enable_service(GravatarService)
        registry.set_default_service(GravatarService)

        registry.enabled_services = []
        self.assertIsNone(registry.default_service)

    def test_for_user(self):
        """Testing AvatarServiceRegistry.for_user"""

        class DummyAvatarServiceRegistry(AvatarServiceRegistry):
            settings_manager_class = DummySettingsManager('dummy', {})
            default_avatar_service_classes = [
                GravatarService,
                DummyAvatarService,
                DummyHighDPIAvatarService,
            ]

        registry = DummyAvatarServiceRegistry()
        registry.enable_service(GravatarService, save=False)
        registry.enable_service(DummyAvatarService, save=False)
        registry.enable_service(DummyHighDPIAvatarService, save=False)
        registry.set_default_service(GravatarService, save=False)

        # Case 1: Their set avatar service.
        self.assertIsInstance(registry.for_user(None), DummyAvatarService)

        # Case 2: A requested avatar service.
        self.assertIsInstance(
            registry.for_user(None,
                              DummyHighDPIAvatarService.avatar_service_id),
            DummyHighDPIAvatarService)

        # Case 3: The default avatar service
        registry.settings_manager_class._avatar_service_id = None
        self.assertIsInstance(registry.for_user(None), GravatarService)
