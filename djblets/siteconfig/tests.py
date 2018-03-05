"""Unit tests for djblets.siteconfig."""

from __future__ import unicode_literals

import hmac

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.utils import six

from djblets.siteconfig.django_settings import (apply_django_settings,
                                                cache_settings_map,
                                                mail_settings_map)
from djblets.siteconfig.models import SiteConfiguration
from djblets.siteconfig.signals import siteconfig_reloaded
from djblets.testing.testcases import TestCase


class SiteConfigTestCase(TestCase):
    """Base class for SiteConfiguration-related unit tests."""

    def setUp(self):
        super(SiteConfigTestCase, self).setUp()

        self.siteconfig = SiteConfiguration(site=Site.objects.get_current())
        self.siteconfig.save()

    def tearDown(self):
        super(SiteConfigTestCase, self).tearDown()

        self.siteconfig.delete()
        SiteConfiguration.objects.clear_cache()


class DjangoSettingsTests(SiteConfigTestCase):
    """Unit tests for django_settings.py."""

    def test_mail_auth_deserialize(self):
        """Testing Django mail siteconfig settings with deserializing mail
        server credentials
        """
        # This is bug 1476. We deserialized the e-mail settings to Unicode
        # strings automatically, but this broke mail sending on some setups.
        # The HMAC library is incompatible with Unicode strings in more recent
        # Python 2.6 versions. Now we deserialize as a string. This test
        # ensures that these settings never break again.

        username = 'myuser'
        password = 'mypass'

        self.assertEqual(type(username), six.text_type)
        self.assertEqual(type(password), six.text_type)

        self.siteconfig.set('mail_host_user', username)
        self.siteconfig.set('mail_host_password', password)
        apply_django_settings(self.siteconfig, mail_settings_map)

        self.assertEqual(settings.EMAIL_HOST_USER, username)
        self.assertEqual(settings.EMAIL_HOST_PASSWORD, password)
        self.assertEqual(type(settings.EMAIL_HOST_USER), str)
        self.assertEqual(type(settings.EMAIL_HOST_PASSWORD), str)

        # Simulate the failure point in HMAC
        settings.EMAIL_HOST_USER.translate(hmac.trans_5C)
        settings.EMAIL_HOST_PASSWORD.translate(hmac.trans_5C)

    def test_cache_backend_with_legacy_uri(self):
        """Testing Django cache backend siteconfig settings with migrating
        stored legacy cache backend URI to settings.CACHES
        """
        settings.CACHES = {
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                'LOCATION': 'foo',
            },
            'staticfiles': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                'LOCATION': 'staticfiles-cache',
            }
        }

        self.siteconfig.set('cache_backend', 'memcached://localhost:12345/')
        apply_django_settings(self.siteconfig, cache_settings_map)

        self.assertTrue('staticfiles' in settings.CACHES)
        self.assertTrue('default' in settings.CACHES)
        self.assertTrue('forwarded_backend' in settings.CACHES)

        self.assertEqual(
            settings.CACHES['default']['BACKEND'],
            'djblets.cache.forwarding_backend.ForwardingCacheBackend')
        self.assertEqual(settings.CACHES['default']['LOCATION'],
                         'forwarded_backend')

        self.assertEqual(settings.CACHES['forwarded_backend']['BACKEND'],
                         'django.core.cache.backends.memcached.MemcachedCache')
        self.assertEqual(settings.CACHES['forwarded_backend']['LOCATION'],
                         'localhost:12345')

    def test_cache_backend_with_caches(self):
        """Testing Django cache backend siteconfig settings with stored CACHES
        dictionary overriding entry in settings.CACHES
        """
        settings.CACHES['staticfiles'] = {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'staticfiles-cache',
        }

        self.siteconfig.set('cache_backend', {
            'default': {
                'BACKEND':
                    'django.core.cache.backends.memcached.MemcachedCache',
                'LOCATION': 'localhost:12345',
            },
        })

        apply_django_settings(self.siteconfig, cache_settings_map)

        self.assertTrue('staticfiles' in settings.CACHES)
        self.assertTrue('default' in settings.CACHES)
        self.assertTrue('forwarded_backend' in settings.CACHES)

        self.assertEqual(
            settings.CACHES['default']['BACKEND'],
            'djblets.cache.forwarding_backend.ForwardingCacheBackend')
        self.assertEqual(settings.CACHES['default']['LOCATION'],
                         'forwarded_backend')

        self.assertEqual(settings.CACHES['forwarded_backend']['BACKEND'],
                         'django.core.cache.backends.memcached.MemcachedCache')
        self.assertEqual(settings.CACHES['forwarded_backend']['LOCATION'],
                         'localhost:12345')

    def test_cache_backend_without_caches_in_settings_py(self):
        """Testing Django cache backend siteconfig settings with stored
        CACHES dictionary and no entry in settings.CACHES
        """
        settings.CACHES['staticfiles'] = {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'staticfiles-cache',
        }

        self.siteconfig.set('cache_backend', {
            'default': {
                'BACKEND':
                    'django.core.cache.backends.memcached.CacheClass',
                'LOCATION': 'localhost:12345',
            },
        })

        apply_django_settings(self.siteconfig, cache_settings_map)

        self.assertTrue('staticfiles' in settings.CACHES)
        self.assertTrue('default' in settings.CACHES)
        self.assertTrue('forwarded_backend' in settings.CACHES)

        self.assertEqual(
            settings.CACHES['default']['BACKEND'],
            'djblets.cache.forwarding_backend.ForwardingCacheBackend')
        self.assertEqual(settings.CACHES['default']['LOCATION'],
                         'forwarded_backend')

        self.assertEqual(settings.CACHES['forwarded_backend']['BACKEND'],
                         'django.core.cache.backends.memcached.MemcachedCache')
        self.assertEqual(settings.CACHES['forwarded_backend']['LOCATION'],
                         'localhost:12345')


