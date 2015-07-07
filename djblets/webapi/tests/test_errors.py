from __future__ import unicode_literals

from djblets.testing.testcases import TestCase
from djblets.webapi.errors import WebAPIError


class WebAPIErrorTests(TestCase):
    """Unit tests for djblets.webapi.errors."""

    def test_with_message(self):
        """Testing WebAPIError.with_message"""
        orig_msg = 'Original message'
        new_msg = 'New message'
        headers = {
            'foo': 'bar',
        }

        orig_error = WebAPIError(123, orig_msg, http_status=500,
                                 headers=headers)
        new_error = orig_error.with_message(new_msg)

        self.assertNotEqual(orig_error, new_error)
        self.assertEqual(new_error.msg, new_msg)
        self.assertEqual(new_error.headers, headers)
        self.assertEqual(new_error.code, orig_error.code)
        self.assertEqual(new_error.http_status, orig_error.http_status)
        self.assertEqual(orig_error.msg, orig_msg)
        self.assertEqual(orig_error.headers, headers)

    def test_with_overrides(self):
        """Testing WebAPIError.with_overrides"""
        orig_msg = 'Original message'
        new_msg = 'New message'
        orig_headers = {
            'foo': 'bar',
        }
        new_headers = {
            'abc': '123',
        }

        orig_error = WebAPIError(123, orig_msg, http_status=500,
                                 headers=orig_headers)
        new_error = orig_error.with_overrides(new_msg, headers=new_headers)

        self.assertNotEqual(orig_error, new_error)
        self.assertEqual(new_error.msg, new_msg)
        self.assertEqual(new_error.headers, new_headers)
        self.assertEqual(new_error.code, orig_error.code)
        self.assertEqual(new_error.http_status, orig_error.http_status)
        self.assertEqual(orig_error.msg, orig_msg)
        self.assertEqual(orig_error.headers, orig_headers)
