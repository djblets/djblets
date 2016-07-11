from __future__ import unicode_literals

from django import forms
from django.contrib.sites.models import Site
from django.http import QueryDict

from djblets.conditions.values import ConditionValueFormField
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
