from __future__ import unicode_literals

from django import forms
from django.contrib.sites.models import Site
from django.http import QueryDict

from djblets.conditions.values import (ConditionValueBooleanField,
                                       ConditionValueFormField,
                                       ConditionValueIntegerField)
from djblets.testing.testcases import TestCase


class ConditionValueFormFieldTests(TestCase):
    """Unit tests for djblets.conditions.values.ConditionValueFormField."""

    def test_serialize_value(self):
        """Testing ConditionValueFormField.serialize_value"""
        # ModelChoiceField uses prepare_value(), needed by serialize_value(),
        # so it's a good test.
        field = ConditionValueFormField(
            forms.ModelChoiceField(queryset=Site.objects.all()))

        site = Site.objects.get_current()
        self.assertEqual(field.serialize_value(site), site.pk)

    def test_deserialize_value(self):
        """Testing ConditionValueFormField.deserialize_value"""
        field = ConditionValueFormField(
            forms.ModelChoiceField(queryset=Site.objects.all()))

        site = Site.objects.get_current()
        self.assertEqual(field.deserialize_value(site.pk), site)

    def test_get_from_form_data(self):
        """Testing ConditionValueFormField.get_from_form_data"""
        field = ConditionValueFormField(forms.CharField())

        data = QueryDict('test-field=abc123')
        files = QueryDict('')

        self.assertEqual(field.get_from_form_data(data, files, 'test-field'),
                         'abc123')

    def test_render_html(self):
        """Testing ConditionValueFormField.render_html"""
        field = ConditionValueFormField(forms.CharField())

        self.assertEqual(field.render_html(),
                         '<input name="XXX" type="text" />')


class ConditionValueBooleanFieldTests(TestCase):
    """Unit tests for djblets.conditions.values.ConditionValueBooleanField."""

    def setUp(self):
        super(ConditionValueBooleanFieldTests, self).setUp()

        self.value_field = ConditionValueBooleanField()

    def test_deserialize_value_with_true(self):
        """Testing ConditionValueBooleanField.deserialize_value with True"""
        self.assertTrue(self.value_field.deserialize_value(True))
        self.assertTrue(self.value_field.deserialize_value('true'))
        self.assertTrue(self.value_field.deserialize_value('True'))
        self.assertTrue(self.value_field.deserialize_value('1'))

    def test_deserialize_value_with_false(self):
        """Testing ConditionValueBooleanField.deserialize_value with False"""
        self.assertFalse(self.value_field.deserialize_value(False))
        self.assertFalse(self.value_field.deserialize_value('false'))
        self.assertFalse(self.value_field.deserialize_value('False'))
        self.assertFalse(self.value_field.deserialize_value('0'))

    def test_prepare_value_for_widget(self):
        """Testing ConditionValueBooleanField.prepare_value_for_widget"""
        self.assertEqual(self.value_field.prepare_value_for_widget(True),
                         'True')
        self.assertEqual(self.value_field.prepare_value_for_widget(False),
                         'False')


class ConditionValueIntegerFieldTests(TestCase):
    """Unit tests for djblets.conditions.values.ConditionValueIntegerField."""

    def setUp(self):
        super(ConditionValueIntegerFieldTests, self).setUp()

        self.value_field = ConditionValueIntegerField()

    def test_deserialize_value(self):
        """Testing ConditionValueIntegerField.deserialize_value"""
        self.assertEqual(self.value_field.deserialize_value(100), 100)
        self.assertEqual(self.value_field.deserialize_value('100'), 100)
