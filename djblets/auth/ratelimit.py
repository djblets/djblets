"""Utilities for rate-limiting login attempts."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, TypedDict

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext as _
from housekeeping import ClassDeprecatedMixin

from djblets.deprecation import RemovedInDjblets70Warning
from djblets.http.requests import get_http_request_ip
from djblets.protect.ratelimit import RateLimit, check_rate_limit

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Any

    from django.http import HttpRequest


logger = logging.getLogger(__name__)


#: Available rate limit categories.
RATE_LIMIT_LOGIN = 0
RATE_LIMIT_API_ANONYMOUS = 1
RATE_LIMIT_API_AUTHENTICATED = 2


#: The default rate limit for logins.
DEFAULT_LOGIN_LIMIT_RATE = '5/m'

#: The default rate limit for anonymous API requests.
DEFAULT_API_ANONYMOUS_LIMIT_RATE = '1000/h'

#: The default rate limit for authenticated API requests.
DEFAULT_API_AUTHENTICATED_LIMIT_RATE = '10000/h'


_RATE_LIMIT_DATA = {
    RATE_LIMIT_LOGIN: (
        'LOGIN_LIMIT_RATE',
        DEFAULT_LOGIN_LIMIT_RATE,
        'login-ratelimit'),
    RATE_LIMIT_API_ANONYMOUS: (
        'API_ANONYMOUS_LIMIT_RATE',
        DEFAULT_API_ANONYMOUS_LIMIT_RATE,
        'api-anonymous-ratelimit'),
    RATE_LIMIT_API_AUTHENTICATED: (
        'API_AUTHENTICATED_LIMIT_RATE',
        DEFAULT_API_AUTHENTICATED_LIMIT_RATE,
        'api-authenticated-ratelimit'),
}


class UsageCount(TypedDict):
    """Rate limit states for a given user or IP address.

    Version Added:
        6.0
    """

    #: The number of login attempts made.
    count: int

    #: The number of attempts allowed.
    limit: int

    #: The time left before the rate limit is over.
    time_left: int


def get_user_id_or_ip(
    request: HttpRequest,
) -> str:
    """Return the user's ID or IP address from the given HTTP request.

    Args:
        request (django.http.HttpRequest):
            The HTTP request from the client.

    Returns:
        str:
        If the user is authenticated, the user ID will be returned.
        Otherwise, the IP address of the client is returned instead.
    """
    if hasattr(request, 'user') and request.user.is_authenticated:
        return str(request.user.pk)

    return get_http_request_ip(request)


def is_ratelimited(
    request: HttpRequest,
    increment: bool = False,
    limit_type: int = RATE_LIMIT_LOGIN,
) -> bool:
    """Check whether the user or IP address has exceeded the rate limit.

    The parameters are used to create a new key or fetch an existing key to
    save or update to the cache and to determine the amount of time period
    left.

    Args:
        request (django.http.HttpRequest):
            The HTTP request from the client.

        increment (bool, optional):
            Whether the number of login attempts should be incremented.

        limit_type (int, optional):
            The type of rate limit to check.

    Returns:
        bool:
        Whether the current user has exceeded the rate limit of login attempts.
    """
    usage = get_usage_count(request, increment, limit_type)
    return (usage is not None and
            usage['count'] > usage['limit'])


def get_usage_count(
    request: HttpRequest,
    increment: bool = False,
    limit_type: int = RATE_LIMIT_LOGIN,
) -> UsageCount | None:
    """Return rate limit status for a given user or IP address.

    This method performs validation checks on the input parameters
    and creates the cache key to keep track of the
    number of login attempts made by the user. It saves the new
    cache key and initial number of attempts or updates the
    existing cache key and number of attempts before returning
    the count, limit, and time_left.

    Args:
        request (django.http.HttpRequest):
            The HTTP request from the client.

        increment (bool, optional):
            Whether the number of login attempts should be incremented.

        limit_type (int, optional):
            The type of rate limit to check.

    Returns:
        UsageCount:
        The rate limit status.

    Raises:
        ValueError:
            An invalid value was specified for ``limit_type``.

        django.core.exceptions.ImproperlyConfigured:
            A rate limit setting could not be parsed.
    """
    try:
        settings_key, default_value = _RATE_LIMIT_DATA[limit_type][:2]
    except KeyError:
        raise ValueError(_('"limit_type" argument had unexpected value "%s"')
                         % limit_type)

    limit_str = getattr(settings, settings_key, default_value)

    if limit_str is None:
        # If the setting is explicitly None, don't do any rate limiting.
        return None

    try:
        rate_limit = RateLimit.parse(limit_str)
    except ValueError:
        raise ImproperlyConfigured(
            _('{key} setting could not be parsed as a rate limit value.')
            .format(key=settings_key))

    key = _get_auth_rate_limit_key(request=request,
                                   limit_type=limit_type)

    usage = check_rate_limit(rate_limit=rate_limit,
                             key=key,
                             increment_count=increment)

    if usage is None:
        return None

    return {
        'count': usage.count,
        'limit': usage.limit,
        'time_left': usage.time_left_secs,
    }


def _get_auth_rate_limit_key(
    request: HttpRequest,
    *,
    limit_type: int = RATE_LIMIT_LOGIN,
) -> Sequence[str]:
    """Return a rate limit key used to interact with rate limit data.

    The key will be specific to the rate limit type and the user or IP address
    from the request.

    Version Added:
        5.3

    Args:
        request (django.http.HttpRequest):
            The HTTP request from the client.

        limit_type (int, optional):
            The rate limit type to use for the key.

    Returns:
        list of str:
        A 2-entry list in the form of:

        1. The resulting rate limit key.
        2. The result of :py:func:`get_user_id_or_ip`.

    Raises:
        ValueError:
            An invalid value was specified for ``limit_type``.
    """
    try:
        cache_key_prefix = _RATE_LIMIT_DATA[limit_type][2]
    except KeyError:
        raise ValueError('"limit_type" argument had unexpected value "%s"'
                         % limit_type)

    user_id_or_ip = get_user_id_or_ip(request)

    return [cache_key_prefix, user_id_or_ip]


class Rate(ClassDeprecatedMixin,
           warning_cls=RemovedInDjblets70Warning):
    """A rate representing login attempt frequency.

    The main functionality of this class is found in the :py:meth:`parse`
    function. This class converts a rate into a Rate object, which
    contains the number of login attempts allowed within a time period based
    on a given rate string.

    Deprecated:
        5.3:
        This has been replaced with
        :py:class:`djblets.protect.ratelimit.RateLimit`. Callers should be
        updated to use this instead.
    """

    #: Dictionary contains keys that represent different time periods.
    #:
    #: The time periods are represented in seconds for days, hours,
    #: minutes, and seconds.

    PERIODS = {
        's': 1,
        'm': 60,
        'h': 60 * 60,
        'd': 24 * 60 * 60,
    }

    #: Regular expression that interprets the rate string.
    RATE_RE = re.compile(r'(\d+)/(\d*)([smhd])?')

    @classmethod
    def parse(cls, rate_str):
        """Return a Rate parsed from the given rate string.

        Converts the given rate string into a Rate object, which contains
        the number of login attempts allowed (count) and the time period
        alotted for these attempts (seconds).

        Args:
            rate (unicode):
                The number of attempts allowed within a period
                of time (can be seconds, minutes, hours, or days).

        Returns:
            Rate:
            A Rate object that returns the number of login attempts
            allowed (count), and the total time period for these attempts
            (seconds).

        Raises:
            ValueError:
                The provided ``rate_str`` value could not be parsed.
        """
        m = Rate.RATE_RE.match(rate_str)

        if m:
            count, multiplier, period = m.groups()
        else:
            raise ValueError('Could not parse given rate: %s.' % rate_str)

        seconds = Rate.PERIODS[period or 's']

        if multiplier:
            seconds *= int(multiplier)

        return cls(count=int(count), seconds=seconds)

    def __init__(self, count, seconds):
        """Initialize attributes for the Rate object.

        This initializes the number of failed login attempts allowed, and
        the time period for the login attempts in seconds based on the
        data returned from the parse() function.

        Args:
            count (int):
                The number of failed login attempts allowed.

            seconds (int):
                The time period for the login attempts in seconds.
        """
        self.count = count
        self.seconds = seconds

    def __eq__(self, other):
        """Return whether the two Rate instances are equal.

        Returns:
            bool:
            Return true if the count and seconds match.
        """
        return (isinstance(other, Rate) and
                self.count == other.count and
                self.seconds == other.seconds)
