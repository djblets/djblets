"""Unit tests for djblets.util.templatetags.djblets_forms."""

from __future__ import unicode_literals

from django.forms import Form
from django.template import Context, Template

from djblets.testing.testcases import TestCase


class GetFieldsetsFilterTests(TestCase):
    """Unit tests for the {{...|get_fieldsets}} template filter."""

    def test_with_modern_fieldsets(self):
        """Testing {{...|get_fieldsets}} with modern fieldsets"""
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

    def test_with_legacy_fieldets(self):
        """Testing {{...|get_fieldsets}} with legacy fieldsets"""
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