class SiteConfigurationTests(SiteConfigTestCase):
    """Unit tests for SiteConfiguration."""

    def test_get(self):
        """Testing SiteConfiguration.get"""
        self.siteconfig.set('valid_key_2', 'valid_parameter_2')

        self.assertEqual(self.siteconfig.get('valid_key_2'),
                         'valid_parameter_2')

    def test_get_with_missing_key_and_explicit_default(self):
        """Testing SiteConfiguration.get and passing a missing key with
        explicit default
        """
        self.assertEqual(self.siteconfig.get('invalid_key', default='default'),
                         'default')

    def test_get_with_missing_key_and_registered_default(self):
        """Testing SiteConfiguration.get and passing a missing key with a
        registered default
        """
        SiteConfiguration.add_global_default('valid_key_1', 'global_default_1')
        self.siteconfig.add_default('valid_key_1', 'valid_parameter_1')

        try:
            self.assertEqual(self.siteconfig.get('valid_key_1'),
                             'valid_parameter_1')
        finally:
            self.siteconfig.remove_default('valid_key_1')

    def test_get_with_missing_key_and_registered_global_default(self):
        """Testing SiteConfiguration.get and passing a missing key with a
        registered global default
        """
        SiteConfiguration.add_global_default('valid_key_1', 'global_default_1')

        try:
            self.assertEqual(self.siteconfig.get('valid_key_1'),
                             'global_default_1')
        finally:
            SiteConfiguration.remove_global_default('valid_key_1')

    def test_set(self):
        """Testing SiteConfiguration.set"""
        self.siteconfig.set('valid_key_2', 'valid_parameter_2')
        self.siteconfig.set('valid_key_3', 'valid_parameter_3')

        self.assertEqual(
            self.siteconfig.settings,
            {
                'valid_key_2': 'valid_parameter_2',
                'valid_key_3': 'valid_parameter_3',
            })

    def test_add_defaults(self):
        """Testing SiteConfiguration.add_defaults"""
        self.siteconfig.add_defaults({
            'valid_key_1': 'valid_parameter_1',
            'valid_key_2': 'valid_parameter_2',
            'valid_key_3': 'valid_parameter_3',
        })

        try:
            self.assertEqual(self.siteconfig.get('valid_key_1'),
                             'valid_parameter_1')
            self.assertEqual(self.siteconfig.get('valid_key_2'),
                             'valid_parameter_2')
            self.assertEqual(self.siteconfig.get('valid_key_3'),
                             'valid_parameter_3')
        finally:
            self.siteconfig.remove_default('valid_key_1')
            self.siteconfig.remove_default('valid_key_2')
            self.siteconfig.remove_default('valid_key_3')

    def test_add_default(self):
        """Testing SiteConfiguration.add_default"""
        self.siteconfig.add_default('valid_key_1', 'valid_new_parameter_2')

        try:
            self.assertEqual(self.siteconfig.get('valid_key_1'),
                             'valid_new_parameter_2')
        finally:
            self.siteconfig.remove_default('valid_key_1')

    def test_remove_default(self):
        """Testing SiteConfiguration.remove_default"""
        self.siteconfig.add_default('valid_key_1', 'valid_new_parameter_2')
        self.siteconfig.remove_default('valid_key_1')

        self.assertIsNone(self.siteconfig.get('valid_key_1'))

    def test_clear_defaults(self):
        """Testing SiteConfiguration.clear_defaults"""
        self.siteconfig.add_default('valid_key_1', 'valid_new_parameter_1')
        self.siteconfig.add_default('valid_key_2', 'valid_new_parameter_2')
        self.siteconfig.clear_defaults()

        self.assertIsNone(self.siteconfig.get('valid_key_1'))
        self.assertIsNone(self.siteconfig.get('valid_key_2'))

    def test_get_defaults(self):
        """Testing SiteConfiguration.get_defaults"""
        self.siteconfig.add_defaults({
            'valid_key_1': 'valid_parameter_1',
            'valid_key_2': 'valid_parameter_2',
            'valid_key_3': 'valid_parameter_3',
        })
        self.siteconfig.add_default('valid_key_1', 'valid_new_parameter_1')

        try:
            siteconfig_defaults = self.siteconfig.get_defaults()
            self.assertEqual(siteconfig_defaults['valid_key_1'],
                             'valid_new_parameter_1')
            self.assertEqual(siteconfig_defaults['valid_key_2'],
                             'valid_parameter_2')
            self.assertEqual(siteconfig_defaults['valid_key_3'],
                             'valid_parameter_3')
        finally:
            self.siteconfig.remove_default('valid_key_1')
            self.siteconfig.remove_default('valid_key_2')
            self.siteconfig.remove_default('valid_key_3')

    def test_get_defaults_excludes_global_defaults(self):
        """Testing SiteConfiguration.get_defaults excludes global defaults"""
        SiteConfiguration.add_global_default('test_global_key', 123)

        try:
            self.siteconfig.add_defaults({
                'valid_key_1': 'valid_parameter_1',
            })
            self.siteconfig.add_default('valid_key_1', 'valid_new_parameter_1')

            siteconfig_defaults = self.siteconfig.get_defaults()
            self.assertEqual(siteconfig_defaults['valid_key_1'],
                             'valid_new_parameter_1')
            self.assertNotIn('test_global_key', siteconfig_defaults)
        finally:
            SiteConfiguration.remove_global_default('test_global_key')

    def test_add_global_defaults(self):
        """Testing SiteConfiguration.add_global_defaults"""
        SiteConfiguration.add_global_defaults({
            'valid_key_1': 'global_value_1',
            'valid_key_2': 'global_value_2',
            'valid_key_3': 'global_value_3',
        })

        try:
            self.assertEqual(self.siteconfig.get('valid_key_1'),
                             'global_value_1')
            self.assertEqual(self.siteconfig.get('valid_key_2'),
                             'global_value_2')
            self.assertEqual(self.siteconfig.get('valid_key_3'),
                             'global_value_3')
        finally:
            SiteConfiguration.remove_global_default('valid_key_1')
            SiteConfiguration.remove_global_default('valid_key_2')
            SiteConfiguration.remove_global_default('valid_key_3')

    def test_add_default(self):
        """Testing SiteConfiguration.add_global_default"""
        SiteConfiguration.add_global_default('valid_key_1', 'global_value')

        try:
            self.assertEqual(self.siteconfig.get('valid_key_1'),
                             'global_value')
        finally:
            SiteConfiguration.remove_global_default('valid_key_1')

    def test_remove_default(self):
        """Testing SiteConfiguration.remove_default"""
        SiteConfiguration.add_global_default('valid_key_1', 'global_value')
        SiteConfiguration.remove_global_default('valid_key_1')

        self.assertIsNone(self.siteconfig.get('valid_key_1'))

    def test_clear_defaults(self):
        """Testing SiteConfiguration.clear_defaults"""
        SiteConfiguration.add_global_default('valid_key_1', 'global_default_1')
        SiteConfiguration.add_global_default('valid_key_2', 'global_default_2')
        SiteConfiguration.clear_global_defaults()

        self.assertIsNone(self.siteconfig.get('valid_key_1'))
        self.assertIsNone(self.siteconfig.get('valid_key_2'))

    def test_get_defaults(self):
        """Testing SiteConfiguration.get_defaults"""
        SiteConfiguration.add_global_defaults({
            'valid_key_1': 'global_value_1',
            'valid_key_2': 'global_value_2',
            'valid_key_3': 'global_value_3',
        })
        SiteConfiguration.add_global_default('valid_key_1', 'new_global_value')

        try:
            siteconfig_defaults = SiteConfiguration.get_global_defaults()
            self.assertEqual(siteconfig_defaults['valid_key_1'],
                             'new_global_value')
            self.assertEqual(siteconfig_defaults['valid_key_2'],
                             'global_value_2')
            self.assertEqual(siteconfig_defaults['valid_key_3'],
                             'global_value_3')
        finally:
            SiteConfiguration.remove_global_default('valid_key_1')
            SiteConfiguration.remove_global_default('valid_key_2')
            SiteConfiguration.remove_global_default('valid_key_3')


