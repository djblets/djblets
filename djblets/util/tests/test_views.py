"""Unit tests for djblets.util.views.

Version Added:
    5.3
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

import kgb
from django.conf import settings
from django.core.cache import caches
from django.db.utils import OperationalError
from django.test import RequestFactory, override_settings

from djblets.testing.testcases import TestCase
from djblets.util.symbols import UNSET
from djblets.util.views import (
    HealthCheckStatus,
    HealthCheckView,
    logger as views_logger,
)

if TYPE_CHECKING:
    from collections.abc import Iterator


@contextmanager
def _db_cursor() -> Iterator[None]:
    """Fake cursor method for successful tests.

    Version Added:
        5.3
    """
    yield


class HealthCheckViewTests(kgb.SpyAgency, TestCase):
    """Unit tests for djblets.util.views.HealthCheckView.

    Version Added:
        5.3
    """

    #: The request factory to use.
    factory: RequestFactory

    #: The view instance to test.
    view: HealthCheckView

    @classmethod
    def setUpClass(cls) -> None:
        """Set up the test case."""
        super().setUpClass()
        cls.factory = RequestFactory()
        cls.view = HealthCheckView()

    @classmethod
    def tearDownClass(cls) -> None:
        """Tear down the test case class."""
        del cls.factory
        del cls.view

    @override_settings(DJBLETS_HEALTHCHECK_IPS=['192.168.1.0/24'])
    def test_get_with_forbidden_ip(self) -> None:
        """Testing HealthCheckView.get with forbidden IP address"""
        request = self.factory.get('/health/')
        request.META['REMOTE_ADDR'] = '10.0.0.1'

        response = self.view.get(request)

        self.assertEqual(response.status_code, 403)

    @override_settings(
        DJBLETS_HEALTHCHECK_IPS=['192.168.1.100'],
        CACHES={
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            },
        },
    )
    def test_get_with_allowed_ip_single(self) -> None:
        """Testing HealthCheckView.get with allowed single IP address"""
        request = self.factory.get('/health/')
        request.META['REMOTE_ADDR'] = '192.168.1.100'

        self.spy_on(self.view._get_database_names,
                    op=kgb.SpyOpReturn(['default']))
        self.spy_on(
            self.view._get_db_cursor,
            op=kgb.SpyOpMatchInOrder([
                {
                    'args': ['default'],
                    'op': kgb.SpyOpReturn(_db_cursor()),
                },
            ]))

        response = self.view.get(request)

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content.decode(), {
            'checks': {
                'database.default': HealthCheckStatus.UP,
            },
            'errors': {},
            'status': HealthCheckStatus.UP,
        })

    @override_settings(
        DJBLETS_HEALTHCHECK_IPS=['192.168.1.0/24'],
        CACHES={
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            },
        },
    )
    def test_get_with_allowed_ip_network(self) -> None:
        """Testing HealthCheckView.get with allowed IP network"""
        request = self.factory.get('/health/')
        request.META['REMOTE_ADDR'] = '192.168.1.50'

        self.spy_on(self.view._get_database_names,
                    op=kgb.SpyOpReturn(['default']))
        self.spy_on(
            self.view._get_db_cursor,
            op=kgb.SpyOpMatchInOrder([
                {
                    'args': ['default'],
                    'op': kgb.SpyOpReturn(_db_cursor()),
                },
            ]))

        response = self.view.get(request)

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content.decode(), {
            'checks': {
                'database.default': HealthCheckStatus.UP,
            },
            'errors': {},
            'status': HealthCheckStatus.UP,
        })

    @override_settings(
        DJBLETS_HEALTHCHECK_IPS=[
            '192.168.1.0/24',
            '10.0.0.0/8',
        ],
        CACHES={
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            },
        },
    )
    def test_get_with_multiple_allowed_networks(self) -> None:
        """Testing HealthCheckView.get with multiple allowed networks"""
        request = self.factory.get('/health/')
        request.META['REMOTE_ADDR'] = '10.0.0.5'

        self.spy_on(self.view._get_database_names,
                    op=kgb.SpyOpReturn(['default']))
        self.spy_on(
            self.view._get_db_cursor,
            op=kgb.SpyOpMatchInOrder([
                {
                    'args': ['default'],
                    'op': kgb.SpyOpReturn(_db_cursor()),
                },
            ]))

        response = self.view.get(request)

        self.assertEqual(response.status_code, 200)

    @override_settings(DJBLETS_HEALTHCHECK_IPS='192.168.1.0/24')
    def test_get_with_invalid_healthcheck_ips_setting(self) -> None:
        """Testing HealthCheckView.get with invalid DJBLETS_HEALTHCHECK_IPS"""
        request = self.factory.get('/health/')
        request.META['REMOTE_ADDR'] = '192.168.1.50'

        with self.assertLogs(views_logger) as logs:
            response = self.view.get(request)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(logs.output, [
            'ERROR:djblets.util.views:Health check: setting '
            '"\'192.168.1.0/24\'" for healthcheck IPs must be a list, got '
            'type "<class \'str\'>".',
        ])

    @override_settings(
        INTERNAL_IPS=['127.0.0.1'],
        CACHES={
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            },
        },
    )
    def test_get_uses_internal_ips_fallback(self) -> None:
        """Testing HealthCheckView.get uses INTERNAL_IPS as fallback"""
        # Remove DJBLETS_HEALTHCHECK_IPS if it exists.
        del settings.DJBLETS_HEALTHCHECK_IPS

        request = self.factory.get('/health/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'

        self.spy_on(self.view._get_database_names,
                    op=kgb.SpyOpReturn(['default']))
        self.spy_on(
            self.view._get_db_cursor,
            op=kgb.SpyOpMatchInOrder([
                {
                    'args': ['default'],
                    'op': kgb.SpyOpReturn(_db_cursor()),
                },
            ]))

        response = self.view.get(request)

        self.assertEqual(response.status_code, 200)

    @override_settings(
        DJBLETS_HEALTHCHECK_IPS=['127.0.0.1'],
        CACHES={
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            },
        },
    )
    def test_get_with_database_connection_failure(self) -> None:
        """Testing HealthCheckView.get with database connection failure"""
        request = self.factory.get('/health/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'

        self.spy_on(self.view._get_database_names,
                    op=kgb.SpyOpReturn(['default']))
        self.spy_on(
            self.view._get_db_cursor,
            op=kgb.SpyOpMatchInOrder([
                {
                    'args': ['default'],
                    'op': kgb.SpyOpRaise(
                        OperationalError('Connection failed')),
                },
            ]))

        with self.assertLogs(views_logger) as logs:
            response = self.view.get(request)

        self.assertEqual(response.status_code, 503)
        self.assertJSONEqual(response.content.decode(), {
            'checks': {
                'database.default': HealthCheckStatus.DOWN,
            },
            'errors': {
                'database.default': 'Connection failed',
            },
            'status': HealthCheckStatus.DOWN,
        })

        self.assertEqual(logs.output, [
            'ERROR:djblets.util.views:Health check: unable to connect to '
            'database "default": Connection failed',
        ])

    @override_settings(
        DJBLETS_HEALTHCHECK_IPS=['127.0.0.1'],
        CACHES={
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            },
            'memcache': {
                'BACKEND': 'django.core.cache.backends.memcached.'
                           'PyMemcacheCache',
            },
        },
    )
    def test_get_with_cache_connection_failure(self) -> None:
        """Testing HealthCheckView.get with cache connection failure"""
        request = self.factory.get('/health/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'

        self.spy_on(self.view._get_database_names,
                    op=kgb.SpyOpReturn(['default']))
        self.spy_on(
            self.view._get_db_cursor,
            op=kgb.SpyOpMatchInOrder([
                {
                    'args': ['default'],
                    'op': kgb.SpyOpReturn(_db_cursor()),
                },
            ]))
        self.spy_on(
            caches['memcache'].set,
            op=kgb.SpyOpRaise(Exception('Memcached connection failed')))

        with self.assertLogs(views_logger) as logs:
            response = self.view.get(request)

        self.assertEqual(response.status_code, 503)
        self.assertJSONEqual(response.content.decode(), {
            'checks': {
                'database.default': HealthCheckStatus.UP,
                'cache.memcache': HealthCheckStatus.DOWN,
            },
            'errors': {
                'cache.memcache': 'Memcached connection failed',
            },
            'status': HealthCheckStatus.DOWN,
        })
        self.assertEqual(logs.output, [
            'ERROR:djblets.util.views:Health check: unable to connect to '
            'cache "memcache": Memcached connection failed',
        ])

    @override_settings(
        DJBLETS_HEALTHCHECK_IPS=['127.0.0.1'],
        CACHES={
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            },
            'memcache': {
                'BACKEND': 'django.core.cache.backends.memcached.'
                           'PyMemcacheCache',
            },
        }
    )
    def test_get_skips_locmem_cache(self) -> None:
        """Testing HealthCheckView.get skips local memory cache"""
        request = self.factory.get('/health/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'

        self.spy_on(self.view._get_database_names,
                    op=kgb.SpyOpReturn(['default']))
        self.spy_on(
            self.view._get_db_cursor,
            op=kgb.SpyOpMatchInOrder([
                {
                    'args': ['default'],
                    'op': kgb.SpyOpReturn(_db_cursor()),
                },
            ]))
        self.spy_on(caches['memcache'].set, op=kgb.SpyOpReturn(None))
        self.spy_on(caches['memcache'].get, op=kgb.SpyOpReturn(True))

        response = self.view.get(request)

        self.assertEqual(response.status_code, 200)

        # Local memory cache (cache.default) should not be in checks.
        self.assertJSONEqual(response.content.decode(), {
            'checks': {
                'database.default': HealthCheckStatus.UP,
                'cache.memcache': HealthCheckStatus.UP,
            },
            'errors': {},
            'status': HealthCheckStatus.UP,
        })

    @override_settings(
        DJBLETS_HEALTHCHECK_IPS=['127.0.0.1'],
        CACHES={
            'memcache': {
                'BACKEND': 'django.core.cache.backends.memcached.'
                           'PyMemcacheCache',
            },
        },
    )
    def test_get_with_cache_key_not_retrieved(self) -> None:
        """Testing HealthCheckView.get with cache key not being retrieved"""
        request = self.factory.get('/health/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'

        self.spy_on(self.view._get_database_names,
                    op=kgb.SpyOpReturn(['default']))
        self.spy_on(
            self.view._get_db_cursor,
            op=kgb.SpyOpMatchInOrder([
                {
                    'args': ['default'],
                    'op': kgb.SpyOpReturn(_db_cursor()),
                },
            ]))
        self.spy_on(caches['memcache'].set, op=kgb.SpyOpReturn(None))
        self.spy_on(caches['memcache'].get, op=kgb.SpyOpReturn(UNSET))

        with self.assertLogs(views_logger) as logs:
            response = self.view.get(request)

        self.assertEqual(response.status_code, 503)
        self.assertJSONEqual(response.content.decode(), {
            'checks': {
                'cache.memcache': HealthCheckStatus.DOWN,
                'database.default': HealthCheckStatus.UP,
            },
            'errors': {
                'cache.memcache': 'Unable to communicate with cache server',
            },
            'status': HealthCheckStatus.DOWN,
        })
        self.assertEqual(logs.output, [
            'ERROR:djblets.util.views:Health check: unable to connect to '
            'cache "memcache": Unable to communicate with cache server',
        ])

    @override_settings(
        DJBLETS_HEALTHCHECK_IPS=['127.0.0.1'],
        CACHES={
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            },
            'memcache': {
                'BACKEND': 'django.core.cache.backends.memcached.'
                           'PyMemcacheCache',
            },
        }
    )
    def test_get_successful_health_check(self) -> None:
        """Testing HealthCheckView.get with successful health check"""
        request = self.factory.get('/health/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'

        self.spy_on(self.view._get_database_names,
                    op=kgb.SpyOpReturn(['default', 'secondary']))
        self.spy_on(
            self.view._get_db_cursor,
            op=kgb.SpyOpMatchInOrder([
                {
                    'args': ['default'],
                    'op': kgb.SpyOpReturn(_db_cursor()),
                },
                {
                    'args': ['secondary'],
                    'op': kgb.SpyOpReturn(_db_cursor()),
                },
            ]))

        response = self.view.get(request)

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content.decode(), {
            'checks': {
                'cache.memcache': HealthCheckStatus.UP,
                'database.default': HealthCheckStatus.UP,
                'database.secondary': HealthCheckStatus.UP,
            },
            'errors': {},
            'status': HealthCheckStatus.UP,
        })
