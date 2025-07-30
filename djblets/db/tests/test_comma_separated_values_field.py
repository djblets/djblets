"""Unit tests for djblets.db.fields.comma_separated_values_field."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models

from djblets.db.fields import CommaSeparatedValuesField
from djblets.testing.testcases import TestCase, TestModelsLoaderMixin


class _TestModel(models.Model):
    """Test model for the CommaSeparatedValuesField."""

    field = CommaSeparatedValuesField(
        max_length=512,
        blank=True)

    choices_field = CommaSeparatedValuesField(
        choices=[
            ('a', 'Item A'),
            ('b', 'Item B'),
            ('c', 'Item C'),
        ],
        max_length=512,
        blank=True)


class CommaSeparatedValuesFieldTests(TestModelsLoaderMixin, TestCase):
    """Tests for djblets.db.fields.comma_separated_values_field."""

    tests_app = 'djblets.db.tests'

    def test_empty_field(self) -> None:
        """Testing CommaSeparatedValuesField with empty initial value."""
        obj = _TestModel()
        self.assertEqual(obj.field, [])

    def test_set_value(self) -> None:
        """Testing CommaSeparatedValuesField with setting value"""
        obj = _TestModel()

        obj.field = ['a', 'b', 'c']
        obj.save()

        obj.refresh_from_db()
        self.assertEqual(obj.field, ['a', 'b', 'c'])

    def test_get_list(self) -> None:
        """Testing CommaSeparatedValuesField.get_<fieldname>_list"""
        obj = _TestModel()
        obj.field = ['a', 'b', 'c', 'c']

        self.assertEqual(obj.get_field_list(), ['a', 'b', 'c', 'c'])

    def test_get_list_with_choices(self) -> None:
        """Testing CommaSeparatedValuesField.get_<fieldname>_list with
        choices
        """
        obj = _TestModel()
        obj.choices_field = ['a', 'b', 'c', 'c', 'z']

        self.assertEqual(obj.get_choices_field_list(), [
            'Item A',
            'Item B',
            'Item C',
            'Item C',
            'z',
        ])

    def test_get_display(self) -> None:
        """Testing CommaSeparatedValuesField.get_<fieldname>_list"""
        obj = _TestModel()
        obj.field = ['a', 'b', 'c', 'c']

        self.assertEqual(obj.get_field_display(), 'a, b, c, c')

    def test_get_display_with_choices(self) -> None:
        """Testing CommaSeparatedValuesField.get_<fieldname>_list with
        choices
        """
        obj = _TestModel()
        obj.choices_field = ['a', 'b', 'c', 'c', 'z']

        self.assertEqual(obj.get_choices_field_display(),
                         'Item A, Item B, Item C, Item C, z')

    def test_validate(self) -> None:
        """Testing CommaSeparatedValuesField.validate"""
        obj = _TestModel()

        obj.field = ['a', 'b', 'c', 'd']
        obj.choices_field = ['a', 'b']

        obj.full_clean()

        message = '''{'choices_field': ["Value 'z' is not a valid choice."]}'''

        with self.assertRaisesMessage(ValidationError, message):
            obj.choices_field = ['a', 'b', 'z']
            obj.full_clean()
