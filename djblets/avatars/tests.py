"""Tests for djblets.avatars."""

from __future__ import unicode_literals

import uuid

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.storage import get_storage_class
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.client import RequestFactory
from django.utils.html import mark_safe
from django.utils.safestring import SafeText
from kgb import SpyAgency

from djblets.avatars.errors import DisabledServiceError
from djblets.avatars.forms import AvatarServiceConfigForm, AvatarSettingsForm
from djblets.avatars.registry import AvatarServiceRegistry
from djblets.avatars.settings import AvatarSettingsManager
from djblets.avatars.services import (AvatarService,
                                      FallbackService,
                                      FileUploadService,
                                      GravatarService,
                                      URLAvatarService)
from djblets.avatars.services.base import logger
from djblets.configforms.pages import ConfigPage
from djblets.gravatars import get_gravatar_url_for_email
from djblets.privacy.consent import ConsentData, get_consent_tracker
from djblets.registries.errors import ItemLookupError
from djblets.siteconfig.models import SiteConfiguration
from djblets.testing.decorators import requires_user_profile
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
            dict: The configuration.
        """
        return self._settings

    def __init__(self, avatar_service_id, settings={}):
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


class AvatarServiceTestCase(TestCase):
    """Base test case for avatar service backend tests."""

    #: The avatar service class.
    avatar_service_cls = None

    @classmethod
    def setUpClass(cls):
        super(AvatarServiceTestCase, cls).setUpClass()

        cls._request_factory = RequestFactory()

    def setUp(self):
        super(AvatarServiceTestCase, self).setUp()

        self.settings_manager = DummySettingsManager(
            self.avatar_service_cls.avatar_service_id)
        self.service = self.avatar_service_cls(self.settings_manager)
        self.request = self._request_factory.get('/')
        self.user = User(username='username',
                         email='username@example.com',
                         first_name='User',
                         last_name='Name')


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

    def test_get_avatar_urls(self):
        """Testing AvatarService.get_avatar_urls"""
        service = AvatarService(DummySettingsManager)

        self.spy_on(logger.error)

        self.assertEqual(
            service.get_avatar_urls(request=self.request,
                                    user=self.user,
                                    size=32),
            {
                '1x': '',
                '2x': '',
                '3x': '',
            }
        )

        self.assertTrue(logger.error.spy.called)

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

    def test_get_avatar_urls_with_request_none(self):
        """Testing AvatarService.get_avatar_urls with request=None"""
        service = DummyAvatarService(DummySettingsManager)

        self.assertEqual(
            service.get_avatar_urls(request=None,
                                    user=self.user,
                                    size=32),
            {
                '1x': 'http://example.com/avatar.png',
                '2x': None,
            }
        )

    def test_default_etag_data(self):
        """Testing AvatarService.get_etag_dagta default implementation"""
        service = DummyAvatarService(DummySettingsManager)

        self.assertEqual(
            service.get_etag_data(self.user), ['dummy', None])

    def test_render(self):
        """Testing AvatarService.render at 1x resolution."""
        service = DummyAvatarService(DummySettingsManager)
        html = service.render(request=self.request,
                              user=self.user,
                              size=24)

        self.assertIsInstance(html, SafeText)
        self.assertHTMLEqual(
            html,
            '<img src="http://example.com/avatar.png" alt="username"'
            ' width="24" height="24"'
            ' srcset="http://example.com/avatar.png 1x"'
            ' class="avatar djblets-o-avatar">')

    def test_render_2x(self):
        """Testing AvatarService.render at 2x resolution."""
        service = DummyHighDPIAvatarService(DummySettingsManager)
        html = service.render(request=self.request,
                              user=self.user,
                              size=24)

        self.assertIsInstance(html, SafeText)
        self.assertHTMLEqual(
            html,
            '<img src="http://example.com/avatar.png" alt="username"'
            ' width="24" height="24"'
            ' srcset="http://example.com/avatar.png 1x,'
            ' http://example.com/avatar@2x.png 2x"'
            ' class="avatar djblets-o-avatar">')

    def test_render_with_request_none(self):
        """Testing AvatarService.render with request=None"""
        self.request = None
        self.test_render()


class FallbackServiceTests(AvatarServiceTestCase):
    """Tests for djblets.avatars.services.fallback.FallbackService."""

    avatar_service_cls = FallbackService

    def test_urls(self):
        """Testing FallbackService.get_avatar_urls"""
        urls = self.service.get_avatar_urls(self.request, self.user, 48)

        self.assertEqual(
            urls,
            {
                '1x': '',
                '2x': '',
                '3x': '',
            })

    def test_render(self):
        """Testing FallbackService.render"""
        html = self.service.render(request=self.request,
                                   user=self.user,
                                   size=48)
        self.assertIsInstance(html, SafeText)

        self.assertHTMLEqual(
            html,
            '<span class="avatar djblets-o-avatar djblets-o-avatar-fallback"'
            ' title="username"'
            ' style="background: hsl(174, 60%, 80%); display: inline-block;'
            ' width: 48px; line-height: 48px; font-size: 16px;'
            ' text-align: center;">'
            'US'
            '</span>')

    def test_render_with_request_none(self):
        """Testing FallbackService.render with request=None"""
        self.request = None
        self.test_render()


class GravatarServiceTests(AvatarServiceTestCase):
    """Tests for djblets.avatars.services.gravatar."""

    avatar_service_cls = GravatarService

    def test_urls(self):
        """Testing GravatarService.get_avatar_urls"""
        urls = self.service.get_avatar_urls(self.request, self.user, 48)

        self.assertEqual(
            urls['1x'],
            get_gravatar_url_for_email(email=self.user.email, size=48))
        self.assertEqual(
            urls['2x'],
            get_gravatar_url_for_email(email=self.user.email, size=96))

    def test_get_avatar_urls_with_rating(self):
        """Testing GravatarService.get_avatar_urls with GRAVATAR_RATING"""
        with self.settings(GRAVATAR_RATING='G'):
            urls = self.service.get_avatar_urls(self.request, self.user, 48)

        self.assertIn('&', urls['1x'])
        self.assertNotIn('&amp;', urls['1x'])
        self.assertIn('&', urls['2x'])
        self.assertNotIn('&amp;', urls['2x'])

    def test_render(self):
        """Testing GravatarService.render"""
        html = self.service.render(request=self.request,
                                   user=self.user,
                                   size=48)

        self.assertIsInstance(html, SafeText)
        self.assertHTMLEqual(
            html,
            '<img alt="username" class="avatar djblets-o-avatar" height="48" '
            ' src="%(gravatar_url_base)s?s=48"'
            ' srcset="%(gravatar_url_base)s?s=48 1x,'
            ' %(gravatar_url_base)s?s=96 2x,'
            ' %(gravatar_url_base)s?s=144 3x" width="48" />'
            % {
                'gravatar_url_base': 'https://secure.gravatar.com/avatar/'
                                     '5f0efb20de5ecfedbe0bf5e7c12353fe',
            })

    def test_render_with_request_none(self):
        """Testing GravatarService.render with request=None"""
        self.request = None
        self.test_render()

    def test_user_without_email(self):
        """Testing GravatarService.render with a user without an email
        address
        """
        user = User(username='username', first_name='User', last_name='Name')
        urls = self.service.get_avatar_urls(self.request, user, 48)

        base_url = ('https://secure.gravatar.com/avatar/'
                    '00000000000000000000000000000000?s=%s')

        self.assertEqual(urls, {
            '1x': base_url % 48,
            '2x': base_url % 96,
            '3x': base_url % 144,
        })


class URLAvatarServiceTests(SpyAgency, AvatarServiceTestCase):
    """Tests for djblets.avatars.services.url."""

    avatar_service_cls = URLAvatarService

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

    def test_render(self):
        """Testing URLAvatarService.render"""
        urls = {
            '1x': 'http://example.com/foo.jpg',
            '2x': 'http://example.com/bar@2x.jpg',
        }
        self.settings_manager.configuration_for(
            URLAvatarService.avatar_service_id).update(urls)

        html = self.service.render(request=self.request,
                                   user=self.user,
                                   size=48)

        self.assertIsInstance(html, SafeText)
        self.assertHTMLEqual(
            html,
            '<img alt="username" class="avatar djblets-o-avatar" height="48"'
            ' src="http://example.com/foo.jpg"'
            ' srcset="http://example.com/foo.jpg 1x,'
            ' http://example.com/bar@2x.jpg 2x" width="48" />')

    def test_render_with_request_none(self):
        """Testing URLAvatarService.render with request=None"""
        self.request = None
        self.test_render()


class AvatarServiceRegistryTests(SpyAgency, TestCase):
    """Tests for djblets.avatars.registry."""

    def setUp(self):
        super(AvatarServiceRegistryTests, self).setUp()

        self.siteconfig = SiteConfiguration.objects.create(
            site=Site.objects.get_current())
        cache.clear()

    def tearDown(self):
        super(AvatarServiceRegistryTests, self).tearDown()
        cache.clear()

    def test_enable_service(self):
        """Testing AvatarServiceRegistry.enable_service"""
        registry = AvatarServiceRegistry()
        registry.register(DummyAvatarService)
        self.assertFalse(registry.is_enabled(DummyAvatarService))
        self.assertEqual(set(registry.enabled_services), set())

        registry.enable_service(DummyAvatarService)
        self.assertTrue(registry.is_enabled(DummyAvatarService))
        self.assertEqual(registry.enabled_services, {DummyAvatarService})

        siteconfig = SiteConfiguration.objects.get_current()
        self.assertEqual(
            siteconfig.get(AvatarServiceRegistry.ENABLED_SERVICES_KEY),
            [DummyAvatarService.avatar_service_id])

    def test_enable_service_with_save_false(self):
        """Testing AvatarServiceRegistry.enable_service with save=False"""
        registry = AvatarServiceRegistry()
        registry.register(DummyAvatarService)
        self.assertFalse(registry.is_enabled(DummyAvatarService))
        self.assertEqual(set(registry.enabled_services), set())

        registry.enable_service(DummyAvatarService, save=False)
        self.assertTrue(registry.is_enabled(DummyAvatarService))
        self.assertEqual(registry.enabled_services, {DummyAvatarService})

        # Make sure we've saved this in our cached siteconfig...
        siteconfig = SiteConfiguration.objects.get_current()
        self.assertEqual(
            siteconfig.get(AvatarServiceRegistry.ENABLED_SERVICES_KEY),
            [DummyAvatarService.avatar_service_id])

        # ... but not in the database.
        siteconfig = SiteConfiguration.objects.get(pk=siteconfig.pk)
        self.assertEqual(
            siteconfig.get(AvatarServiceRegistry.ENABLED_SERVICES_KEY),
            [])

    def test_enable_service_by_id(self):
        """Testing AvatarServiceRegistry.enable_service_by_id"""
        registry = AvatarServiceRegistry()
        registry.register(DummyAvatarService)
        self.assertFalse(registry.is_enabled(DummyAvatarService))
        self.assertEqual(set(registry.enabled_services), set())

        registry.enable_service_by_id(DummyAvatarService.avatar_service_id)
        self.assertTrue(registry.is_enabled(DummyAvatarService))
        self.assertEqual(registry.enabled_services, {DummyAvatarService})

        siteconfig = SiteConfiguration.objects.get_current()
        self.assertEqual(
            siteconfig.get(AvatarServiceRegistry.ENABLED_SERVICES_KEY),
            [DummyAvatarService.avatar_service_id])

    def test_enable_service_by_id_with_save_false(self):
        """Testing AvatarServiceRegistry.enable_service_by_id with save=False
        """
        registry = AvatarServiceRegistry()
        registry.register(DummyAvatarService)
        self.assertFalse(registry.is_enabled(DummyAvatarService))
        self.assertEqual(set(registry.enabled_services), set())

        registry.enable_service_by_id(DummyAvatarService.avatar_service_id,
                                      save=False)
        self.assertTrue(registry.is_enabled(DummyAvatarService))
        self.assertEqual(registry.enabled_services, {DummyAvatarService})

        # Make sure we've saved this in our cached siteconfig...
        siteconfig = SiteConfiguration.objects.get_current()
        self.assertEqual(
            siteconfig.get(AvatarServiceRegistry.ENABLED_SERVICES_KEY),
            [DummyAvatarService.avatar_service_id])

        # ... but not in the database.
        siteconfig = SiteConfiguration.objects.get(pk=siteconfig.pk)
        self.assertEqual(
            siteconfig.get(AvatarServiceRegistry.ENABLED_SERVICES_KEY),
            [])

    def test_disable_service(self):
        """Testing AvatarServiceRegistry.disable_service"""
        registry = AvatarServiceRegistry()
        self.assertFalse(registry.is_enabled(GravatarService))
        registry.enable_service(GravatarService)

        self.assertTrue(registry.is_enabled(GravatarService))
        self.assertEqual(set(registry.enabled_services), {GravatarService})

        registry.disable_service(GravatarService)
        self.assertFalse(registry.is_enabled(GravatarService))
        self.assertEqual(set(registry.enabled_services), set())

        siteconfig = SiteConfiguration.objects.get_current()
        self.assertEqual(
            siteconfig.get(AvatarServiceRegistry.ENABLED_SERVICES_KEY),
            [])

    def test_disable_service_with_save_false(self):
        """Testing AvatarServiceRegistry.disable_service with save=False"""
        registry = AvatarServiceRegistry()
        self.assertFalse(registry.is_enabled(GravatarService))
        registry.enable_service(GravatarService)

        self.assertTrue(registry.is_enabled(GravatarService))
        self.assertEqual(set(registry.enabled_services), {GravatarService})

        registry.disable_service(GravatarService, save=False)
        self.assertFalse(registry.is_enabled(GravatarService))
        self.assertEqual(set(registry.enabled_services), set())

        # Make sure we've saved this in our cached siteconfig...
        siteconfig = SiteConfiguration.objects.get_current()
        self.assertEqual(
            siteconfig.get(AvatarServiceRegistry.ENABLED_SERVICES_KEY),
            [])

        # ... but not in the database.
        siteconfig = SiteConfiguration.objects.get(pk=siteconfig.pk)
        self.assertEqual(
            siteconfig.get(AvatarServiceRegistry.ENABLED_SERVICES_KEY),
            [GravatarService.avatar_service_id])

    def test_disable_service_by_id(self):
        """Testing AvatarServiceRegistry.disable_service_by_id"""
        registry = AvatarServiceRegistry()
        self.assertFalse(registry.is_enabled(GravatarService))
        registry.enable_service(GravatarService)

        self.assertTrue(registry.is_enabled(GravatarService))
        self.assertEqual(set(registry.enabled_services), {GravatarService})

        registry.disable_service_by_id(GravatarService.avatar_service_id)
        self.assertFalse(registry.is_enabled(GravatarService))
        self.assertEqual(set(registry.enabled_services), set())

        siteconfig = SiteConfiguration.objects.get_current()
        self.assertEqual(
            siteconfig.get(AvatarServiceRegistry.ENABLED_SERVICES_KEY),
            [])

    def test_disable_service_by_id_with_save_false(self):
        """Testing AvatarServiceRegistry.disable_service_by_id with save=False
        """
        registry = AvatarServiceRegistry()
        self.assertFalse(registry.is_enabled(GravatarService))
        registry.enable_service(GravatarService)

        self.assertTrue(registry.is_enabled(GravatarService))
        self.assertEqual(set(registry.enabled_services), {GravatarService})

        registry.disable_service_by_id(GravatarService.avatar_service_id,
                                       save=False)
        self.assertFalse(registry.is_enabled(GravatarService))
        self.assertEqual(set(registry.enabled_services), set())

        # Make sure we've saved this in our cached siteconfig...
        siteconfig = SiteConfiguration.objects.get_current()
        self.assertEqual(
            siteconfig.get(AvatarServiceRegistry.ENABLED_SERVICES_KEY),
            [])

        # ... but not in the database.
        siteconfig = SiteConfiguration.objects.get(pk=siteconfig.pk)
        self.assertEqual(
            siteconfig.get(AvatarServiceRegistry.ENABLED_SERVICES_KEY),
            [GravatarService.avatar_service_id])

    def test_set_enabled_services(self):
        """Testing AvatarServiceRegistry.set_enabled_services"""
        registry = AvatarServiceRegistry()

        registry.register(DummyAvatarService)

        registry.set_enabled_services([DummyAvatarService, GravatarService])

        self.assertEqual(registry.enabled_services,
                         {DummyAvatarService, GravatarService})

        siteconfig = SiteConfiguration.objects.get_current()
        self.assertEqual(
            set(siteconfig.get(AvatarServiceRegistry.ENABLED_SERVICES_KEY)),
            {
                DummyAvatarService.avatar_service_id,
                GravatarService.avatar_service_id,
            })

    def test_set_enabled_services_with_save_false(self):
        """Testing AvatarServiceRegistry.set_enabled_services with save=False
        """
        registry = AvatarServiceRegistry()
        registry.register(DummyAvatarService)
        registry.set_enabled_services([DummyAvatarService, GravatarService],
                                      save=False)

        self.assertEqual(registry.enabled_services,
                         {DummyAvatarService, GravatarService})

        # Make sure we've saved this in our cached siteconfig...
        siteconfig = SiteConfiguration.objects.get_current()
        self.assertEqual(
            set(siteconfig.get(AvatarServiceRegistry.ENABLED_SERVICES_KEY)),
            {DummyAvatarService.avatar_service_id,
             GravatarService.avatar_service_id})

        # ... but not in the database.
        siteconfig = SiteConfiguration.objects.get(pk=siteconfig.pk)
        self.assertEqual(
            siteconfig.get(AvatarServiceRegistry.ENABLED_SERVICES_KEY),
            [])

    def test_get_enabled_services_populated(self):
        """Testing AvatarServiceRegistry.enabled_services property calls
        populate()
        """
        class TestRegistry(AvatarServiceRegistry):
            settings_manager_class = DummySettingsManager

            def populate(self):
                if self.populated:
                    return

                super(TestRegistry, self).populate()
                self.set_enabled_services([DummyAvatarService])

            def get_defaults(self):
                yield DummyAvatarService

        self.siteconfig.set(AvatarServiceRegistry.ENABLED_SERVICES_KEY,
                            [DummyAvatarService.avatar_service_id])
        self.siteconfig.save()

        registry = TestRegistry()
        self.assertFalse(registry.populated)

        enabled_services = set(registry.enabled_services)
        self.assertTrue(registry.populated)
        self.assertSetEqual(enabled_services, {DummyAvatarService})

    def test_set_enabled_services_invalid_service(self):
        """Testing AvatarServiceRegistry.set_enabled_services with an
        unregistered service
        """
        registry = AvatarServiceRegistry()

        with self.assertRaises(ItemLookupError):
            registry.set_enabled_services([DummyAvatarService,
                                           GravatarService])

        self.assertEqual(registry.enabled_services, set())

        siteconfig = SiteConfiguration.objects.get_current()
        self.assertEqual(
            siteconfig.get(AvatarServiceRegistry.ENABLED_SERVICES_KEY),
            [])

    def test_default_service(self):
        """Testing AvatarServiceRegistry.default_service"""
        registry = AvatarServiceRegistry()
        registry.register(DummyAvatarService)

        registry.set_enabled_services([DummyAvatarService, GravatarService])
        self.assertIsNone(registry.default_service)

        # Set the default backend to the dummy backend.
        registry.set_default_service(DummyAvatarService)
        self.assertIsInstance(registry.default_service, DummyAvatarService)

        siteconfig = SiteConfiguration.objects.get_current()
        self.assertEqual(
            siteconfig.get(AvatarServiceRegistry.DEFAULT_SERVICE_KEY),
            DummyAvatarService.avatar_service_id)

        # Set the default backend to the Gravatar backend.
        registry.set_default_service(GravatarService)
        self.assertIsInstance(registry.default_service, GravatarService)

        siteconfig = SiteConfiguration.objects.get_current()
        self.assertEqual(
            siteconfig.get(AvatarServiceRegistry.DEFAULT_SERVICE_KEY),
            GravatarService.avatar_service_id)

        # Remove the default backend.
        registry.set_default_service(None)
        self.assertIsNone(registry.default_service)

        siteconfig = SiteConfiguration.objects.get_current()
        self.assertIsNone(
            siteconfig.get(AvatarServiceRegistry.DEFAULT_SERVICE_KEY))

    def test_default_service_after_service_reregistered(self):
        """Testing AvatarServiceRegistry.default_service after service
        registered after previously unregistered
        """
        self.siteconfig.set(AvatarServiceRegistry.ENABLED_SERVICES_KEY,
                            [DummyAvatarService.avatar_service_id])
        self.siteconfig.set(AvatarServiceRegistry.DEFAULT_SERVICE_KEY,
                            DummyAvatarService.avatar_service_id)
        self.siteconfig.save()

        registry = AvatarServiceRegistry()
        registry.populate()

        self.assertIsNone(registry.default_service)

        # Make sure it's still saved in siteconfig. We'd only unset it if
        # wasn't in the list of stoerd enabled service IDs, since we might be
        # running without extensions loaded.
        siteconfig = SiteConfiguration.objects.get_current()
        self.assertEqual(
            siteconfig.get(AvatarServiceRegistry.DEFAULT_SERVICE_KEY),
            DummyAvatarService.avatar_service_id)

        registry.register(DummyAvatarService)

        self.assertIsInstance(registry.default_service, DummyAvatarService)

        siteconfig = SiteConfiguration.objects.get_current()
        self.assertEqual(
            siteconfig.get(AvatarServiceRegistry.DEFAULT_SERVICE_KEY),
            DummyAvatarService.avatar_service_id)

    def test_set_default_service(self):
        """Testing AvatarServiceRegistry.set_default_service"""
        self.siteconfig.set(AvatarServiceRegistry.ENABLED_SERVICES_KEY,
                            [GravatarService.avatar_service_id])
        self.siteconfig.save()

        registry = AvatarServiceRegistry()
        self.assertIsNone(registry.default_service)

        registry.set_default_service(GravatarService)

        self.assertIsInstance(registry.default_service, GravatarService)

        siteconfig = SiteConfiguration.objects.get_current()
        self.assertEqual(
            siteconfig.get(AvatarServiceRegistry.DEFAULT_SERVICE_KEY),
            GravatarService.avatar_service_id)

    def test_set_default_service_with_save_false(self):
        """Testing AvatarServiceRegistry.set_default_service with save=False"""
        self.siteconfig.set(AvatarServiceRegistry.ENABLED_SERVICES_KEY,
                            [GravatarService.avatar_service_id])
        self.siteconfig.set(AvatarServiceRegistry.DEFAULT_SERVICE_KEY,
                            GravatarService.avatar_service_id)
        self.siteconfig.save()

        registry = AvatarServiceRegistry()
        registry.set_default_service(None, save=False)

        self.assertIsNone(registry.default_service)

        # Make sure we've saved this in our cached siteconfig...
        siteconfig = SiteConfiguration.objects.get_current()
        self.assertIsNone(
            siteconfig.get(AvatarServiceRegistry.DEFAULT_SERVICE_KEY))

        # ... but not in the database.
        siteconfig = SiteConfiguration.objects.get(pk=siteconfig.pk)
        self.assertEqual(
            siteconfig.get(AvatarServiceRegistry.DEFAULT_SERVICE_KEY),
            GravatarService.avatar_service_id)

    def test_set_default_service_invalid(self):
        """Testing AvatarServiceRegistry.set_default_service with an
        unregistered service
        """
        self.siteconfig.set(AvatarServiceRegistry.ENABLED_SERVICES_KEY,
                            [GravatarService.avatar_service_id])
        self.siteconfig.set(AvatarServiceRegistry.DEFAULT_SERVICE_KEY,
                            GravatarService.avatar_service_id)
        self.siteconfig.save()

        registry = AvatarServiceRegistry()
        self.assertIsInstance(registry.default_service, GravatarService)

        with self.assertRaises(ItemLookupError):
            registry.set_default_service(DummyAvatarService)

        self.assertIsInstance(registry.default_service, GravatarService)

        siteconfig = SiteConfiguration.objects.get_current()
        self.assertEqual(
            siteconfig.get(AvatarServiceRegistry.DEFAULT_SERVICE_KEY),
            GravatarService.avatar_service_id)

    def test_set_default_service_disabled(self):
        """Testing AvatarServiceRegistry.set_default_service with a disabled
        service
        """
        registry = AvatarServiceRegistry()
        gravatar_service = registry.get('avatar_service_id',
                                        GravatarService.avatar_service_id)

        self.assertIsNone(registry.default_service)

        with self.assertRaises(DisabledServiceError):
            registry.set_default_service(gravatar_service)

        self.assertIsNone(registry.default_service)

        siteconfig = SiteConfiguration.objects.get_current()
        self.assertIsNone(
            siteconfig.get(AvatarServiceRegistry.DEFAULT_SERVICE_KEY))

    def test_populate(self):
        """Testing AvatarServiceRegistry.populate with site configuration
        settings
        """
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

    def test_unregister(self):
        """Testing AvatarServiceRegistry.unregister"""
        self.siteconfig.set(AvatarServiceRegistry.DEFAULT_SERVICE_KEY,
                            GravatarService.avatar_service_id)
        self.siteconfig.set(AvatarServiceRegistry.ENABLED_SERVICES_KEY,
                            [GravatarService.avatar_service_id])
        self.siteconfig.save()

        registry = AvatarServiceRegistry()
        gravatar_service = registry.get('avatar_service_id',
                                        GravatarService.avatar_service_id)

        self.assertEqual(registry.enabled_services, {gravatar_service})

        registry.unregister(gravatar_service)
        self.assertEqual(registry.enabled_services, set())
        self.assertIsNone(registry.default_service)

        siteconfig = SiteConfiguration.objects.get_current()
        self.assertEqual(
            siteconfig.get(AvatarServiceRegistry.ENABLED_SERVICES_KEY),
            [GravatarService.avatar_service_id])
        self.assertEqual(
            siteconfig.get(AvatarServiceRegistry.DEFAULT_SERVICE_KEY),
            GravatarService.avatar_service_id)

    def test_unregister_register_keeps_enabled(self):
        """Testing AvatarServiceRegistry.unregister followed by register keeps
        enabled state
        """
        registry = AvatarServiceRegistry()
        gravatar_service = registry.get('avatar_service_id',
                                        GravatarService.avatar_service_id)

        registry.enable_service(GravatarService)

        self.assertEqual(registry.enabled_services, {gravatar_service})
        registry.unregister(gravatar_service)
        self.assertEqual(registry.enabled_services, set())

        registry.register(gravatar_service)
        self.assertEqual(registry.enabled_services, {gravatar_service})

        siteconfig = SiteConfiguration.objects.get_current()
        self.assertEqual(
            siteconfig.get(AvatarServiceRegistry.ENABLED_SERVICES_KEY),
            [GravatarService.avatar_service_id])

    def test_disable_default(self):
        """Testing AvatarServiceRegistry.disable_service unsets the default
        service
        """
        registry = AvatarServiceRegistry()
        registry.enable_service(GravatarService)
        registry.set_default_service(GravatarService)

        registry.disable_service(GravatarService)
        self.assertIsNone(registry.default_service)

        siteconfig = SiteConfiguration.objects.get_current()
        self.assertEqual(
            siteconfig.get(AvatarServiceRegistry.ENABLED_SERVICES_KEY),
            [])
        self.assertIsNone(
            siteconfig.get(AvatarServiceRegistry.DEFAULT_SERVICE_KEY))

    def test_disable_default_from_setter(self):
        """Testing AvatarServiceRegistry.set_enabled_services unsets the
        default services when removed
        """
        registry = AvatarServiceRegistry()
        registry.enable_service(GravatarService)
        registry.set_default_service(GravatarService)

        registry.set_enabled_services([])
        self.assertIsNone(registry.default_service)

        siteconfig = SiteConfiguration.objects.get_current()
        self.assertEqual(
            siteconfig.get(AvatarServiceRegistry.ENABLED_SERVICES_KEY),
            [])
        self.assertIsNone(
            siteconfig.get(AvatarServiceRegistry.DEFAULT_SERVICE_KEY))

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

    def test_for_user_with_consent_checks_and_no_consent_needed(self):
        """Testing AvatarServiceRegistry.for_user with consent checks enabled
        and no consent needed by service
        """
        class DummyAvatarServiceRegistry(AvatarServiceRegistry):
            settings_manager_class = DummySettingsManager(
                DummyAvatarService.avatar_service_id, {})
            default_avatar_service_classes = [
                GravatarService,
                DummyAvatarService,
            ]

        registry = DummyAvatarServiceRegistry()
        registry.enable_service(GravatarService, save=False)
        registry.enable_service(DummyAvatarService, save=False)
        registry.set_default_service(DummyAvatarService, save=False)

        user = User.objects.create(username='test-user')

        settings = {
            AvatarServiceRegistry.ENABLE_CONSENT_CHECKS: True,
        }

        with self.siteconfig_settings(settings):
            self.assertIsInstance(registry.for_user(user), DummyAvatarService)

    def test_for_user_with_consent_checks_and_consent_unset(self):
        """Testing AvatarServiceRegistry.for_user with consent checks enabled
        and consent unset
        """
        class DummyAvatarServiceRegistry(AvatarServiceRegistry):
            settings_manager_class = DummySettingsManager(
                GravatarService.avatar_service_id, {})
            default_avatar_service_classes = [
                GravatarService,
                DummyAvatarService,
            ]

        registry = DummyAvatarServiceRegistry()
        registry.enable_service(GravatarService, save=False)
        registry.enable_service(DummyAvatarService, save=False)
        registry.set_default_service(DummyAvatarService, save=False)

        user = User.objects.create(username='test-user')

        settings = {
            AvatarServiceRegistry.ENABLE_CONSENT_CHECKS: True,
        }

        with self.siteconfig_settings(settings):
            self.assertIsInstance(registry.for_user(user), DummyAvatarService)

    def test_for_user_with_consent_checks_and_consent_denied(self):
        """Testing AvatarServiceRegistry.for_user with consent checks enabled
        and consent denied
        """
        class DummyAvatarServiceRegistry(AvatarServiceRegistry):
            settings_manager_class = DummySettingsManager(
                GravatarService.avatar_service_id, {})
            default_avatar_service_classes = [
                GravatarService,
                DummyAvatarService,
            ]

        registry = DummyAvatarServiceRegistry()
        registry.enable_service(GravatarService, save=False)
        registry.enable_service(DummyAvatarService, save=False)
        registry.set_default_service(DummyAvatarService, save=False)

        user = User.objects.create(username='test-user')

        settings = {
            AvatarServiceRegistry.ENABLE_CONSENT_CHECKS: True,
        }

        get_consent_tracker().record_consent_data(
            user,
            ConsentData(requirement_id=GravatarService.consent_requirement_id,
                        granted=False))

        with self.siteconfig_settings(settings):
            self.assertIsInstance(registry.for_user(user), DummyAvatarService)

    def test_for_user_with_consent_checks_and_consent_granted(self):
        """Testing AvatarServiceRegistry.for_user with consent checks enabled
        and consent granted
        """
        class DummyAvatarServiceRegistry(AvatarServiceRegistry):
            settings_manager_class = DummySettingsManager(
                GravatarService.avatar_service_id, {})
            default_avatar_service_classes = [
                GravatarService,
                DummyAvatarService,
            ]

        registry = DummyAvatarServiceRegistry()
        registry.enable_service(GravatarService, save=False)
        registry.enable_service(DummyAvatarService, save=False)
        registry.set_default_service(DummyAvatarService, save=False)

        user = User.objects.create(username='test-user')

        settings = {
            AvatarServiceRegistry.ENABLE_CONSENT_CHECKS: True,
        }

        get_consent_tracker().record_consent_data(
            user,
            ConsentData(requirement_id=GravatarService.consent_requirement_id,
                        granted=True))

        with self.siteconfig_settings(settings):
            self.assertIsInstance(registry.for_user(user), GravatarService)

    def test_for_user_with_consent_checks_and_no_allowed_services(self):
        """Testing AvatarServiceRegistry.for_user with consent checks enabled
        and no resulting consented services
        """
        class DummyAvatarServiceRegistry(AvatarServiceRegistry):
            settings_manager_class = DummySettingsManager(
                GravatarService.avatar_service_id, {})
            default_avatar_service_classes = [
                GravatarService,
            ]

        registry = DummyAvatarServiceRegistry()
        registry.enable_service(GravatarService, save=False)
        registry.set_default_service(GravatarService, save=False)

        user = User.objects.create(username='test-user')

        settings = {
            AvatarServiceRegistry.ENABLE_CONSENT_CHECKS: True,
        }

        with self.siteconfig_settings(settings):
            self.assertIsInstance(registry.for_user(user),
                                  registry.fallback_service_class)

    def test_for_user_default_service_none_and_no_configured_services(self):
        """Testing AvatarServiceRegistry.for_user with None as default
        avatar service and no user-configured services
        """
        class DummyAvatarServiceRegistry(AvatarServiceRegistry):
            settings_manager_class = DummySettingsManager(
                GravatarService.avatar_service_id, {})
            default_avatar_service_classes = []

        registry = DummyAvatarServiceRegistry()
        registry.set_default_service(None, save=False)

        user = User.objects.create(username='test-user')

        self.assertIsInstance(registry.for_user(user),
                              registry.fallback_service_class)


@requires_user_profile
class AvatarSettingsFormTests(SpyAgency, TestCase):
    """Tests for djblets.avatars.forms.AvatarSettingsForm."""

    @classmethod
    def setUpClass(cls):
        super(AvatarSettingsFormTests, cls).setUpClass()
        cls.request_factory = RequestFactory()

    def setUp(self):
        super(AvatarSettingsFormTests, self).setUp()
        site = Site.objects.get_current()
        self.siteconfig = SiteConfiguration.objects.create(site=site)

    def tearDown(self):
        super(AvatarSettingsFormTests, self).tearDown()
        self.siteconfig.delete()

    def test_instantiate_form_no_default_service(self):
        """Testing AvatarSettingsForm instantiation when there is no
        default avatar service
        """
        class TestAvatarServiceRegistry(AvatarServiceRegistry):
            default_avatar_service_classes = []
            settings_manager_class = DummySettingsManager(None, {})

        class TestSettingsForm(AvatarSettingsForm):
            avatar_service_registry = TestAvatarServiceRegistry()

        class TestPage(ConfigPage):
            form_classes = [TestSettingsForm]

        self.spy_on(User.get_profile, call_fake=lambda *args: None)

        self.assertIsNone(
            TestSettingsForm.avatar_service_registry.default_service)

        request = self.request_factory.get('/')
        user = User(username='test', email='test@example.com')
        page = TestPage(None, request, user)
        TestSettingsForm(page, request, user)

    def test_ensure_valid_subform_config(self):
        """Testing AvatarSettingsForm.is_valid ensures avatar service
        configuration form is also valid
        """
        class InvalidAvatarServiceForm(AvatarServiceConfigForm):
            def clean(self):
                raise ValidationError('Invalid!')

        class InvalidAvatarService(AvatarService):
            avatar_service_id = 'invalid-service'
            config_form_class = InvalidAvatarServiceForm

        class TestAvatarServiceRegistry(AvatarServiceRegistry):
            default_avatar_service_classes = [InvalidAvatarService]
            settings_manager_class = DummySettingsManager(None, {})

        class TestSettingsForm(AvatarSettingsForm):
            avatar_service_registry = TestAvatarServiceRegistry()

        class TestPage(ConfigPage):
            form_classes = [TestSettingsForm]

        self.spy_on(User.get_profile, call_fake=lambda self: None)

        request = self.request_factory.get('/')
        user = User(username='test', email='test@example.com')
        page = TestPage(None, request, user)
        TestSettingsForm.avatar_service_registry.enable_service(
            InvalidAvatarService, save=False)
        form = TestSettingsForm(
            page,
            request,
            user,
            data={
                'avatar_service_id': InvalidAvatarService.avatar_service_id,
            })

        self.assertFalse(form.is_valid())


@requires_user_profile
class FileUploadTests(SpyAgency, TestCase):
    """Unit tests for FileUploadService and FileUploadServiceForm."""

    def setUp(self):
        super(FileUploadTests, self).setUp()

        self.user = User(username='doc')

        # We cache a UUID so that we can compare resultant filenames.
        self.uuid = uuid.uuid4()
        self.spy_on(uuid.uuid4, call_fake=lambda: self.uuid)

        self.configuration = {}
        self.settings_mgr = DummySettingsManager(
            FileUploadService.avatar_service_id, self.configuration)

        self.storage_cls = get_storage_class()

    def test_filename_generation(self):
        """Testing FileUploadServiceForm.save puts files in the correct
        location
        """
        self.spy_on(User.get_profile, call_fake=lambda *args: None)

        avatar = SimpleUploadedFile('filename.png', content=b' ',
                                    content_type='image/png')

        service = FileUploadService(self.settings_mgr)
        form = service.get_configuration_form(self.user, None, None, self.user,
                                              data={})

        form.files = {
            form.add_prefix('avatar_upload'): avatar,
        }

        self.assertTrue(form.is_valid())

        self.spy_on(self.storage_cls.save,
                    call_fake=lambda self, name, *args, **kwargs: name)
        form.save()

        self.assertTrue(self.storage_cls.save.spy.called)
        self.assertEqual(self.storage_cls.save.spy.last_call.args[0],
                         'uploaded/avatars/d/do/doc__%s.png' % self.uuid)

    def test_filename_generation_no_ext(self):
        """Testing FileUploadServiceForm.save puts files in the correct
        location when there is no file extension
        """
        self.spy_on(User.get_profile, call_fake=lambda *args: None)

        avatar = SimpleUploadedFile('filename', content=b' ',
                                    content_type='image/png')

        service = FileUploadService(self.settings_mgr)
        form = service.get_configuration_form(self.user, None, None, self.user,
                                              data={})

        form.files = {
            form.add_prefix('avatar_upload'): avatar,
        }

        self.assertTrue(form.is_valid())

        self.spy_on(self.storage_cls.save,
                    call_fake=lambda self, name, *args, **kwargs: name)
        form.save()

        self.assertTrue(self.storage_cls.save.spy.called)
        self.assertEqual(self.storage_cls.save.spy.last_call.args[0],
                         'uploaded/avatars/d/do/doc__%s' % self.uuid)

    def test_filename_generation_improper_ext(self):
        """Testing FileUploadServiceForm.save puts files in the correct
        location when the extension is improper
        """
        self.spy_on(User.get_profile, call_fake=lambda *args: None)

        avatar = SimpleUploadedFile('filename. bad extension', content=b' ',
                                    content_type='image/png')

        service = FileUploadService(self.settings_mgr)
        form = service.get_configuration_form(self.user, None, None, self.user,
                                              data={})

        form.files = {
            form.add_prefix('avatar_upload'): avatar,
        }

        self.assertTrue(form.is_valid())

        self.spy_on(self.storage_cls.save,
                    call_fake=lambda self, name, *args, **kwargs: name)
        form.save()

        self.assertTrue(self.storage_cls.save.spy.called)
        self.assertEqual(self.storage_cls.save.spy.last_call.args[0],
                         'uploaded/avatars/d/do/doc__%s._bad_extension'
                         % self.uuid)
