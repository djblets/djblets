"""Unit tests for djblets.util.templatetags.djblets_forms."""

from __future__ import unicode_literals

from django import forms
from django.template import Context, Template

from djblets.testing.testcases import TestCase


class FormFieldHasLabelFirstTests(TestCase):
    """Unit tests for the ``{{...|form_field_has_label_first}}`` filter."""

    def test_with_checkbox_input(self):
        """Testing {{...|form_field_has_label_first}} with CheckboxInput"""
        class MyForm(forms.Form):
            my_field = forms.BooleanField()

        form = MyForm()
        t = Template('{% load djblets_forms %}'
                     '{% if field|form_field_has_label_first %}yep{% endif %}')

        self.assertEqual(
            t.render(Context({
                'field': form['my_field'],
            })),
            '')

    def test_with_other_widget(self):
        """Testing {{...|form_field_has_label_first}} with non-CheckboxInput
        widget
        """
        class MyForm(forms.Form):
            my_field = forms.CharField()

        form = MyForm()
        t = Template('{% load djblets_forms %}'
                     '{% if field|form_field_has_label_first %}yep{% endif %}')

        self.assertEqual(
            t.render(Context({
                'field': form['my_field'],
            })),
            'yep')


class FormFieldIDTests(TestCase):
    """Unit tests for the ``{{...|form_field_id}}`` template filter."""

    def test_with_id_from_field(self):
        """Testing {{...|form_field_id}} with ID from field"""
        class MyForm(forms.Form):
            my_field = forms.CharField(label='My field',
                                       required=True)

        form = MyForm()
        t = Template('{% load djblets_forms %}'
                     '{{field|form_field_id}}')

        self.assertEqual(
            t.render(Context({
                'field': form['my_field'],
            })),
            'id_my_field')

    def test_with_id_attr(self):
        """Testing {{...|form_field_id}} with ID from widget attribute"""
        class MyForm(forms.Form):
            my_field = forms.CharField(
                label='My field',
                required=True,
                widget=forms.TextInput(attrs={
                    'id': 'custom_id',
                }))

        form = MyForm()
        t = Template('{% load djblets_forms %}'
                     '{{field|form_field_id}}')

        self.assertEqual(
            t.render(Context({
                'field': form['my_field'],
            })),
            'custom_id')


class GetFieldsetsFilterTests(TestCase):
    """Unit tests for the ``{{...|get_fieldsets}}`` template filter."""

    def test_with_modern_fieldsets(self):
        """Testing {{...|get_fieldsets}} with modern fieldsets"""
        class MyForm(forms.Form):
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
        class MyForm(forms.Form):
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


class IsCheckboxRowTests(TestCase):
    """Unit tests for the ``{{...|is_checkbox_row}}}`` template filter."""

    def test_with_checkbox_input(self):
        """Testing {{...|is_checkbox_row}} with CheckboxInput widget"""
        class MyForm(forms.Form):
            my_field = forms.BooleanField(widget=forms.CheckboxInput())

        form = MyForm()
        t = Template('{% load djblets_forms %}'
                     '{% if field|is_checkbox_row %}yep{% endif %}')

        self.assertEqual(
            t.render(Context({
                'field': form['my_field'],
            })),
            'yep')

    def test_with_radio_select(self):
        """Testing {{...|is_checkbox_row}} with RadioSelect widget"""
        class MyForm(forms.Form):
            my_field = forms.ChoiceField(
                choices=((1, 'A'), (2, 'B')),
                widget=forms.RadioSelect())

        form = MyForm()
        t = Template('{% load djblets_forms %}'
                     '{% if field|is_checkbox_row %}yep{% endif %}')

        self.assertEqual(
            t.render(Context({
                'field': form['my_field'],
            })),
            'yep')

    def test_with_checkbox_select_multiple(self):
        """Testing {{...|is_checkbox_row}} with CheckboxSelectMultiple widget
        """
        class MyForm(forms.Form):
            my_field = forms.ChoiceField(
                choices=((1, 'A'), (2, 'B')),
                widget=forms.CheckboxSelectMultiple())

        form = MyForm()
        t = Template('{% load djblets_forms %}'
                     '{% if field|is_checkbox_row %}yep{% endif %}')

        self.assertEqual(
            t.render(Context({
                'field': form['my_field'],
            })),
            'yep')

    def test_with_other_widget(self):
        """Testing {{...|is_checkbox_row}} with non-checkbox-ish widget"""
        class MyForm(forms.Form):
            my_field = forms.ChoiceField(choices=((1, 'A'), (2, 'B')))

        form = MyForm()
        t = Template('{% load djblets_forms %}'
                     '{% if field|is_checkbox_row %}yep{% endif %}')

        self.assertEqual(
            t.render(Context({
                'field': form['my_field'],
            })),
            '')


