"""Unit tests for djblets.protect.ratelimit.

Version Added:
    5.3
"""

from __future__ import annotations

import kgb
from django.core.cache import cache

from djblets.protect.ratelimit import (
    RateLimit,
    RateLimitUsage,
    _get_time_int,
    check_rate_limit,
)
from djblets.testing.testcases import TestCase


class RateLimitUsageTests(TestCase):
    """Unit tests for RateLimitUsage.

    Version Added:
        5.3
    """

    def test_is_limited_without_limit(self) -> None:
        """Testing RateLimitUsage.is_limited with limit=None"""
        usage = RateLimitUsage(count=100000000000)

        self.assertIsNone(usage.limit)
        self.assertFalse(usage.is_limited)

    def test_is_limited_with_count_lte_limit(self) -> None:
        """Testing RateLimitUsage.is_limited with count <= limit"""
        usage = RateLimitUsage(count=100,
                               limit=100)

        self.assertFalse(usage.is_limited)

    def test_is_limited_with_count_gt_limit(self) -> None:
        """Testing RateLimitUsage.is_limited with count > limit"""
        usage = RateLimitUsage(count=101,
                               limit=100)

        self.assertTrue(usage.is_limited)


class RateLimitTests(TestCase):
    """Unit tests for RateLimit.

    Version Added:
        5.3
    """

    def test_parse_with_s(self) -> None:
        """Testing RateLimit.parse with /s"""
        self.assertEqual(RateLimit.parse('100/s'),
                         RateLimit(period_secs=1,
                                   total_limit=100))

    def test_parse_with_ns(self) -> None:
        """Testing RateLimit.parse with /Ns"""
        self.assertEqual(RateLimit.parse('100/10s'),
                         RateLimit(period_secs=10,
                                   total_limit=100))

    def test_parse_with_n(self) -> None:
        """Testing RateLimit.parse with /N"""
        self.assertEqual(RateLimit.parse('100/10'),
                         RateLimit(period_secs=10,
                                   total_limit=100))

    def test_parse_with_m(self) -> None:
        """Testing RateLimit.parse with /m"""
        self.assertEqual(RateLimit.parse('100/m'),
                         RateLimit(period_secs=60,
                                   total_limit=100))

    def test_parse_with_nm(self) -> None:
        """Testing RateLimit.parse with /Nm"""
        self.assertEqual(RateLimit.parse('100/10m'),
                         RateLimit(period_secs=600,
                                   total_limit=100))

    def test_parse_with_h(self) -> None:
        """Testing RateLimit.parse with /h"""
        self.assertEqual(RateLimit.parse('100/h'),
                         RateLimit(period_secs=3600,
                                   total_limit=100))

    def test_parse_with_nh(self) -> None:
        """Testing RateLimit.parse with /Nh"""
        self.assertEqual(RateLimit.parse('100/10h'),
                         RateLimit(period_secs=36000,
                                   total_limit=100))

    def test_parse_with_d(self) -> None:
        """Testing RateLimit.parse with /d"""
        self.assertEqual(RateLimit.parse('100/d'),
                         RateLimit(period_secs=86400,
                                   total_limit=100))

    def test_parse_with_nd(self) -> None:
        """Testing RateLimit.parse with /Nd"""
        self.assertEqual(RateLimit.parse('100/10d'),
                         RateLimit(period_secs=864000,
                                   total_limit=100))

    def test_parse_with_bad_string(self) -> None:
        """Testing RateLimit.parse with bad string"""
        message = 'Could not parse given rate limit: 100/f'

        with self.assertRaisesMessage(ValueError, message):
            RateLimit.parse('100/f')

    def test_get_reset_timestamp(self) -> None:
        """Testing RateLimit.get_reset_timestamp"""
        rate_limit = RateLimit(period_secs=60,
                               total_limit=100)

        self.assertEqual(rate_limit.get_reset_timestamp(60_000),
                         60_060)

    def test_get_reset_timestamp_with_period_secs_1(self) -> None:
        """Testing RateLimit.get_reset_timestamp"""
        rate_limit = RateLimit(period_secs=1,
                               total_limit=100)

        self.assertEqual(rate_limit.get_reset_timestamp(60_000),
                         60_000)


