"""Unit tests for djblets.db.fields.comma_separated_values_field."""

from __future__ import annotations

from django.db import models

from djblets.db.fields import CommaSeparatedValuesField
from djblets.testing.testcases import TestCase, TestModelsLoaderMixin


class TestModel(models.Model):
    """Test model for the CommaSeparatedValuesField."""

    field = CommaSeparatedValuesField(
        max_length=512,
        blank=True)


class CommaSeparatedValuesFieldTests(TestModelsLoaderMixin, TestCase):
    """Tests for djblets.db.fields.comma_separated_values_field."""

    tests_app = 'djblets.db.tests'

    def test_empty_field(self) -> None:
        """Testing CommaSeparatedValuesField with empty initial value."""
        obj = TestModel()
        self.assertEqual(obj.field, [])

    def test_set_value(self) -> None:
        """Testing CommaSeparatedValuesField with setting value"""
        obj = TestModel()

        obj.field = ['a', 'b', 'c']
        obj.save()

        obj.refresh_from_db()
        self.assertEqual(obj.field, ['a', 'b', 'c'])