class IsFieldCheckboxTests(TestCase):
    """Unit tests for the ``{{...|is_field_checkbox}}}`` template filter."""

    def test_with_checkbox_input(self):
        """Testing {{...|is_field_checkbox}} with CheckboxInput widget"""
        class MyForm(forms.Form):
            my_field = forms.BooleanField(widget=forms.CheckboxInput())

        form = MyForm()
        t = Template('{% load djblets_forms %}'
                     '{% if field|is_field_checkbox %}yep{% endif %}')

        self.assertEqual(
            t.render(Context({
                'field': form['my_field'],
            })),
            'yep')

    def test_with_non_checkbox_input(self):
        """Testing {{...|is_field_checkbox}} with non-CheckboxInput widget"""
        class MyForm(forms.Form):
            my_field = forms.BooleanField(widget=forms.TextInput())

        form = MyForm()
        t = Template('{% load djblets_forms %}'
                     '{% if field|is_field_checkbox %}yep{% endif %}')

        self.assertEqual(
            t.render(Context({
                'field': form['my_field'],
            })),
            '')


class LabelTagTests(TestCase):
    """Unit tests for the ``{% label_tag %}`` template tag."""

    def test_with_optional_field(self):
        """Testing {% label_tag %} with optional field"""
        class MyForm(forms.Form):
            my_field = forms.CharField(label='My field',
                                       required=False)

        form = MyForm()
        t = Template('{% load djblets_forms %}'
                     '{% label_tag field %}')

        self.assertHTMLEqual(
            t.render(Context({
                'field': form['my_field'],
            })),
            '<label for="id_my_field">My field:</label>')

    def test_with_required_field(self):
        """Testing {% label_tag %} with required field"""
        class MyForm(forms.Form):
            my_field = forms.CharField(label='My field',
                                       required=True)

        form = MyForm()
        t = Template('{% load djblets_forms %}'
                     '{% label_tag field %}')

        self.assertHTMLEqual(
            t.render(Context({
                'field': form['my_field'],
            })),
            '<label for="id_my_field" class="required">'
            'My field:</label>')

    def test_with_checkbox_field(self):
        """Testing {% label_tag %} with checkbox field"""
        class MyForm(forms.Form):
            my_checkbox = forms.BooleanField(label='My checkbox',
                                             required=False)

        form = MyForm()
        t = Template('{% load djblets_forms %}'
                     '{% label_tag field %}')

        self.assertHTMLEqual(
            t.render(Context({
                'field': form['my_checkbox'],
            })),
            '<label for="id_my_checkbox" class="vCheckboxLabel">'
            'My checkbox</label>')

    def test_with_empty_label(self):
        """Testing {% label_tag %} with empty label"""
        class MyForm(forms.Form):
            my_checkbox = forms.BooleanField(label='')

        form = MyForm()
        t = Template('{% load djblets_forms %}'
                     '{% label_tag field %}')

        self.assertEqual(
            t.render(Context({
                'field': form['my_checkbox'],
            })),
            '')
