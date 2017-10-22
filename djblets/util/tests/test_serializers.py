"""Unit tests for djblets.util.serializers."""

from __future__ import unicode_literals

from datetime import datetime

from djblets.testing.testcases import TestCase
from djblets.util.serializers import DjbletsJSONEncoder


class DjbletsJSONEncoderTests(TestCase):
    """Unit tests for djblets.util.serializers.DjbletsJSONEncoder."""

    def test_object_to_json(self):
        """Testing DjbletsJSONEncoder.encode for an object with a to_json()
        method
        """
        class TestObject(object):
            def to_json(self):
                return {
                    'foo': 1,
                }

        obj = TestObject()
        encoder = DjbletsJSONEncoder()

        self.assertEqual(encoder.encode(obj), '{"foo": 1}')

    def test_datetime(self):
        """Testing DjbletsJSONENcoder.encode with datetimes"""
        encoder = DjbletsJSONEncoder()
        self.assertEqual(
            encoder.encode(datetime(2016, 8, 26, 3, 3, 26, 123456)),
            '"2016-08-26T03:03:26"')

    def test_datetime_with_strip_ms(self):
        """Testing DjbletsJSONENcoder.encode with datetimes when using
        strip_datetime_ms=False
        """
        encoder = DjbletsJSONEncoder(strip_datetime_ms=False)
        self.assertEqual(
            encoder.encode(datetime(2016, 8, 26, 3, 3, 26, 123456)),
            '"2016-08-26T03:03:26.123"')
