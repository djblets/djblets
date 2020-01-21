# coding: utf-8
"""Unit tests for djblets.db.fields.base64_field."""

from __future__ import unicode_literals

from django.db import models
from django.utils import six

from djblets.db.fields.base64_field import (Base64DecodedValue, Base64Field,
                                            Base64TypeError)
from djblets.testing.testcases import TestCase, TestModelsLoaderMixin


class Base64TestModel(models.Model):
    field = Base64Field(null=True)


class Base64FieldTests(TestModelsLoaderMixin, TestCase):
    """Unit tests for djblets.db.fields.base64_field.Base64Field."""

    tests_app = 'djblets.db.tests'

    def test_create_with_decoded_bytes_value(self):
        """Testing Base64Field with setting decoded bytes value in
        Model.objects.create()
        """
        obj = Base64TestModel.objects.create(field=b'This is a test')

        self.assertIs(type(obj.field), Base64DecodedValue)
        self.assertEqual(obj.field, b'This is a test')

        encoded = obj.get_field_base64()
        self.assertIs(type(encoded), bytes)
        self.assertEqual(encoded, b'VGhpcyBpcyBhIHRlc3Q=\n')

    def test_create_with_decoded_unicode_value(self):
        """Testing Base64Field with setting decoded unicode value in
        Model.objects.create()
        """
        obj = Base64TestModel.objects.create(field='This is a tést')

        self.assertIs(type(obj.field), Base64DecodedValue)
        self.assertEqual(obj.field, b'This is a t\xc3\xa9st')

        encoded = obj.get_field_base64()
        self.assertIs(type(encoded), bytes)
        self.assertEqual(encoded, b'VGhpcyBpcyBhIHTDqXN0\n')

    def test_create_with_base64_decoded_value(self):
        """Testing Base64Field with setting Base64DecodedValue in
        Model.objects.create()
        """
        obj = Base64TestModel.objects.create(
            field=Base64DecodedValue(b'This is a test'))

        self.assertIs(type(obj.field), Base64DecodedValue)
        self.assertEqual(obj.field, b'This is a test')

        encoded = obj.get_field_base64()
        self.assertIs(type(encoded), bytes)
        self.assertEqual(encoded, b'VGhpcyBpcyBhIHRlc3Q=\n')

    def test_create_with_memoryview(self):
        """Testing Base64Field with setting memoryview in
        Model.objects.create()
        """
        obj = Base64TestModel.objects.create(
            field=six.memoryview(b'This is a t\xc3\xa9st'))

        self.assertIs(type(obj.field), Base64DecodedValue)
        self.assertEqual(obj.field, b'This is a t\xc3\xa9st')

        encoded = obj.get_field_base64()
        self.assertIs(type(encoded), bytes)
        self.assertEqual(encoded, b'VGhpcyBpcyBhIHTDqXN0\n')

    def test_create_with_none(self):
        """Testing Base64Field with setting None in
        Model.objects.create()
        """
        obj = Base64TestModel.objects.create(field=None)
        self.assertIsNone(obj.field)

        encoded = obj.get_field_base64()
        self.assertIsNone(encoded)

    def test_create_with_invalid_value_type(self):
        """Testing Base64Field with setting invalid value type in
        Model.objects.create()
        """
        with self.assertRaises(Base64TypeError):
            Base64TestModel.objects.create(field=True)

    def test_unsaved_obj_with_decoded_bytes_value(self):
        """Testing Base64Field with setting decoded bytes value on unsaved
        instance
        """
        obj = Base64TestModel()
        obj.field = b'This is a test'

        self.assertIs(type(obj.field), Base64DecodedValue)
        self.assertEqual(obj.field, b'This is a test')

        encoded = obj.get_field_base64()
        self.assertIs(type(encoded), bytes)
        self.assertEqual(encoded, b'VGhpcyBpcyBhIHRlc3Q=\n')

    def test_unsaved_obj_with_decoded_unicode_value(self):
        """Testing Base64Field with setting decoded unicode value on unsaved
        instance
        """
        obj = Base64TestModel()
        obj.field = 'This is a tést'

        self.assertIs(type(obj.field), Base64DecodedValue)
        self.assertEqual(obj.field, b'This is a t\xc3\xa9st')

        encoded = obj.get_field_base64()
        self.assertIs(type(encoded), bytes)
        self.assertEqual(encoded, b'VGhpcyBpcyBhIHTDqXN0\n')

    def test_unsaved_obj_with_base64_decoded_value(self):
        """Testing Base64Field with setting Base64DecodedValue on unsaved
        instance
        """
        obj = Base64TestModel()
        obj.field = Base64DecodedValue(b'This is a test')

        self.assertIs(type(obj.field), Base64DecodedValue)
        self.assertEqual(obj.field, b'This is a test')

        encoded = obj.get_field_base64()
        self.assertIs(type(encoded), bytes)
        self.assertEqual(encoded, b'VGhpcyBpcyBhIHRlc3Q=\n')

    def test_unsaved_obj_with_memoryview_value(self):
        """Testing Base64Field with setting memoryview on unsaved instance"""
        obj = Base64TestModel()
        obj.field = six.memoryview(b'This is a t\xc3\xa9st')

        self.assertIs(type(obj.field), Base64DecodedValue)
        self.assertEqual(obj.field, b'This is a t\xc3\xa9st')

        encoded = obj.get_field_base64()
        self.assertIs(type(encoded), bytes)
        self.assertEqual(encoded, b'VGhpcyBpcyBhIHTDqXN0\n')

    def test_unsaved_obj_with_invalid_value_type(self):
        """Testing Base64Field with setting invalid value type on unsaved
        instance
        """
        obj = Base64TestModel()

        with self.assertRaises(Base64TypeError):
            obj.field = True

    def test_unsaved_obj_with_none(self):
        """Testing Base64Field with setting None on unsaved instance"""
        obj = Base64TestModel()
        obj.field = None

        self.assertIsNone(obj.field)

        encoded = obj.get_field_base64()
        self.assertIsNone(encoded)

    def test_saved_obj_with_decoded_bytes_value(self):
        """Testing Base64Field with setting decoded bytes value on saved
        instance
        """
        obj = Base64TestModel.objects.create()
        obj.field = b'VGhpcyBpcyBhIHRlc3Q=\n'

        self.assertIs(type(obj.field), Base64DecodedValue)
        self.assertEqual(obj.field, b'This is a test')

        encoded = obj.get_field_base64()
        self.assertIs(type(encoded), bytes)
        self.assertEqual(encoded, b'VGhpcyBpcyBhIHRlc3Q=\n')

    def test_saved_obj_with_decoded_unicode_value(self):
        """Testing Base64Field with setting decoded unicode value on saved
        instance
        """
        obj = Base64TestModel.objects.create()
        obj.field = 'VGhpcyBpcyBhIHTDqXN0\n'

        self.assertIs(type(obj.field), Base64DecodedValue)
        self.assertEqual(obj.field, b'This is a t\xc3\xa9st')

        encoded = obj.get_field_base64()
        self.assertIs(type(encoded), bytes)
        self.assertEqual(encoded, b'VGhpcyBpcyBhIHTDqXN0\n')

    def test_saved_obj_with_base64_decoded_value(self):
        """Testing Base64Field with setting Base64DecodedValue on saved
        instance
        """
        obj = Base64TestModel.objects.create()
        obj.field = Base64DecodedValue(b'This is a test')

        self.assertIs(type(obj.field), Base64DecodedValue)
        self.assertEqual(obj.field, b'This is a test')

        encoded = obj.get_field_base64()
        self.assertIs(type(encoded), bytes)
        self.assertEqual(encoded, b'VGhpcyBpcyBhIHRlc3Q=\n')

    def test_saved_obj_with_memoryview_value(self):
        """Testing Base64Field with setting memoryview on saved instance"""
        obj = Base64TestModel.objects.create()
        obj.field = six.memoryview(b'VGhpcyBpcyBhIHTDqXN0\n')

        self.assertIs(type(obj.field), Base64DecodedValue)
        self.assertEqual(obj.field, b'This is a t\xc3\xa9st')

        encoded = obj.get_field_base64()
        self.assertIs(type(encoded), bytes)
        self.assertEqual(encoded, b'VGhpcyBpcyBhIHTDqXN0\n')

    def test_saved_obj_with_invalid_value_type(self):
        """Testing Base64Field with setting invalid value type on saved
        instance
        """
        obj = Base64TestModel.objects.create()

        with self.assertRaises(Base64TypeError):
            obj.field = True

    def test_saved_obj_with_none(self):
        """Testing Base64Field with setting None on saved instance"""
        obj = Base64TestModel.objects.create()
        obj.field = None

        self.assertIsNone(obj.field)

        encoded = obj.get_field_base64()
        self.assertIsNone(encoded)

    def test_values_persist_after_save(self):
        """Testing Base64Field value persists correctly after save"""
        obj = Base64TestModel.objects.create(field=b'This is a test')
        obj = Base64TestModel.objects.get(pk=obj.pk)

        self.assertIs(type(obj.field), Base64DecodedValue)
        self.assertEqual(obj.field, b'This is a test')

        encoded = obj.get_field_base64()
        self.assertIs(type(encoded), bytes)
        self.assertEqual(encoded, b'VGhpcyBpcyBhIHRlc3Q=\n')

    def test_save_form_data_with_bytes(self):
        """Testing Base64Field.save_form_data with bytes value"""
        obj = Base64TestModel(field=b'This is a test')
        obj._meta.get_field('field').save_form_data(obj, b'This is a test')

        self.assertIs(type(obj.field), Base64DecodedValue)
        self.assertEqual(obj.field, b'This is a test')

        encoded = obj.get_field_base64()
        self.assertIs(type(encoded), bytes)
        self.assertEqual(encoded, b'VGhpcyBpcyBhIHRlc3Q=\n')

    def test_save_form_data_with_unicode(self):
        """Testing Base64Field.save_form_data with unicode value"""
        obj = Base64TestModel(field=b'This is a test')
        obj._meta.get_field('field').save_form_data(obj, 'This is a tést')

        self.assertIs(type(obj.field), Base64DecodedValue)
        self.assertEqual(obj.field, b'This is a t\xc3\xa9st')

        encoded = obj.get_field_base64()
        self.assertIs(type(encoded), bytes)
        self.assertEqual(encoded, b'VGhpcyBpcyBhIHTDqXN0\n')

    def test_save_form_data_with_memoryview(self):
        """Testing Base64Field.save_form_data with memoryview value"""
        obj = Base64TestModel(field=b'This is a test')
        obj._meta.get_field('field').save_form_data(
            obj, six.memoryview(b'This is a t\xc3\xa9st'))

        self.assertIs(type(obj.field), Base64DecodedValue)
        self.assertEqual(obj.field, b'This is a t\xc3\xa9st')

        encoded = obj.get_field_base64()
        self.assertIs(type(encoded), bytes)
        self.assertEqual(encoded, b'VGhpcyBpcyBhIHTDqXN0\n')

    def test_to_python_with_bytes(self):
        """Testing Base64Field.to_python with bytes value"""
        obj = Base64TestModel()
        value = obj._meta.get_field('field').to_python(
            b'VGhpcyBpcyBhIHRlc3Q=\n')

        self.assertIs(type(value), Base64DecodedValue)
        self.assertEqual(value, b'This is a test')

    def test_to_python_with_unicode(self):
        """Testing Base64Field.to_python with unicode value"""
        obj = Base64TestModel()
        value = obj._meta.get_field('field').to_python(
            'VGhpcyBpcyBhIHRlc3Q=\n')

        self.assertIs(type(value), Base64DecodedValue)
        self.assertEqual(value, b'This is a test')

    def test_to_python_with_base64_decoded_value(self):
        """Testing Base64Field.to_python with Base64DecodedValue"""
        obj = Base64TestModel()
        value = obj._meta.get_field('field').to_python(
            Base64DecodedValue(b'This is a test'))

        self.assertIs(type(value), Base64DecodedValue)
        self.assertEqual(value, b'This is a test')

    def test_to_python_with_memoryview_value(self):
        """Testing Base64Field.to_python with memoryview value"""
        obj = Base64TestModel()
        value = obj._meta.get_field('field').to_python(
            six.memoryview(b'VGhpcyBpcyBhIHTDqXN0\n'))

        self.assertIs(type(value), Base64DecodedValue)
        self.assertEqual(value, b'This is a t\xc3\xa9st')

    def test_to_python_with_none(self):
        """Testing Base64Field.to_python with None"""
        obj = Base64TestModel()
        value = obj._meta.get_field('field').to_python(None)

        self.assertIsNone(value)

    def test_value_to_string_with_base64_decoded_value(self):
        """Testing Base64Field.value_to_string with Base64DecodedValue"""
        obj = Base64TestModel(field=b'This is a test')
        value = obj._meta.get_field('field').value_to_string(obj)

        self.assertIs(type(value), bytes)
        self.assertEqual(value, b'VGhpcyBpcyBhIHRlc3Q=\n')

    def test_value_to_string_with_none(self):
        """Testing Base64Field.value_to_string with None"""
        obj = Base64TestModel(field=None)
        value = obj._meta.get_field('field').value_to_string(obj)

        self.assertIsNone(value)
