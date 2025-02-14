"""Unit tests for djblets.conditions.values."""

from __future__ import annotations

import re
from typing import Any, Optional, Sequence

from django import forms
from django.contrib.sites.models import Site
from django.db.models.query import QuerySet
from django.http import QueryDict
from typing_extensions import assert_type

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

    def test_serialize_value(self) -> None:
        """Testing ConditionValueFormField.serialize_value"""
        # ModelChoiceField uses prepare_value(), needed by serialize_value(),
        # so it's a good test.
        field = ConditionValueFormField(
            forms.ModelChoiceField(queryset=Site.objects.all()))
        assert_type(field, ConditionValueFormField[Any])

        site = Site.objects.get_current()
        self.assertEqual(field.serialize_value(site), site.pk)

    def test_deserialize_value(self) -> None:
        """Testing ConditionValueFormField.deserialize_value"""
        field = ConditionValueFormField(
            forms.ModelChoiceField(queryset=Site.objects.all()))
        assert_type(field, ConditionValueFormField[Any])

        site = Site.objects.get_current()
        self.assertEqual(field.deserialize_value(site.pk), site)

    def test_get_from_form_data(self) -> None:
        """Testing ConditionValueFormField.get_from_form_data"""
        field = ConditionValueFormField[str](forms.CharField())

        data = QueryDict('test-field=abc123')
        files = QueryDict('')

        value = field.get_from_form_data(data, files, 'test-field')

        assert_type(value, Optional[str])
        self.assertEqual(value, 'abc123')

    def test_render_html(self) -> None:
        """Testing ConditionValueFormField.render_html"""
        field = ConditionValueFormField[str](forms.CharField())

        self.assertHTMLEqual(field.render_html(),
                             '<input name="XXX" type="text" />')

    def test_field_with_callable(self) -> None:
        """Testing ConditionValueFormField.field with callable field"""
        field = ConditionValueFormField[str](lambda: forms.CharField())

        self.assertIsInstance(field.field, forms.CharField)


class ConditionValueBooleanFieldTests(TestCase):
    """Unit tests for djblets.conditions.values.ConditionValueBooleanField."""

    def test_deserialize_value_with_true(self) -> None:
        """Testing ConditionValueBooleanField.deserialize_value with True"""
        value_field = ConditionValueBooleanField()

        value = value_field.deserialize_value(True)
        assert_type(value, bool)
        self.assertTrue(value)

        value = value_field.deserialize_value('true')
        assert_type(value, bool)
        self.assertTrue(value)

        value = value_field.deserialize_value('True')
        assert_type(value, bool)
        self.assertTrue(value)

        value = value_field.deserialize_value('1')
        assert_type(value, bool)
        self.assertTrue(value)

    def test_deserialize_value_with_false(self) -> None:
        """Testing ConditionValueBooleanField.deserialize_value with False"""
        value_field = ConditionValueBooleanField()

        value = value_field.deserialize_value(False)
        assert_type(value, bool)
        self.assertFalse(value)

        value = value_field.deserialize_value('false')
        assert_type(value, bool)
        self.assertFalse(value)

        value = value_field.deserialize_value('False')
        assert_type(value, bool)
        self.assertFalse(value)

        value = value_field.deserialize_value('0')
        assert_type(value, bool)
        self.assertFalse(value)

    def test_serialize_value(self) -> None:
        """Testing ConditionValueBooleanField.serialize_value"""
        value_field = ConditionValueBooleanField()

        self.assertIs(value_field.serialize_value(True), True)
        self.assertIs(value_field.serialize_value(False), False)

    def test_prepare_value_for_widget(self) -> None:
        """Testing ConditionValueBooleanField.prepare_value_for_widget"""
        value_field = ConditionValueBooleanField()

        self.assertEqual(value_field.prepare_value_for_widget(True), 'True')
        self.assertEqual(value_field.prepare_value_for_widget(False), 'False')


class ConditionValueIntegerFieldTests(TestCase):
    """Unit tests for djblets.conditions.values.ConditionValueIntegerField."""

    def test_deserialize_value(self) -> None:
        """Testing ConditionValueIntegerField.deserialize_value"""
        value_field = ConditionValueIntegerField()

        value = value_field.deserialize_value(100)
        assert_type(value, int)
        self.assertEqual(value, 100)

        value = value_field.deserialize_value('100')
        assert_type(value, int)
        self.assertEqual(value, 100)

    def test_serialize_value(self) -> None:
        """Testing ConditionValueIntegerField.serialize_value"""
        value_field = ConditionValueIntegerField()

        self.assertEqual(value_field.serialize_value(100), 100)


