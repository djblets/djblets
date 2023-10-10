"""Various utility views."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Dict, Sequence

from django.conf import settings
from django.core.cache import caches
from django.core.cache.backends.locmem import LocMemCache
from django.db import connections
from django.db.utils import OperationalError
from django.http import HttpRequest, HttpResponseForbidden, JsonResponse
from django.http.response import HttpResponseBase
from django.utils.translation import get_language
from django.views.generic import View
from django.views.i18n import JavaScriptCatalog
from typing_extensions import TypedDict

from djblets.cache.backend import cache_memoize, make_cache_key
from djblets.cache.serials import generate_locale_serial
from djblets.util.symbols import UNSET


logger = logging.getLogger(__name__)
locale_serials: Dict[str, int] = {}


def cached_javascript_catalog(
    request: HttpRequest,
    domain: str = 'djangojs',
    packages: Sequence[str] = [],
) -> HttpResponseBase:
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
        'jsi18n-%s-%s-%s-%d' % (domain, package_str, get_language(), serial),
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
    checks: Dict[str, HealthCheckStatus]

    #: A mapping of the check name to the error if the service is down.
    errors: Dict[str, str]

    #: The overall health status of the server.
    status: HealthCheckStatus


class HealthCheckView(View):
    """A view for health checks.

    This will check the status of connected database and cache servers, and
    report whether everything can be accessed. It will return either HTTP 200
    or 503, and the payload will be a JSON blob defined by
    :py:class:`HealthCheckResult`.

    Version Added:
        4.0
    """

    def get(
        self,
        request: HttpRequest,
        *args,
        **kwargs,
    ) -> HttpResponseBase:
        """Perform a health check.

        This will do a health check on whether the database and cache server
        can be used. If both are accessible, this will return an HTTP 200. If
        not, this will return HTTP 500.

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

        if request.META.get('REMOTE_ADDR') not in allowed_ips:
            return HttpResponseForbidden()

        result: HealthCheckResult = {
            'checks': {},
            'errors': {},
            'status': HealthCheckStatus.UP,
        }
        status: int = 200
        success: bool = True

        for key in settings.DATABASES.keys():
            result_key = f'database.{key}'

            try:
                db = connections[key]

                with db.cursor():
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

        for key in settings.CACHES.keys():
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