class CheckRateLimitTests(kgb.SpyAgency, TestCase):
    """Unit tests for check_rate_limit.

    Version Added:
        5.3
    """

    def setUp(self) -> None:
        """Set up state for a unit test.

        This will clear the cache.
        """
        super().setUp()

        cache.clear()

    def tearDown(self) -> None:
        """Tear down state for a unit test.

        This will clear the cache.
        """
        super().tearDown()

        cache.clear()

    def test_with_no_rate_limit(self) -> None:
        """Testing check_rate_limit with no rate limit"""
        self.assertEqual(check_rate_limit(rate_limit=None,
                                          key='test'),
                         RateLimitUsage(count=1))

    def test_with_str_rate_limit(self) -> None:
        """Testing check_rate_limit with rate limit string"""
        self.spy_on(_get_time_int, op=kgb.SpyOpReturn(1759962125))

        self.assertEqual(
            check_rate_limit(rate_limit='200/5m',
                             key='test'),
            RateLimitUsage(count=1,
                           limit=200,
                           time_left_secs=175))

        self.assertIsNone(
            cache.get('example.com:_ratelimit_:test:200/300:1759962300'))

        # Do it one more time, to verify counts aren't retained given
        # lack of cache updates.
        self.assertEqual(
            check_rate_limit(rate_limit='200/5m',
                             key='test'),
            RateLimitUsage(count=1,
                           limit=200,
                           time_left_secs=175))

    def test_with_parsed_rate_limit(self) -> None:
        """Testing check_rate_limit with parsed rate limit"""
        self.spy_on(_get_time_int, op=kgb.SpyOpReturn(1759962125))

        rate_limit = RateLimit(period_secs=300,
                               total_limit=200)

        self.assertEqual(
            check_rate_limit(rate_limit=rate_limit,
                             key='test'),
            RateLimitUsage(count=1,
                           limit=200,
                           time_left_secs=175))

        self.assertIsNone(
            cache.get('example.com:_ratelimit_:test:200/300:1759962300'))

        # Do it one more time, to verify counts aren't retained given
        # lack of cache updates.
        self.assertEqual(
            check_rate_limit(rate_limit=rate_limit,
                             key='test'),
            RateLimitUsage(count=1,
                           limit=200,
                           time_left_secs=175))

    def test_with_rate_limit_in_cache(self) -> None:
        """Testing check_rate_limit with rate limit in cache"""
        self.spy_on(_get_time_int, op=kgb.SpyOpReturn(1759962125))

        cache.set('example.com:_ratelimit_:test:200/300:1759962300', 10)

        rate_limit = RateLimit(period_secs=300,
                               total_limit=200)

        self.assertEqual(
            check_rate_limit(rate_limit=rate_limit,
                             key='test'),
            RateLimitUsage(count=11,
                           limit=200,
                           time_left_secs=175))

        self.assertEqual(
            cache.get('example.com:_ratelimit_:test:200/300:1759962300'),
            10)

        # Do it one more time, to verify counts aren't retained given
        # lack of cache updates.
        self.assertEqual(
            check_rate_limit(rate_limit=rate_limit,
                             key='test'),
            RateLimitUsage(count=11,
                           limit=200,
                           time_left_secs=175))

    def test_with_increment_count(self) -> None:
        """Testing check_rate_limit with increment_count=True"""
        self.spy_on(_get_time_int, op=kgb.SpyOpReturn(1759962125))

        rate_limit = RateLimit(period_secs=300,
                               total_limit=200)

        self.assertEqual(
            check_rate_limit(rate_limit=rate_limit,
                             key='test',
                             increment_count=True),
            RateLimitUsage(count=1,
                           limit=200,
                           time_left_secs=175))

        self.assertEqual(
            cache.get('example.com:_ratelimit_:test:200/300:1759962300'),
            1)

        # Do it one more time, to verify the counts increase beyond the
        # default.
        self.assertEqual(
            check_rate_limit(rate_limit=rate_limit,
                             key='test',
                             increment_count=True),
            RateLimitUsage(count=2,
                           limit=200,
                           time_left_secs=175))

        self.assertEqual(
            cache.get('example.com:_ratelimit_:test:200/300:1759962300'),
            2)

    def test_with_different_keys(self) -> None:
        """Testing check_rate_limit with different keys"""
        self.spy_on(_get_time_int, op=kgb.SpyOpReturn(1759962125))

        rate_limit = RateLimit(period_secs=300,
                               total_limit=200)

        self.assertEqual(
            check_rate_limit(rate_limit=rate_limit,
                             key='test',
                             increment_count=True),
            RateLimitUsage(count=1,
                           limit=200,
                           time_left_secs=175))

        self.assertEqual(
            cache.get('example.com:_ratelimit_:test:200/300:1759962300'),
            1)

        # Do it one more time, to verify the counts increase beyond the
        # default.
        self.assertEqual(
            check_rate_limit(rate_limit=rate_limit,
                             key=['other', 'test'],
                             increment_count=True),
            RateLimitUsage(count=1,
                           limit=200,
                           time_left_secs=175))

        self.assertEqual(
            cache.get('example.com:_ratelimit_:test:200/300:1759962300'),
            1)
        self.assertEqual(
            cache.get('example.com:_ratelimit_:other:test:200/300:1759962300'),
            1)
