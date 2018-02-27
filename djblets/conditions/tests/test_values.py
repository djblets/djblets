from __future__ import unicode_literals

import re

from django import forms
from django.contrib.sites.models import Site
from django.db.models.query import QuerySet
from django.http import QueryDict

from djblets.conditions.errors import InvalidConditionValueError
from djblets.conditions.values import (ConditionValueBooleanField,
                                       ConditionValueFormField,
                                       ConditionValueIntegerField,
                                       ConditionValueModelField,
                                       ConditionValueMultipleModelField,
                                       ConditionValueRegexField)
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

        self.assertHTMLEqual(field.render_html(),
                             '<input name="XXX" type="text" />')

    def test_field_with_callable(self):
        """Testing ConditionValueFormField.field with callable field"""
        field = ConditionValueFormField(lambda: forms.CharField())

        self.assertTrue(isinstance(field.field, forms.CharField))


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


class ConditionValueModelFieldTests(TestCase):
    """Unit tests for ConditionValueModelField."""

    def test_init_with_queryset(self):
        """Testing ConditionValueModelField initialization with QuerySet"""
        field = ConditionValueModelField(queryset=Site.objects.all())

        self.assertTrue(isinstance(field.field.queryset, QuerySet))

    def test_init_with_callable(self):
        """Testing ConditionValueModelField initialization with callable"""
        field = ConditionValueModelField(queryset=lambda: Site.objects.all())

        self.assertTrue(isinstance(field.field.queryset, QuerySet))

    def test_serialize_value(self):
        """Testing ConditionValueModelField.serialize_value"""
        field = ConditionValueModelField(queryset=Site.objects.all())

        site = Site.objects.get_current()
        self.assertEqual(field.serialize_value(site), site.pk)

    def test_deserialize_value(self):
        """Testing ConditionValueModelField.deserialize_value"""
        field = ConditionValueModelField(queryset=Site.objects.all())

        site = Site.objects.get_current()
        self.assertEqual(field.deserialize_value(site.pk), site)


class ConditionValueMultipleModelFieldTests(TestCase):
    """Unit tests for ConditionValueMultipleModelField."""

    def test_init_with_queryset(self):
        """Testing ConditionValueMultipleModelField initialization with
        QuerySet
        """
        field = ConditionValueMultipleModelField(queryset=Site.objects.all())

        self.assertTrue(isinstance(field.field.queryset, QuerySet))

    def test_init_with_callable(self):
        """Testing ConditionValueMultipleModelField initialization with
        callable
        """
        field = ConditionValueMultipleModelField(
            queryset=lambda: Site.objects.all())

        self.assertTrue(isinstance(field.field.queryset, QuerySet))

    def test_serialize_value(self):
        """Testing ConditionValueMultipleModelField.serialize_value"""
        field = ConditionValueMultipleModelField(queryset=Site.objects.all())

        site = Site.objects.get_current()
        self.assertEqual(field.serialize_value([site]), [site.pk])

    def test_deserialize_value(self):
        """Testing ConditionValueMultipleModelField.deserialize_value"""
        field = ConditionValueMultipleModelField(queryset=Site.objects.all())

        site = Site.objects.get_current()
        result = field.deserialize_value([site.pk])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], site)


class ConditionValueRegexFieldTests(TestCase):
    """Unit tests for djblets.conditions.values.ConditionValueRegexField."""

    def setUp(self):
        super(ConditionValueRegexFieldTests, self).setUp()

        self.value_field = ConditionValueRegexField()

    def test_deserialize_value(self):
        """Testing ConditionValueRegexField.deserialize_value"""
        regex_obj = self.value_field.deserialize_value('ab[^c]d+e?')

        # Weird, right? re.RegexObject, the documented result of a
        # re.compile(), does not exist. Instead, it's a _sre.SRE_Pattern,
        # but that's basically an internal detail we don't want to rely upon.
        # Internally, the re module actually does this type() mess to get
        # the type to use, so that's what we're doing!
        regex_type = type(re.compile(''))

        self.assertTrue(isinstance(regex_obj, regex_type))
        self.assertEqual(regex_obj.pattern, re.compile('ab[^c]d+e?').pattern)

    def test_deserialize_value_with_bad_pattern(self):
        """Testing ConditionValueRegexField.deserialize_value with bad
        pattern
        """
        with self.assertRaises(InvalidConditionValueError):
            self.value_field.deserialize_value('*')

    def test_serialize_value(self):
        """Testing ConditionValueRegexField.serialize_value"""
        regex_obj = re.compile('ab[^c]d+e?')

        self.assertEqual(
            self.value_field.serialize_value(regex_obj),
            'ab[^c]d+e?')
