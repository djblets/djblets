"""Various utility views."""

from __future__ import annotations

import ipaddress
import logging
from enum import Enum
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.cache import caches
from django.core.cache.backends.locmem import LocMemCache
from django.db import connections
from django.db.utils import OperationalError
from django.http import HttpRequest, HttpResponseForbidden, JsonResponse
from django.utils.translation import get_language
from django.views.generic import View
from django.views.i18n import JavaScriptCatalog
from typing_extensions import TypedDict

from djblets.cache.backend import cache_memoize, make_cache_key
from djblets.cache.serials import generate_locale_serial
from djblets.util.symbols import UNSET

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from django.db.backends.utils import CursorWrapper
    from django.http.response import HttpResponse


logger = logging.getLogger(__name__)
locale_serials: dict[str, int] = {}


def cached_javascript_catalog(
    request: HttpRequest,
    domain: str = 'djangojs',
    packages: Sequence[str] = [],
) -> HttpResponse:
    """A cached version of javascript_catalog.

    Args:
        request (django.http.HttpRequest):
            The HTTP request.

        domain (str):
            The translation domain to use when looking up strings.

        packages (list of str):
            The package names to get strings from.

    Returns:
        django.http.HttpResponse:
        The response to send back to the client.
    """
    global locale_serials

    package_str = '_'.join(packages)

    try:
        serial = locale_serials[package_str]
    except KeyError:
        serial = generate_locale_serial(packages)
        locale_serials[package_str] = serial

    return cache_memoize(
        ('jsi18n', domain, package_str, get_language(), str(serial)),
        lambda: JavaScriptCatalog.as_view(domain=domain,
                                          packages=packages)(request),
        large_data=True,
        compress_large_data=True)


class HealthCheckStatus(str, Enum):
    """A status indicator for health checks.

    Version Added:
        4.0
    """
    # TODO: this can inherit from StrEnum once we're Python 3.11+

    #: The state when a service is running and can be connected to.
    UP = 'UP'

    #: The state when a service is down or otherwise cannot be connected to.
    DOWN = 'DOWN'

    #: The state when it is unknown if a service is up or down.
    UNKNOWN = 'UNKNOWN'

    def __str__(self) -> str:
        """Return a string representation of the status.

        This exists so we can compare a string against an enum. Once we move to
        StrEnum this can be removed.

        Returns:
            str:
            The string status.
        """
        return str.__str__(self)


class HealthCheckResult(TypedDict):
    """Result structure for health checks.

    Version Added:
        4.0
    """

    #: The individual checks that were run.
    checks: dict[str, HealthCheckStatus]

    #: A mapping of the check name to the error if the service is down.
    errors: dict[str, str]

    #: The overall health status of the server.
    status: HealthCheckStatus


