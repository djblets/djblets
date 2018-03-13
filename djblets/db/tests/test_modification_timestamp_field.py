"""Unit tests for djblets.db.fields.modification_timestamp_field."""

from __future__ import unicode_literals

from datetime import datetime

from django.db import models

from djblets.db.fields.modification_timestamp_field import \
    ModificationTimestampField
from djblets.testing.testcases import TestCase, TestModelsLoaderMixin


class ModificationTimestampFieldTestModel(models.Model):
    field = ModificationTimestampField()


class ModificationTimestampFieldTests(TestModelsLoaderMixin, TestCase):
    """Unit tests for ModificationTimestampField."""

    tests_app = 'djblets.db.tests'

    def test_pre_save_with_new_instance_with_auto_value(self):
        """Testing ModificationTimestampField.pre_save with new model instance
        and auto-added value
        """
        obj = ModificationTimestampFieldTestModel()
        self.assertIsNone(obj.field)

        obj.save()
        self.assertIsNotNone(obj.field)

    def test_pre_save_with_new_instance_with_custom_value(self):
        """Testing ModificationTimestampField.pre_save with new model instance
        and custom value
        """
        timestamp = datetime(2018, 3, 6, 23, 31, 30)

        obj = ModificationTimestampFieldTestModel(field=timestamp)
        self.assertIsNotNone(obj.field)

        obj.save()
        self.assertIsNotNone(obj.field)
        self.assertEqual(obj.field, timestamp)

    def test_pre_save_with_existing_instance(self):
        """Testing ModificationTimestampField.pre_save with existing model
        instance
        """
        timestamp = datetime(2018, 3, 6, 23, 31, 30)

        obj = ModificationTimestampFieldTestModel.objects.create(
            field=timestamp)
        self.assertEqual(obj.field, timestamp)

        obj.save()
        self.assertNotEqual(obj.field, timestamp)
        self.assertTrue(obj.field > timestamp)

    def test_get_internal_type(self):
        """Testing ModificationTimestampField.get_internal_type"""
        obj = ModificationTimestampFieldTestModel()
        self.assertEqual(obj._meta.get_field('field').get_internal_type(),
                         'DateTimeField')
