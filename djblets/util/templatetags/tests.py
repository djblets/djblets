from __future__ import unicode_literals

from django.http import HttpRequest
from django.template import Context, Template

from djblets.template.loaders.memory import MemoryTemplateLoader
from djblets.template.loaders.util import add_template_loader
from djblets.testing.testcases import TestCase
from djblets.util.templatetags.djblets_js import json_dumps


class JSTagTests(TestCase):
    """Unit tests for djblets_js template tags."""

    def test_json_dumps_xss(self):
        """Testing json_dumps doesn't allow XSS injection"""
        # This is bug 3406.
        obj = {
            'xss': '</script><script>alert(1);</script>'
        }

        self.assertEqual(
            json_dumps(obj),
            '{"xss": "\\u003C/script\\u003E\\u003Cscript\\u003E'
            'alert(1);\\u003C/script\\u003E"}')


class UtilsTagTests(TestCase):
    """Tests for djblets_utils template tags."""

    def test_include_as_string_tag(self):
        """Testing include_as_string template tag"""

        t = Template('{% load djblets_utils %}'
                     '{% include_as_string "foo" %}')

        loader = MemoryTemplateLoader({
            'foo': 'var={{var}}',
        })

        with add_template_loader(loader):
            self.assertEqual(
                t.render(Context({
                    'var': 1
                })),
                "'var=1'")

    def test_querystring_with_tag(self):
        """Testing querystring_with template tag"""
        t = Template('{% load djblets_utils %}'
                     '{% querystring_with "foo" "bar" %}')

        self.assertEqual(
            t.render(Context({
                'request': HttpRequest()
            })),
            '?foo=bar')

    def test_querystring_with_tag_existing_query(self):
        """Testing querystring_with template tag with an existing query"""
        t = Template('{% load djblets_utils %}'
                     '{% querystring_with "foo" "bar" %}')

        request = HttpRequest()
        request.GET = {
            'bar': 'baz',
        }

        self.assertEqual(
            t.render(Context({
                'request': request
            })),
            '?bar=baz&foo=bar')

    def test_querystring_with_existing_query_override(self):
        """Testing querystring_with template tag with an existing query that
        gets overriden
        """
        t = Template('{% load djblets_utils %}'
                     '{% querystring_with "foo" "bar" %}')

        request = HttpRequest()
        request.GET = {
            'foo': 'foo',
            'bar': 'baz',
        }

        self.assertEqual(
            t.render(Context({
                'request': request
            })),
            '?bar=baz&foo=bar')


class EmailTagTests(TestCase):
    """Tests for djblets_email template tags."""

    def test_quoted_email_tag(self):
        """Testing quoted_email template tag"""
        t = Template('{% load djblets_email %}'
                     '{% quoted_email template_name %}')

        loader = MemoryTemplateLoader({
            'foo': '{{foo}} {{bar}}',
        })

        with add_template_loader(loader):
            self.assertEqual(
                t.render(Context({
                    'template_name': 'foo',
                    'foo': 'baz',
                    'bar': 'qux',
                })),
                '> baz qux')
