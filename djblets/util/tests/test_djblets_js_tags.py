"""Unit tests for djblets.util.templatetags.djblets_js."""

from __future__ import unicode_literals

from djblets.testing.testcases import TestCase
from djblets.util.templatetags.djblets_js import json_dumps


class JSONDumpsFilterTests(TestCase):
    """Unit tests for the {{...|json_dumps}} template filter."""

    def test_prevents_xss(self):
        """Testing {{...|json_dumps}} doesn't allow XSS injection"""
        # This is bug 3406.
        obj = {
            'xss': '</script><script>alert(1);</script>'
        }

        self.assertEqual(
            json_dumps(obj),
            '{"xss": "\\u003C/script\\u003E\\u003Cscript\\u003E'
            'alert(1);\\u003C/script\\u003E"}')

    def test_sorted_keys(self):
        """Testing {{...|json_dumps}} sorts dictionary keys"""
        self.assertEqual(
            json_dumps({
                'a': 1,
                'b': 2,
                'z': 3,
                '0': 4,
            }),
            '{"0": 4, "a": 1, "b": 2, "z": 3}')