class ConditionValueModelFieldTests(TestCase):
    """Unit tests for ConditionValueModelField."""

    def test_init_with_queryset(self) -> None:
        """Testing ConditionValueModelField initialization with QuerySet"""
        field = ConditionValueModelField[Site](queryset=Site.objects.all())

        form_field = field.field
        assert isinstance(form_field, forms.ModelChoiceField)

        self.assertIsInstance(form_field.queryset, QuerySet)

    def test_init_with_callable(self) -> None:
        """Testing ConditionValueModelField initialization with callable"""
        field = ConditionValueModelField[Site](
            queryset=lambda: Site.objects.all())

        form_field = field.field
        assert isinstance(form_field, forms.ModelChoiceField)

        self.assertIsInstance(form_field.queryset, QuerySet)

    def test_serialize_value(self) -> None:
        """Testing ConditionValueModelField.serialize_value"""
        field = ConditionValueModelField[Site](queryset=Site.objects.all())

        site = Site.objects.get_current()
        self.assertEqual(field.serialize_value(site), site.pk)

    def test_deserialize_value(self) -> None:
        """Testing ConditionValueModelField.deserialize_value"""
        field = ConditionValueModelField[Site](queryset=Site.objects.all())
        site = Site.objects.get_current()

        value = field.deserialize_value(site.pk)
        assert_type(value, Site)

        self.assertEqual(value, site)


class ConditionValueMultipleModelFieldTests(TestCase):
    """Unit tests for ConditionValueMultipleModelField."""

    def test_init_with_queryset(self) -> None:
        """Testing ConditionValueMultipleModelField initialization with
        QuerySet
        """
        field = ConditionValueMultipleModelField[Site](
            queryset=Site.objects.all())

        form_field = field.field
        assert isinstance(form_field, forms.ModelMultipleChoiceField)

        self.assertIsInstance(form_field.queryset, QuerySet)

    def test_init_with_callable(self) -> None:
        """Testing ConditionValueMultipleModelField initialization with
        callable
        """
        field = ConditionValueMultipleModelField[Site](
            queryset=lambda: Site.objects.all())

        form_field = field.field
        assert isinstance(form_field, forms.ModelMultipleChoiceField)

        self.assertIsInstance(form_field.queryset, QuerySet)

    def test_serialize_value(self) -> None:
        """Testing ConditionValueMultipleModelField.serialize_value"""
        field = ConditionValueMultipleModelField[Site](
            queryset=Site.objects.all())

        site = Site.objects.get_current()
        self.assertEqual(field.serialize_value([site]), [site.pk])

    def test_deserialize_value(self) -> None:
        """Testing ConditionValueMultipleModelField.deserialize_value"""
        field = ConditionValueMultipleModelField[Site](
            queryset=Site.objects.all())

        site = Site.objects.get_current()
        result = field.deserialize_value([site.pk])

        assert_type(result, Sequence[Site])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], site)


class ConditionValueRegexFieldTests(TestCase):
    """Unit tests for djblets.conditions.values.ConditionValueRegexField."""

    def setUp(self) -> None:
        super(ConditionValueRegexFieldTests, self).setUp()

        self.value_field = ConditionValueRegexField()

    def test_deserialize_value(self) -> None:
        """Testing ConditionValueRegexField.deserialize_value"""
        regex_obj = self.value_field.deserialize_value('ab[^c]d+e?')

        assert_type(regex_obj, re.Pattern)
        self.assertIsInstance(regex_obj, re.Pattern)
        self.assertEqual(regex_obj.pattern, re.compile('ab[^c]d+e?').pattern)

    def test_deserialize_value_with_bad_pattern(self) -> None:
        """Testing ConditionValueRegexField.deserialize_value with bad
        pattern
        """
        with self.assertRaises(InvalidConditionValueError):
            self.value_field.deserialize_value('*')

    def test_serialize_value(self) -> None:
        """Testing ConditionValueRegexField.serialize_value"""
        regex_obj = re.compile('ab[^c]d+e?')

        self.assertEqual(
            self.value_field.serialize_value(regex_obj),
            'ab[^c]d+e?')