class SiteConfigurationManagerTests(SiteConfigTestCase):
    """Unit tests for SiteConfigurationManager."""

    def test_check_expired_with_stale_cache(self):
        """Testing SiteConfigurationManager.check_expired with stale cache"""
        siteconfig1 = SiteConfiguration.objects.get_current()
        self.assertFalse(siteconfig1.is_expired())

        siteconfig2 = SiteConfiguration.objects.get(site=self.siteconfig.site)
        siteconfig2.set('foobar', 123)

        # Save, and prevent clearing of caches to simulate still having the
        # stale cache around for another thread.
        siteconfig2.save(clear_caches=False)

        self.assertTrue(siteconfig1.is_expired())

        SiteConfiguration.objects.check_expired()

        # See if we fetch the same one again
        siteconfig1 = SiteConfiguration.objects.get_current()
        self.assertEqual(siteconfig1.get('foobar'), 123)

    def test_check_expired_with_expired_cache(self):
        """Testing SiteConfigurationManager.check_expired with an expired
        state in cache
        """
        siteconfig1 = SiteConfiguration.objects.get_current()
        self.assertFalse(siteconfig1.is_expired())

        siteconfig2 = SiteConfiguration.objects.get(site=self.siteconfig.site)
        siteconfig2.set('foobar', 123)

        # Save, and prevent clearing of caches to simulate still having the
        # stale cache around for another thread.
        siteconfig2.save(clear_caches=False)

        cache.delete('%s:siteconfig:%s:generation' %
                     (siteconfig2.site.domain, siteconfig2.id))

        self.assertTrue(siteconfig1.is_expired())

        SiteConfiguration.objects.check_expired()

        # See if we fetch the same one again
        siteconfig1 = SiteConfiguration.objects.get_current()
        self.assertEqual(siteconfig1.get('foobar'), 123)

    def test_check_expired_emits_reloaded_signal(self):
        """Testing SiteConfigurationManager.check_expired emits
        siteconfig_reloaded when expired
        """
        signal_seen = []

        def _on_siteconfig_reloaded(siteconfig, old_siteconfig, **kwargs):
            self.assertIsNot(siteconfig, siteconfig1)
            self.assertIsNot(siteconfig, siteconfig2)
            self.assertIs(old_siteconfig, siteconfig1)
            self.assertEqual(old_siteconfig.settings, siteconfig1.settings)
            self.assertEqual(siteconfig.settings, siteconfig2.settings)
            signal_seen.append(1)

        siteconfig_reloaded.connect(_on_siteconfig_reloaded)

        siteconfig1 = SiteConfiguration.objects.get_current()
        self.assertFalse(siteconfig1.is_expired())

        siteconfig2 = SiteConfiguration.objects.get(site=self.siteconfig.site)
        siteconfig2.set('foobar', 123)

        # Save, and prevent clearing of caches to simulate still having the
        # stale cache around for another thread.
        siteconfig2.save(clear_caches=False)

        self.assertTrue(siteconfig1.is_expired())

        SiteConfiguration.objects.check_expired()

        # See if we fetch the same one again.
        siteconfig1 = SiteConfiguration.objects.get_current()
        self.assertEqual(siteconfig1.get('foobar'), 123)

        # See if the signal was emitted.
        self.assertTrue(signal_seen)
