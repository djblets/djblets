from __future__ import unicode_literals

from django.forms import Form
from django.template import Context, Template

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
