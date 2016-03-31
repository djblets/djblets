"""Tests for djblets.avatars."""

from __future__ import unicode_literals

import logging

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.http import HttpRequest
from django.utils.html import mark_safe
from kgb import SpyAgency

from djblets.avatars.errors import DisabledServiceError
from djblets.avatars.registry import AvatarServiceRegistry
from djblets.avatars.services.base import AvatarService
from djblets.avatars.services.gravatar import GravatarService
from djblets.gravatars import get_gravatar_url_for_email
from djblets.registries.errors import ItemLookupError
from djblets.siteconfig.models import SiteConfiguration
from djblets.testing.testcases import TestCase


class DummyAvatarService(AvatarService):
    """An Avatar service for testing."""

    avatar_service_id = 'dummy'
    name = 'Dummy Avatar Service'

    def __init__(self, use_2x=False):
        """Initialize the dummy avatar service.

        Args:
            use_2x (bool):
                Whether or not the avatar service should provide high-DPI
                (retina) avatars.
        """
        self.use_2x = use_2x

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
            A dictionary of avatars. If ``use_2x`` was specified at
            initialization, a high-DPI avatar will be supplied.
        """
        urls = {
            '1x': mark_safe('http://example.com/avatar.png'),
            '2x': None,
        }

        if self.use_2x:
            urls['2x'] = mark_safe('http://example.com/avatar@2x.png')

        return urls


class AvatarServiceTests(SpyAgency, TestCase):
    """Tests for djblets.avatars.services.base."""

    def setUp(self):
        super(AvatarServiceTests, self).setUp()

        self.user = User(username='username',
                         email='username@example.com',
                         first_name='User',
                         last_name='Name')

    def test_default_urls(self):
        """Testing AvatarService.get_avatar_urls default implementation"""
        service = AvatarService()
        request = HttpRequest()

        with self.assertRaises(NotImplementedError):
            service.get_avatar_urls(request, self.user, 32)

    def test_render(self):
        """Testing AvatarService.render at 1x resolution."""
        service = DummyAvatarService()
        self.assertEqual(
            service.render(HttpRequest(), self.user, 24),
            '<img src="http://example.com/avatar.png" alt="User Name"'
            ' width="24" height="24"'
            ' srcset="http://example.com/avatar.png 1x" class="avatar">\n')

    def test_render_2x(self):
        """Testing AvatarService.render at 2x resolution."""
        service = DummyAvatarService(use_2x=True)
        self.assertEqual(
            service.render(HttpRequest(), self.user, 24),
            '<img src="http://example.com/avatar.png" alt="User Name"'
            ' width="24" height="24"'
            ' srcset="http://example.com/avatar.png 1x,'
            ' http://example.com/avatar@2x.png 2x" class="avatar">\n')

    def test_get_avatar_urls_caching(self):
        """Testing AvatarService.get_avatar_urls caching"""
        service = DummyAvatarService()
        request = HttpRequest()
        self.spy_on(service.get_avatar_urls_uncached)

        self.assertIs(service.get_avatar_urls(request, self.user, 48),
                      service.get_avatar_urls(request, self.user, 48))
        self.assertEqual(len(service.get_avatar_urls_uncached.calls), 1)

        self.assertIs(service.get_avatar_urls(request, self.user, 32),
                      service.get_avatar_urls(request, self.user, 32))
        self.assertEqual(len(service.get_avatar_urls_uncached.calls), 2)


class GravatarServiceTests(SpyAgency, TestCase):
    """Tests for djblets.avatars.services.gravatar."""

    def setUp(self):
        super(GravatarServiceTests, self).setUp()

        self.service = GravatarService()
        self.request = HttpRequest()
        self.user = User(username='username',
                         email='username@example.com',
                         first_name='User',
                         last_name='Name')

    def test_urls(self):
        """Testing GravatarService.get_avatar_urls"""
        urls = self.service.get_avatar_urls(self.request, self.user, 48)

        self.assertEqual(
            urls['1x'],
            get_gravatar_url_for_email(self.request, self.user.email, 48))
        self.assertEqual(
            urls['2x'],
            get_gravatar_url_for_email(self.request, self.user.email, 96))

    def test_render_safely(self):
        """Testing GravatarService.render renders to HTML safely"""
        with self.settings(GRAVATAR_RATING='G'):
            urls = self.service.get_avatar_urls(self.request, self.user, 48)

        self.assertIn('&', urls['1x'])
        self.assertNotIn('&amp;', urls['1x'])
        self.assertIn('&', urls['2x'])
        self.assertNotIn('&amp;', urls['2x'])


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
        service = DummyAvatarService()

        registry.register(service)
        self.assertFalse(registry.is_enabled(service.avatar_service_id))
        self.assertSetEqual(set(registry.enabled_services), set())

        registry.enable_service(service.avatar_service_id)
        self.assertTrue(registry.is_enabled(service.avatar_service_id))
        self.assertSetEqual(
            registry.enabled_services,
            {service})

    def test_disable_service(self):
        """Testing AvatarServiceRegistry.disable_service"""
        registry = AvatarServiceRegistry()
        self.assertFalse(registry.is_enabled(
            GravatarService.avatar_service_id))
        registry.enable_service(GravatarService.avatar_service_id)

        self.assertTrue(registry.is_enabled(GravatarService.avatar_service_id))
        self.assertSetEqual(set(registry.enabled_services),
                            set(registry))

        registry.disable_service(GravatarService.avatar_service_id)
        self.assertFalse(registry.is_enabled(
            GravatarService.avatar_service_id))
        self.assertSetEqual(set(registry.enabled_services), set())

    def test_set_enabled_services(self):
        """Testing AvatarServiceRegistry.enabled_services setter"""
        registry = AvatarServiceRegistry()

        dummy_service = DummyAvatarService()
        registry.register(dummy_service)

        gravatar_service = registry.get('avatar_service_id',
                                        GravatarService.avatar_service_id)

        registry.enabled_services = [dummy_service, gravatar_service]

        self.assertEqual(registry.enabled_services,
                         {dummy_service, gravatar_service})

    def test_get_enabled_services_populated(self):
        """Testing AvatarServiceRegistry.enabled_services getter calls
        populate()
        """
        dummy_service = DummyAvatarService()

        class TestRegistry(AvatarServiceRegistry):
            def populate(self):
                if self.populated:
                    return

                super(TestRegistry, self).populate()
                self.enabled_services = [dummy_service]

            def get_defaults(self):
                yield dummy_service

        registry = TestRegistry()
        self.assertFalse(registry.populated)

        enabled_services = set(registry.enabled_services)
        self.assertTrue(registry.populated)
        self.assertSetEqual(enabled_services, {dummy_service})

    def test_set_enabled_services_invalid_service(self):
        """Testing AvatarServiceRegistry.enabled_services setter with an
        unregistered service
        """
        registry = AvatarServiceRegistry()

        dummy_service = DummyAvatarService()

        gravatar_service = registry.get('avatar_service_id',
                                        GravatarService.avatar_service_id)

        with self.assertRaises(ItemLookupError):
            registry.enabled_services = [dummy_service, gravatar_service]

        self.assertEqual(registry.enabled_services, set())

    def test_default_service(self):
        """Testing AvatarServiceRegistry.default_service"""
        registry = AvatarServiceRegistry()

        dummy_serivce = DummyAvatarService()
        gravatar_service = registry.get('avatar_service_id',
                                        GravatarService.avatar_service_id)
        registry.register(dummy_serivce)
        registry.enabled_services = [dummy_serivce, gravatar_service]

        self.assertIsNone(registry.default_service)

        registry.set_default_service(dummy_serivce)
        self.assertEqual(registry.default_service, dummy_serivce)

        registry.set_default_service(gravatar_service)
        self.assertEqual(registry.default_service, gravatar_service)

        registry.set_default_service(None)
        self.assertIsNone(registry.default_service)

    def test_set_default_service_invalid(self):
        """Testing AvatarServiceRegistry.set_default_service setter with an
        unregistered service
        """
        registry = AvatarServiceRegistry()
        dummy_service = DummyAvatarService()

        self.assertIsNone(registry.default_service)

        with self.assertRaises(ItemLookupError):
            registry.set_default_service(dummy_service)

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

        gravatar_service = registry.get('avatar_service_id',
                                        GravatarService.avatar_service_id)

        self.assertTrue(registry.populated)
        self.assertEqual(registry.default_service, gravatar_service)
        self.assertEqual(registry.enabled_services, {gravatar_service})

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
        dummy_service = DummyAvatarService()

        class TestRegistry(AvatarServiceRegistry):
            def get_defaults(self):
                yield dummy_service
                yield GravatarService()

        self.spy_on(logging.error)
        self.siteconfig.set(AvatarServiceRegistry.ENABLED_SERVICES_KEY,
                            [DummyAvatarService.avatar_service_id])
        self.siteconfig.set(AvatarServiceRegistry.DEFAULT_SERVICE_KEY,
                            DummyAvatarService.avatar_service_id)
        self.siteconfig.save()

        registry = TestRegistry()
        self.assertIs(registry.default_service, dummy_service)
        self.assertFalse(logging.error.spy.called)

    def test_unregister(self):
        """Testing AvatarServiceRegistry.unregister"""
        registry = AvatarServiceRegistry()
        gravatar_service = registry.get('avatar_service_id',
                                        GravatarService.avatar_service_id)

        registry.enable_service(GravatarService.avatar_service_id)

        self.assertSetEqual(registry.enabled_services, {gravatar_service})
        registry.unregister(gravatar_service)
        self.assertSetEqual(registry.enabled_services, set())

    def test_disable_default(self):
        """Testing AvatarServiceRegistry.disable_service unsets the default
        service
        """
        registry = AvatarServiceRegistry()
        registry.enable_service(GravatarService.avatar_service_id)
        registry.set_default_service(
            registry.get('avatar_service_id',
                         GravatarService.avatar_service_id))

        registry.disable_service(GravatarService.avatar_service_id)
        self.assertIsNone(registry.default_service)

    def test_disable_default_from_setter(self):
        """Testing AvatarServiceRegistry.enabled_services setter unsets the
        default services
        """
        registry = AvatarServiceRegistry()
        registry.enable_service(GravatarService.avatar_service_id)
        registry.set_default_service(
            registry.get('avatar_service_id',
                         GravatarService.avatar_service_id))

        registry.enabled_services = []
        self.assertIsNone(registry.default_service)
