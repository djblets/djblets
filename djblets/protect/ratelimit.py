"""General support for rate limiting of operations.

This can be used to impose rate limits on operations or access to resources,
locked down to a user, IP, or any other criteria.

Version Added:
    5.3
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.core.cache import cache
from django.utils.translation import gettext as _
from typing_extensions import Self

from djblets.cache.backend import make_cache_key

if TYPE_CHECKING:
    from collections.abc import Sequence


logger = logging.getLogger(__name__)


@dataclass
class RateLimitUsage:
    """Usage information for a rate limit key.

    This information can be used to determine if a user has any activity
    remaining before hitting a rate limit, or if they've hit the limit.

    Version Added:
        5.3
    """

    #: The number of attempts made against the rate limit key.
    count: int

    #: The total number of attempts allowed.
    limit: (int | None) = None

    #: The time remaining in seconds before the rate limit resets.
    time_left_secs: (int | None) = None

    @property
    def is_limited(self) -> bool:
        """Whether the usage has hit the rate limit.

        Type:
            bool
        """
        limit = self.limit

        return limit is not None and self.count > limit


class RateLimit:
    """A rate limit applied to an operation or access.

    This represents the data behind a parsed rate limit imposed on an
    operation or access to a resource.

    Version Added:
        5.3
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
    RATE_RE = re.compile(r'^(\d+)/(\d*)([smhd])?$')

    ######################
    # Instance variables #
    ######################

    #: The time period in seconds for a rate limit window.
    period_secs: int

    #: The total number of failed attempts allowed.
    total_limit: int

    @classmethod
    def parse(
        cls,
        rate_str: str,
    ) -> Self:
        """Return a RateLimit parsed from the given rate string.

        Converts the given rate string into a Rate object, which contains
        the number of login attempts allowed (count) and the time period
        alotted for these attempts (seconds).

        Args:
            rate (str):
                The number of attempts allowed within a period
                of time (can be seconds, minutes, hours, or days).

        Returns:
            RateLimit:
            The parsed rate limit information.
        """
        m = cls.RATE_RE.match(rate_str)

        if m:
            count, multiplier, period = m.groups()
        else:
            raise ValueError(_('Could not parse given rate limit: %s.')
                             % rate_str)

        period_secs = cls.PERIODS[period or 's']

        if multiplier:
            period_secs *= int(multiplier)

        return cls(total_limit=int(count),
                   period_secs=period_secs)

    def __init__(
        self,
        *,
        total_limit: int,
        period_secs: int,
    ) -> None:
        """Initialize attributes for the Rate object.

        This initializes the number of failed login attempts allowed, and
        the time period for the login attempts in seconds based on the
        data returned from the :py:meth:`parse` function.

        Args:
            total_limit (int):
                The total number of failed attempts allowed.

            period_secs (int):
                The time period in seconds for a rate limit window.
        """
        self.total_limit = total_limit
        self.period_secs = period_secs

    def get_reset_timestamp(
        self,
        timestamp: int,
    ) -> int:
        """Return the timestamp until a rate limit is reset.

        This calculates the number of seconds from the given timestamp when
        a rate limit period will reset.

        Args:
            timestamp (int):
                The time in seconds used as "now" for the calculation.

        Returns:
            int:
            The timestamp at which the rate limit will reset.
        """
        period_secs = self.period_secs

        if period_secs == 1:
            # The window will reset now.
            return timestamp

        return timestamp - (timestamp % period_secs) + period_secs

    def __eq__(
        self,
        other: object,
    ) -> bool:
        """Return whether the two Rate instances are equal.

        Args:
            other (object):
                The object to compare to.

        Returns:
            bool:
            Return true if the count and seconds match.
        """
        return (isinstance(other, RateLimit) and
                self.total_limit == other.total_limit and
                self.period_secs == other.period_secs)

    def __repr__(self) -> str:
        """Return a string representation of the instance.

        Returns:
            str:
            The string representation.
        """
        return (
            f'<RateLimit(period_secs={self.period_secs!r}, '
            f'total_limit={self.total_limit!r})>'
        )


def check_rate_limit(
    *,
    rate_limit: RateLimit | str | None,
    key: str | Sequence[str],
    increment_count: bool = False,
) -> RateLimitUsage:
    """Return rate limit status for a given key.

    This fetches the rate limit status for a key, optionally incrementing the
    count towards the limit in the process.

    Version Added:
        5.3

    Args:
        rate_limit (str or RateLimit):
            The default limit for any new rate limits.

            This may be a rate limit string or a pre-parsed
            :py:class:`RateLimit`.

            If ``None``, then rate limiting will not be performed. A result
            with a count of 1 will be returned.

        key (str or list of str):
            The rate limit key associated with the rate limit.

            This key is used along with other state to form a cache key. It
            may be a string or a sequence of components for a key.

        increment_count (bool, optional):
            Whether to increment the count toward the rate limit.

    Returns:
        RateLimitUsage:
        The resulting rate limit stats for the key.
    """
    if rate_limit is None:
        # If the setting is explicitly None, don't do any rate limiting.
        return RateLimitUsage(count=1)

    if isinstance(rate_limit, str):
        rate_limit = RateLimit.parse(rate_limit)

    limit = rate_limit.total_limit
    period_secs = rate_limit.period_secs

    # Prepare cache key to add or update to cache and determine remaining time
    # period left.
    now = _get_time_int()
    window = rate_limit.get_reset_timestamp(now)
    time_left_secs = window - now

    # Build a key for the cache to track usage.
    if isinstance(key, str):
        key = [key]

    cache_key = make_cache_key([
        '_ratelimit_',
        *key,
        f'{limit}/{period_secs}',
        str(window),
    ])

    # Check and track the rate limit count.
    count: (int | None) = None

    if increment_count:
        try:
            try:
                count = cache.incr(cache_key)
            except ValueError:
                # Add this to the cache, and set expiration 1 minute beyond
                # the window to help avoid race conditions or clock skew,
                cache.add(cache_key, 1, timeout=window + 60)
        except Exception as e:
            logger.exception('Failed to set rate limit cache key "%s". Rate '
                             'limit checks are currently unreliable. Is the '
                             'cache server down? Error = %s',
                             cache_key, e)

    if count is None:
        try:
            count = cache.get(cache_key, 0)
        except Exception as e:
            logger.exception('Failed to fetch rate limit cache key "%s". Rate '
                             'limit checks are currently unreliable. Is the '
                             'cache server down? Error = %s',
                             cache_key, e)
            count = 0

    assert count is not None

    if not increment_count:
        # Add one to the returned value, even if we aren't incrementing the
        # stored value. This makes it so that we're consistent in how many
        # tries per period regardless of whether we're incrementing now or
        # later.
        count += 1

    return RateLimitUsage(count=count,
                          limit=limit,
                          time_left_secs=time_left_secs)


def _get_time_int() -> int:
    """Return the current time as an integer rounded to the nearest second.

    This is available as a convenience wrapper to help with unit testing.

    Version Added:
        5.3

    Returns:
        int:
        The current time rounded to the nearest second.
    """
    return int(time.time())
