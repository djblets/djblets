"""Unit tests for djblets.http.requests.

Version Added:
    5.3
"""

from __future__ import annotations

from django.test.client import RequestFactory

from djblets.http.requests import get_http_request_ip
from djblets.testing.testcases import TestCase


class GetHTTPRequestIPTests(TestCase):
    """Unit tests for get_http_request_ip.

    Version Added:
        5.3
    """

    def test_with_http_x_real_ip(self) -> None:
        """Testing get_http_request_ip with X-Real-IP header"""
        request = RequestFactory().get('/', headers={
            'X-Real-IP': '1.2.3.4',
        })

        self.assertEqual(get_http_request_ip(request), '1.2.3.4')

    def test_with_http_x_real_ip_ipv6(self) -> None:
        """Testing get_http_request_ip with X-Real-IP header with IPv6"""
        request = RequestFactory().get('/', headers={
            'X-Real-IP': '2001:db8:85a3:8d3:1319:8a2e:370:7348',
        })

        self.assertEqual(get_http_request_ip(request),
                         '2001:db8:85a3:8d3:1319:8a2e:370:7348')

    def test_with_http_x_forwarded_for(self) -> None:
        """Testing get_http_request_ip with X-Forwarded-For header"""
        request = RequestFactory().get('/', headers={
            'X-Forwarded-For': '1.2.3.4',
        })

        self.assertEqual(get_http_request_ip(request), '1.2.3.4')

    def test_with_http_x_forwarded_for_multi(self) -> None:
        """Testing get_http_request_ip with X-Forwarded-For header with
        multiple IPs
        """
        request = RequestFactory().get('/', headers={
            'X-Forwarded-For': '1.2.3.4, 4.5.5.67',
        })

        self.assertEqual(get_http_request_ip(request), '1.2.3.4')

    def test_with_http_x_forwarded_for_ipv6(self) -> None:
        """Testing get_http_request_ip with X-Forwarded-For header with IPv6
        """
        request = RequestFactory().get('/', headers={
            'X-Forwarded-For': '2001:db8:85a3:8d3:1319:8a2e:370:7348, 1.2.3.4',
        })

        self.assertEqual(get_http_request_ip(request),
                         '2001:db8:85a3:8d3:1319:8a2e:370:7348')

    def test_with__remote_addr(self) -> None:
        """Testing get_http_request_ip with REMOTE_ADDR"""
        request = RequestFactory().get('/',
                                       REMOTE_ADDR='1.2.3.4')

        self.assertEqual(get_http_request_ip(request), '1.2.3.4')

    def test_with__remote_addr_ipv6(self) -> None:
        """Testing get_http_request_ip with REMOTE_ADDR with IPv6"""
        request = RequestFactory().get(
            '/',
            REMOTE_ADDR='2001:db8:85a3:8d3:1319:8a2e:370:7348')

        self.assertEqual(get_http_request_ip(request),
                         '2001:db8:85a3:8d3:1319:8a2e:370:7348')