class HealthCheckView(View):
    """A view for health checks.

    This will check the status of connected database and cache servers, and
    report whether everything can be accessed. It will return either HTTP 200
    or 503, and the payload will be a JSON blob defined by
    :py:class:`HealthCheckResult`.

    This will only allow requests from whitelisted IP addresses. These are set
    in a Django setting named ``DJBLETS_HEALTHCHECK_IPS``, which should be a
    list of strings.

    Version Changed:
        5.3:
        Changed to allow CIDR subnets in the ``DJBLETS_HEALTHCHECK_IPS``
        setting.

    Version Added:
        4.0
    """

    def get(
        self,
        request: HttpRequest,
        *args,
        **kwargs,
    ) -> HttpResponse:
        """Perform a health check.

        This will do a health check on whether the database and cache server
        can be used. If both are accessible, this will return an HTTP 200. If
        not, this will return HTTP 500.

        Version Changed:
            5.3:
            Changed IP matching to use networks instead of single IP addresses.

        Args:
            request (django.http.HttpRequest):
                The HTTP request.

            *args (tuple, unused):
                Positional arguments, for future expansion.

            **kwargs (dict, unused):
                Keyword arguments, for future expansion.

        Returns:
            django.http.JsonResponse:
            The response to send back to the client.
        """
        allowed_ips = getattr(settings, 'DJBLETS_HEALTHCHECK_IPS',
                              settings.INTERNAL_IPS)

        if not isinstance(allowed_ips, list):
            logger.error('Health check: setting "%r" for healthcheck IPs must '
                         'be a list, got type "%r".',
                         allowed_ips, type(allowed_ips))

            return HttpResponseForbidden()

        remote_addr = request.META.get('REMOTE_ADDR')
        assert isinstance(remote_addr, str)

        networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []

        for network in allowed_ips:
            try:
                networks.append(ipaddress.ip_network(network))
            except ValueError:
                logger.error('Health check: invalid value in setting '
                             'DJBLETS_HEALTHCHECK_IPS: %r',
                             network)

        address = ipaddress.ip_address(remote_addr)

        if not any(address in network for network in networks):
            logger.warning('Health check: got request to healthcheck endpoint '
                           'from invalid remote address %s',
                           remote_addr)

            return HttpResponseForbidden()

        result: HealthCheckResult = {
            'checks': {},
            'errors': {},
            'status': HealthCheckStatus.UP,
        }
        status: int = 200
        success: bool = True

        for key in self._get_database_names():
            result_key = f'database.{key}'

            try:
                with self._get_db_cursor(key):
                    pass

                result['checks'][result_key] = HealthCheckStatus.UP
            except OperationalError as e:
                logger.error('Health check: unable to connect to database '
                             '"%s": %s',
                             key, e,
                             extra={'request': request})

                success = False
                result['checks'][result_key] = HealthCheckStatus.DOWN
                result['errors'][result_key] = str(e)

        cache_key = make_cache_key('djblets-healthcheck')

        for key in settings.CACHES:
            if key == 'forwarded_backend':
                # This is the backing for a Djblets cache forwarding backend
                # (which will be covered under another cache backend key).
                # We can skip this one.
                continue

            result_key = f'cache.{key}'

            try:
                cache = caches[key]

                if isinstance(cache, LocMemCache):
                    # This is a local memory cache. If it doesn't work, the
                    # server is *really* in trouble. We can probably filter
                    # it out, though.
                    continue

                # Check for a key in the cache.
                #
                # We have to do this as two non-atomic operations:
                #
                # 1. Set a key explicitly.
                # 2. Check that something was set.
                #
                # The reason is that some cache backends (pymemcache notably)
                # has mitigation against intermittent outages/bad connections.
                # They can mask outages until a certain number of failures
                # have occurred, and then re-introduce the failed servers
                # after a period of time.
                #
                # These timeframes cause problems with standard service health
                # check behavior, which often employ a Circuit Breaker pattern,
                # requiring a certain number of failures within a certain
                # amount of time before considering a service unhealthy, and
                # then resetting when considering any successful result. This
                # does not play well with the cache backend mitigations.
                #
                # Since the cache backends return a caller-provided default
                # when in outage mitigation mode, we need to check whether the
                # key we just stored can be returned or just disappears. We
                # don't really care about the value itself, just whether we
                # got back a default.
                #
                # Note that this can have a false-positive if the cache server
                # happens to lose our newly-set key right away, but health
                # checks should be able to handle a sporadic outage report.
                cache.set(cache_key, True)

                if cache.get(cache_key, UNSET) is UNSET:
                    raise Exception('Unable to communicate with cache server')

                result['checks'][result_key] = HealthCheckStatus.UP
            except Exception as e:
                logger.error('Health check: unable to connect to cache '
                             '"%s": %s',
                             key, e,
                             extra={'request': request})

                success = False
                result['checks'][result_key] = HealthCheckStatus.DOWN
                result['errors'][result_key] = str(e)

        if not success:
            status = 503
            result['status'] = HealthCheckStatus.DOWN

        return JsonResponse(result, status=status)

    def _get_database_names(self) -> Iterable[str]:
        """Return a list of configured database names.

        This method exists to make it easier to do unit tests.

        Version Added:
            5.3

        Returns:
            iterator of str:
            An iterator of the database names.
        """
        return settings.DATABASES.keys()

    def _get_db_cursor(
        self,
        name: str,
    ) -> CursorWrapper:
        """Return a database cursor.

        This method exists to make it easier to do unit tests.

        Version Added:
            5.3

        Args:
            name (str):
                The name of the database to get the cursor for.

        Returns:
            django.db.backends.utils.CursorWrapper:
            The database cursor.

        Raises:
            django.db.utils.OperationalError:
                The database could not be connected.
        """
        return connections[name].cursor()
