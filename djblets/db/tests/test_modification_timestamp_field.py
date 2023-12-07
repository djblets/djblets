"""Unit tests for djblets.db.fields.modification_timestamp_field."""

from __future__ import annotations

import datetime

import kgb
from django.db import models
from django.utils import timezone

from djblets.db.fields.modification_timestamp_field import \
    ModificationTimestampField
from djblets.testing.testcases import TestCase, TestModelsLoaderMixin


class ModificationTimestampFieldTestModel(models.Model):
    field = ModificationTimestampField()


class MultitipleModificationTimestampFieldTestModel(models.Model):
    timestamp1 = ModificationTimestampField('timestamp1')
    timestamp2 = ModificationTimestampField('timestamp2')


class ModificationTimestampFieldTests(kgb.SpyAgency, TestModelsLoaderMixin,
                                      TestCase):
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
        timestamp = datetime.datetime(2018, 3, 6, 23, 31, 30,
                                      tzinfo=datetime.timezone.utc)

        obj = ModificationTimestampFieldTestModel(field=timestamp)
        self.assertIsNotNone(obj.field)

        obj.save()
        self.assertIsNotNone(obj.field)
        self.assertEqual(obj.field, timestamp)

    def test_pre_save_with_existing_instance(self):
        """Testing ModificationTimestampField.pre_save with existing model
        instance
        """
        timestamp = datetime.datetime(2018, 3, 6, 23, 31, 30,
                                      tzinfo=datetime.timezone.utc)

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

    def test_save_updates_value_with_tz(self):
        """Testing ModificationTimestampField updates the value on save when
        USE_TZ=True
        """
        with self.settings(USE_TZ=True):
            original_timestamp = timestamp = timezone.now()
            self.spy_on(timezone.now, call_fake=lambda: timestamp)

            instance = ModificationTimestampFieldTestModel.objects.create()
            self.assertEqual(instance.field, timestamp)

            timestamp += datetime.timedelta(hours=1)
            instance.save()
            self.assertEqual(instance.field, timestamp)
            self.assertNotEqual(instance.field, original_timestamp)

    def test_save_updates_value_without_tz(self):
        """Testing ModificationTimestampField udpates the value on save when
        USE_TZ=False
        """
        with self.settings(USE_TZ=False):
            original_timestamp = timestamp = timezone.now()
            self.spy_on(timezone.now, call_fake=lambda: timestamp)

            instance = ModificationTimestampFieldTestModel.objects.create()
            self.assertEqual(instance.field, timestamp)

            timestamp += datetime.timedelta(hours=1)
            instance.save()
            self.assertEqual(instance.field, timestamp)
            self.assertNotEqual(instance.field, original_timestamp)

    def test_save_doesnt_overwrite_modified_value_with_tz(self):
        """Testing ModificationTimestampField doesn't overwite manual setting
        of the field when USE_TZ=False
        """
        with self.settings(USE_TZ=True):
            timestamp = timezone.now()
            self.spy_on(timezone.now, call_fake=lambda: timestamp)

            instance = ModificationTimestampFieldTestModel.objects.create()
            instance.field += datetime.timedelta(hours=1)
            instance.save()

            # Make sure the manually set value won't be overwritten.
            self.assertNotEqual(instance.field, timestamp)
            self.assertEqual(instance.field,
                             timestamp + datetime.timedelta(hours=1))

            timestamp += datetime.timedelta(days=1)
            instance.save()

            # Make sure the old manually set value can be overwritten later.
            self.assertEqual(instance.field, timestamp)

    def test_save_doesnt_overwite_modified_value_without_tz(self):
        """Testing ModificationTimestampField doesn't overwite manual setting
        of the field when USE_TZ=False
        """
        with self.settings(USE_TZ=False):
            timestamp = timezone.now()
            self.spy_on(timezone.now, call_fake=lambda: timestamp)

            instance = ModificationTimestampFieldTestModel.objects.create()
            instance.field += datetime.timedelta(hours=1)
            instance.save()

            self.assertNotEqual(instance.field, timestamp)
            self.assertEqual(instance.field,
                             timestamp + datetime.timedelta(hours=1))

            timestamp += datetime.timedelta(days=1)
            instance.save()

            # Make sure the old manually set value can be overwritten later.
            self.assertEqual(instance.field, timestamp)

    def test_save_multiple_with_tz(self):
        """Testing multiple ModificationTimestampField save correctly when
        USE_TZ=True
        """
        with self.settings(USE_TZ=True):
            timestamp = timezone.now()
            self.spy_on(timezone.now, call_fake=lambda: timestamp)

            manual_value = timestamp + datetime.timedelta(hours=4)

            instance = MultitipleModificationTimestampFieldTestModel()
            instance.timestamp1 = manual_value
            instance.save()

            self.assertEqual(instance.timestamp1, manual_value)
            self.assertEqual(instance.timestamp2, timestamp)

            timestamp += datetime.timedelta(hours=1)

            instance.timestamp2 = manual_value
            instance.save()

            self.assertEqual(instance.timestamp1, timestamp)
            self.assertEqual(instance.timestamp2, manual_value)

    def test_save_multiple_without_tz(self):
        """Testing multiple ModificationTimestampField save correctly when
        USE_TZ=False
        """
        with self.settings(USE_TZ=False):
            timestamp = timezone.now()
            self.spy_on(timezone.now, call_fake=lambda: timestamp)

            manual_value = timestamp + datetime.timedelta(hours=4)

            instance = MultitipleModificationTimestampFieldTestModel()
            instance.timestamp1 = manual_value
            instance.save()

            self.assertEqual(instance.timestamp1, manual_value)
            self.assertEqual(instance.timestamp2, timestamp)

            timestamp += datetime.timedelta(hours=1)

            instance.timestamp2 = manual_value
            instance.save()

            self.assertEqual(instance.timestamp1, timestamp)
            self.assertEqual(instance.timestamp2, manual_value)

    def test_save_with_object_from_manager(self) -> None:
        """Testing ModificationTimestampField automatically updates when
        saving a model instance fetched from a model manager
        """
        timestamp = timezone.now()
        self.spy_on(timezone.now, call_fake=lambda: timestamp)

        instance = ModificationTimestampFieldTestModel.objects.create()

        self.assertEqual(instance.field, timestamp)

        fetched = ModificationTimestampFieldTestModel.objects.get(
            pk=instance.pk)
        timestamp += datetime.timedelta(hours=1)
        fetched.save()

        self.assertEqual(fetched.field, timestamp)

    def test_save_with_object_from_manager_doesnt_overwrite(self) -> None:
        """Testing ModificationTimestampField doesn't overwrite manually set
        values when saving a model instance fetched from a model manager
        """
        timestamp = timezone.now()
        self.spy_on(timezone.now, call_fake=lambda: timestamp)

        instance = ModificationTimestampFieldTestModel.objects.create()

        self.assertEqual(instance.field, timestamp)

        fetched = ModificationTimestampFieldTestModel.objects.get(
            pk=instance.pk)
        fetched.field += datetime.timedelta(hours=1)
        fetched.save()

        self.assertEqual(fetched.field,
                         timestamp + datetime.timedelta(hours=1))

        timestamp += datetime.timedelta(days=1)
        fetched.save()

        # Make sure the old manually set value can be overwritten later.
        self.assertEqual(fetched.field, timestamp)
