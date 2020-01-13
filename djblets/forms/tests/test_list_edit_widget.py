"""Unit tests for djblets.forms.widgets.ListEditWidget."""

from __future__ import unicode_literals

from django import forms

from djblets.forms.widgets import ListEditWidget
from djblets.testing.testcases import TestCase


class ListEditWidgetTests(TestCase):
    """Unit tests for djblets.forms.widgets.ListEditWidget."""

    def test_render(self):
        """Testing ListEditWidget.render"""
        field = forms.CharField(widget=ListEditWidget())
        rendered = field.widget.render(
            name='my_field',
            value=' foo,  bar , baz ',
            attrs={
                'id': 'id_my_field',
                'class': 'my-value-class',
            })

        self.assertIn(
            '<div class="djblets-c-list-edit-widget list-edit-widget"'
            ' id="id_my_field_container">',
            rendered)
        self.assertIn('<input value="foo" type="text"'
                      ' class="my-value-class'
                      ' djblets-c-list-edit-widget__input">',
                      rendered)
        self.assertIn('<input value="bar" type="text"'
                      ' class="my-value-class'
                      ' djblets-c-list-edit-widget__input">',
                      rendered)
        self.assertIn('<input value="baz" type="text"'
                      ' class="my-value-class'
                      ' djblets-c-list-edit-widget__input">',
                      rendered)

    def test_render_with_custom_separator(self):
        """Testing ListEditWidget.render with custom separator"""
        field = forms.CharField(widget=ListEditWidget(sep=';'))
        rendered = field.widget.render(
            name='my_field',
            value=' foo;  bar ; baz ',
            attrs={
                'id': 'id_my_field',
                'class': 'my-value-class',
            })

        self.assertIn(
            '<div class="djblets-c-list-edit-widget list-edit-widget"'
            ' id="id_my_field_container">',
            rendered)
        self.assertIn('<input value="foo" type="text"'
                      ' class="my-value-class'
                      ' djblets-c-list-edit-widget__input">',
                      rendered)
        self.assertIn('<input value="bar" type="text"'
                      ' class="my-value-class'
                      ' djblets-c-list-edit-widget__input">',
                      rendered)
        self.assertIn('<input value="baz" type="text"'
                      ' class="my-value-class'
                      ' djblets-c-list-edit-widget__input">',
                      rendered)
