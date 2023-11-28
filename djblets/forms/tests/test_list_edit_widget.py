"""Unit tests for djblets.forms.widgets.ListEditWidget."""

from django import forms
from django.utils.datastructures import MultiValueDict

from djblets.forms.fields import ListEditField
from djblets.forms.widgets import ListEditWidget
from djblets.testing.testcases import TestCase


class ListEditWidgetTests(TestCase):
    """Unit tests for djblets.forms.widgets.ListEditWidget."""

    def test_render(self):
        """Testing ListEditWidget.render with a list of values"""
        field = forms.CharField(widget=ListEditWidget())
        rendered = field.widget.render(
            name='my_field',
            value=['foo', 'bar', 'baz'],
            attrs={
                'id': 'id_my_field',
                'class': 'my-value-class',
            })

        self.assertIn(
            '<div class="djblets-c-list-edit-widget list-edit-widget"'
            ' id="id_my_field_container">',
            rendered)
        self.assertIn('<input type="text"'
                      ' name="my_field_value[0]"'
                      ' value="foo"'
                      ' class="my-value-class'
                      ' djblets-c-list-edit-widget__input"'
                      ' id="id_my_field_value_0">',
                      rendered)
        self.assertIn('<input type="text"'
                      ' name="my_field_value[1]"'
                      ' value="bar"'
                      ' class="my-value-class'
                      ' djblets-c-list-edit-widget__input"'
                      ' id="id_my_field_value_1">',
                      rendered)
        self.assertIn('<input type="text"'
                      ' name="my_field_value[2]"'
                      ' value="baz"'
                      ' class="my-value-class'
                      ' djblets-c-list-edit-widget__input"'
                      ' id="id_my_field_value_2">',
                      rendered)

    def test_render_with_custom_value_widget(self):
        """Testing ListEditWidget.render with using a custom value widget"""
        field = ListEditField(
            widget=ListEditWidget(value_widget=forms.widgets.EmailInput))
        rendered = field.widget.render(
            name='my_field',
            value=['a@test.com', 'b@test.com'],
            attrs={
                'id': 'id_my_field',
                'class': 'my-value-class',
            })

        self.assertIn(
            '<div class="djblets-c-list-edit-widget list-edit-widget"'
            ' id="id_my_field_container">',
            rendered)
        self.assertIn('<input type="email"'
                      ' name="my_field_value[0]"'
                      ' value="a@test.com"'
                      ' class="my-value-class'
                      ' djblets-c-list-edit-widget__input"'
                      ' id="id_my_field_value_0">',
                      rendered)
        self.assertIn('<input type="email"'
                      ' name="my_field_value[1]"'
                      ' value="b@test.com"'
                      ' class="my-value-class'
                      ' djblets-c-list-edit-widget__input"'
                      ' id="id_my_field_value_1">',
                      rendered)

    def test_value_from_datadict(self):
        """Testing ListEditWidget.value_from_datadict"""
        field = ListEditField(widget=ListEditWidget())
        data = MultiValueDict('')
        data.update({
            'my_field_value[0]': 'a@test.com',
            'my_field_value[1]': 'b@test.com',
            'my_field_num_rows': '2',
        })

        self.assertEqual(
            field.widget.value_from_datadict(data, MultiValueDict(''),
                                             'my_field'),
            ['a@test.com', 'b@test.com'])

    def test_value_from_datadict_using_field_name(self):
        """Testing ListEditWidget.value_from_datadict when only the field
        name is given in the data dict"""
        field = ListEditField(widget=ListEditWidget())
        data = MultiValueDict('')
        data.update({
            'my_field': ['a@test.com', 'b@test.com']
        })

        self.assertEqual(
            field.widget.value_from_datadict(data, MultiValueDict(''),
                                             'my_field'),
            ['a@test.com', 'b@test.com'])

    def test_get_context(self):
        """Testing ListEditWidget.get_context"""
        field = ListEditField(widget=ListEditWidget())
        result = field.widget.get_context(
            'my_field',
            ['foo', 'bar'],
            {
                'id': 'id_my_field',
                'class': 'my-value-class'
            })

        self.assertEqual(
            set(result),
            {
                'name', 'id', 'remove_text', 'rendered_rows',
                'rendered_empty_row', 'rendered_initial_row',
            })
        self.assertEqual(result['name'], 'my_field')
        self.assertEqual(result['id'], 'id_my_field')

        rendered_rows = result['rendered_rows']
        self.assertEqual(len(rendered_rows), 2)
        self.assertHTMLEqual(
            rendered_rows[0],
            '<input type="text"'
            ' name="my_field_value[0]"'
            ' value="foo"'
            ' class="my-value-class'
            ' djblets-c-list-edit-widget__input"'
            ' id="id_my_field_value_0" />')
        self.assertHTMLEqual(
            rendered_rows[1],
            '<input type="text"'
            ' name="my_field_value[1]"'
            ' value="bar"'
            ' class="my-value-class'
            ' djblets-c-list-edit-widget__input"'
            ' id="id_my_field_value_1" />')
        self.assertHTMLEqual(
            result['rendered_empty_row'],
            '<input type="text"'
            ' name="my_field_value[__EDIT_LIST_ROW_INDEX__]"'
            ' class="my-value-class'
            ' djblets-c-list-edit-widget__input"'
            ' id="id_my_field_value___EDIT_LIST_ROW_ID__" />')
