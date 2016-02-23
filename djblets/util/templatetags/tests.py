from __future__ import unicode_literals

from django.forms import Form
from django.http import HttpRequest
from django.template import Context, Template
from pipeline.conf import settings as pipeline_settings

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
                     '{% include_as_string template_name %}')

        self.assertEqual(
            t.render(Context({
                'template_name': 'testing/foo.html',
                'foo': 1,
                'bar': 2,
            })),
            "'1 2\\\n'")

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

        self.assertEqual(
            t.render(Context({
                'template_name': 'testing/foo.html',
                'foo': 'baz',
                'bar': 'qux',
            })),
            '> baz qux\n'
            '>')


class FormsTests(TestCase):
    """Unit tests for the djblets_forms template tags."""

    def test_get_fieldsets_modern(self):
        """Testing the get_fieldsets template filter with modern fieldsets"""
        class MyForm(Form):
            class Meta:
                fieldsets = (
                    ('Test 1', {
                        'description': 'This is test 1',
                        'fields': ('field_1', 'field_2'),
                    }),
                    (None, {
                        'description': 'This is test 2',
                        'fields': ('field_3', 'field_4'),
                    }),
                )

        t = Template(
            '{% load djblets_forms %}'
            '{% for title, fieldset in form|get_fieldsets %}'
            'Title: {{title}}\n'
            'Description: {{fieldset.description}}\n'
            'Fields: {{fieldset.fields|join:","}}\n'
            '{% endfor %}'
        )

        self.assertEqual(
            t.render(Context({
                'form': MyForm(),
            })),
            'Title: Test 1\n'
            'Description: This is test 1\n'
            'Fields: field_1,field_2\n'
            'Title: None\n'
            'Description: This is test 2\n'
            'Fields: field_3,field_4\n')

    def test_get_fieldsets_legacy(self):
        """Testing the get_fieldsets template filter with legacy fieldsets"""
        class MyForm(Form):
            class Meta:
                fieldsets = (
                    {
                        'title': 'Test 1',
                        'description': 'This is test 1',
                        'fields': ('field_1', 'field_2'),
                    },
                    {
                        'description': 'This is test 2',
                        'fields': ('field_3', 'field_4'),
                    }
                )

        t = Template(
            '{% load djblets_forms %}'
            '{% for title, fieldset in form|get_fieldsets %}'
            'Title: {{title}}\n'
            'Description: {{fieldset.description}}\n'
            'Fields: {{fieldset.fields|join:","}}\n'
            '{% endfor %}'
        )

        self.assertEqual(
            t.render(Context({
                'form': MyForm(),
            })),
            'Title: Test 1\n'
            'Description: This is test 1\n'
            'Fields: field_1,field_2\n'
            'Title: None\n'
            'Description: This is test 2\n'
            'Fields: field_3,field_4\n')


class CompressedTagTests(TestCase):
    """Tests for compressed template tags."""

    def test_compressed_css_tag(self):
        """Testing compressed_css template tag"""
        pipeline_settings.STYLESHEETS = {
            'test': {
                'source_filenames': [],
                'output_filename': 'test.css',
            }
        }

        t = Template('{% load compressed %}'
                     '{% compressed_css "test" %}')

        self.assertEqual(t.render(Context({'test': 'test'})),
                         '/test.css\n')

    def test_compressed_js_tag(self):
        """Testing compressed_js template tag"""
        pipeline_settings.JAVASCRIPT = {
            'test': {
                'source_filenames': [],
                'output_filename': 'test.js',
            }
        }

        t = Template('{% load compressed %}'
                     '{% compressed_js "test" %}')

        self.assertEqual(t.render(Context({'test': 'test'})),
                         '/test.js\n')
