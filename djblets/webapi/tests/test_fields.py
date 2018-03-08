"""Unit tests for djblets.webapi.fields."""

from __future__ import unicode_literals

from datetime import datetime

import pytz
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.utils import six, timezone
from kgb import SpyAgency

from djblets.testing.testcases import TestCase
from djblets.webapi.fields import (BooleanFieldType,
                                   ChoiceFieldType,
                                   DateTimeFieldType,
                                   DictFieldType,
                                   FileFieldType,
                                   IntFieldType,
                                   ListFieldType,
                                   ResourceFieldType,
                                   ResourceListFieldType,
                                   StringFieldType)
from djblets.webapi.resources.user import UserResource, user_resource


class BooleanFieldTypeTests(TestCase):
    """Unit tests for djblets.webapi.fields.BooleanFieldType."""

    def setUp(self):
        super(BooleanFieldTypeTests, self).setUp()

        self.field_type = BooleanFieldType({})

    def test_get_value_from_data(self):
        """Testing BooleanFieldType.get_value_from_data"""
        value = self.field_type.get_value_from_data(
            name='var',
            fields_data={
                'var': True,
            },
            files_data={
                'var': False,
            })
        self.assertTrue(value)

    def test_clean_value_with_truthy_values(self):
        """Testing BooleanFieldType.clean_value with truthy values"""
        self.assertTrue(self.field_type.clean_value(True))
        self.assertTrue(self.field_type.clean_value(1))
        self.assertTrue(self.field_type.clean_value('1'))
        self.assertTrue(self.field_type.clean_value('true'))
        self.assertTrue(self.field_type.clean_value('True'))
        self.assertTrue(self.field_type.clean_value('TRUE'))

    def test_clean_value_with_falsy_values(self):
        """Testing BooleanFieldType.clean_value with falsy values"""
        self.assertFalse(self.field_type.clean_value(False))
        self.assertFalse(self.field_type.clean_value(0))
        self.assertFalse(self.field_type.clean_value(''))
        self.assertFalse(self.field_type.clean_value('false'))
        self.assertFalse(self.field_type.clean_value('False'))
        self.assertFalse(self.field_type.clean_value('FALSE'))

    def test_str(self):
        """Testing BooleanFieldType.__str__"""
        self.assertEqual(six.text_type(self.field_type), 'Boolean')


class ChoiceFieldTypeTests(TestCase):
    """Unit tests for djblets.webapi.fields.ChoiceFieldType."""

    def setUp(self):
        super(ChoiceFieldTypeTests, self).setUp()

        self.field_type = ChoiceFieldType({
            'choices': ['a', 'b', 'cde'],
        })

    def test_init_without_choices(self):
        """Testing ChoiceFieldType.__init__ without choices key"""
        expected_message = 'Missing "choices" key in {}'

        with self.assertRaisesMessage(KeyError, expected_message):
            ChoiceFieldType({})

    def test_get_value_from_data(self):
        """Testing ChoiceFieldType.get_value_from_data"""
        value = self.field_type.get_value_from_data(
            name='var',
            fields_data={
                'var': 'b',
            },
            files_data={
                'var': 'cde',
            })
        self.assertEqual(value, 'b')

    def test_clean_value_with_valid_values(self):
        """Testing ChoiceFieldType.clean_value with valid values"""
        self.assertEqual(self.field_type.clean_value('a'), 'a')
        self.assertEqual(self.field_type.clean_value('b'), 'b')
        self.assertEqual(self.field_type.clean_value('cde'), 'cde')

    def test_clean_value_with_invalid_values(self):
        """Testing ChoiceFieldType.clean_value with invalid values"""
        expected_message = \
            '"c" is not a valid value. Valid values are: "a", "b", "cde"'

        with self.assertRaisesMessage(ValidationError, expected_message):
            self.field_type.clean_value('c')

    def test_str(self):
        """Testing ChoiceFieldType.__str__"""
        self.assertEqual(six.text_type(self.field_type),
                         'One of "a", "b", "cde"')


class DateTimeFieldTypeTests(SpyAgency, TestCase):
    """Unit tests for djblets.webapi.fields.DateTimeFieldType."""

    def setUp(self):
        super(DateTimeFieldTypeTests, self).setUp()

        self.field_type = DateTimeFieldType({})

    def test_get_value_from_data(self):
        """Testing DateTimeFieldType.get_value_from_data"""
        value = self.field_type.get_value_from_data(
            name='var',
            fields_data={
                'var': '2018-02-20T13:42:00',
            },
            files_data={
                'var': None,
            })
        self.assertEqual(value, '2018-02-20T13:42:00')

    def test_clean_value_with_aware_datetime(self):
        """Testing DateTimeFieldType.clean_value with aware datetime"""
        dt = datetime(2018, 2, 20, 13, 42, 0, tzinfo=timezone.utc)

        self.assertEqual(self.field_type.clean_value(dt),
                         dt)

    def test_clean_value_with_naive_datetime(self):
        """Testing DateTimeFieldType.clean_value with naive datetime"""
        dt = datetime(2018, 2, 20, 13, 42, 0)
        self.assertTrue(timezone.is_naive(dt))

        pst = pytz.timezone('US/Pacific')

        with timezone.override(pst):
            self.assertEqual(self.field_type.clean_value(dt),
                             pst.localize(dt))

    def test_clean_value_with_timestamp_string_utc(self):
        """Testing DateTimeFieldType.clean_value with timestamp string with
        UTC offset
        """
        self.assertEqual(
            self.field_type.clean_value('2018-02-20T13:42:00Z'),
            datetime(2018, 2, 20, 13, 42, 0, tzinfo=timezone.utc))

    def test_clean_value_with_timestamp_string_no_timezone(self):
        """Testing DateTimeFieldType.clean_value with timestamp string without
        timezone offset
        """
        pst = pytz.timezone('US/Pacific')

        with timezone.override(pst):
            self.assertEqual(
                self.field_type.clean_value('2018-02-20T13:42:00'),
                pst.localize(datetime(2018, 2, 20, 13, 42, 0)))

    def test_clean_value_with_timestamp_string_ambiguous(self):
        """Testing DateTimeFieldType.clean_value with timestamp string with
        ambiguous time
        """
        with timezone.override(pytz.timezone('America/Chicago')):
            expected_message = (
                'This timestamp needs a UTC offset to avoid being ambiguous '
                'due to daylight savings time changes'
            )

            with self.assertRaisesMessage(ValidationError, expected_message):
                self.field_type.clean_value('2016-11-06T01:05:59')

    def test_clean_value_with_invalid_timestamp(self):
        """Testing DateTimeFieldType.clean_value with invalid timestamp string
        """
        expected_message = 'This timestamp is not a valid ISO 8601 date/time'

        with self.assertRaisesMessage(ValidationError, expected_message):
            self.field_type.clean_value('2016-112')

    def test_str(self):
        """Testing DateTimeFieldType.__str__"""
        self.assertEqual(six.text_type(self.field_type),
                         'ISO 8601 Date/Time')


class DictFieldTypeTests(TestCase):
    """Unit tests for djblets.webapi.fields.DictFieldType."""

    def setUp(self):
        super(DictFieldTypeTests, self).setUp()

        self.field_type = DictFieldType({})

    def test_get_value_from_data(self):
        """Testing DictFieldType.get_value_from_data"""
        value = self.field_type.get_value_from_data(
            name='var',
            fields_data={
                'var': '{"a": true}',
            },
            files_data={
                'var': None,
            })
        self.assertEqual(value, '{"a": true}')

    def test_clean_value_with_dict(self):
        """Testing DictFieldType.clean_value with dict value"""
        self.assertEqual(
            self.field_type.clean_value({
                'a': True,
                'b': False,
            }),
            {
                'a': True,
                'b': False,
            })

    def test_clean_value_with_dict_json(self):
        """Testing DictFieldType.clean_value with JSON dict value"""
        self.assertEqual(
            self.field_type.clean_value('{"a": true, "b": false}'),
            {
                'a': True,
                'b': False,
            })

    def test_clean_value_with_non_dict(self):
        """Testing DictFieldType.clean_value with non-dict value"""
        expected_message = 'This value is not a valid dictionary value'

        with self.assertRaisesMessage(ValidationError, expected_message):
            self.field_type.clean_value([1, 2, 3])

    def test_clean_value_with_non_dict_json(self):
        """Testing DictFieldType.clean_value with JSON non-dict value"""
        expected_message = 'This value is not a valid dictionary value'

        with self.assertRaisesMessage(ValidationError, expected_message):
            self.field_type.clean_value('[1, 2, 3]')

    def test_clean_value_with_invalid_json(self):
        """Testing DictFieldType.clean_value with invalid JSON value"""
        expected_message = 'This value is not a valid JSON document'

        with self.assertRaisesMessage(ValidationError, expected_message):
            self.field_type.clean_value('{"a": 1')

    def test_str(self):
        """Testing DictFieldType.__str__"""
        self.assertEqual(six.text_type(self.field_type), 'Dictionary')


class FileFieldTypeTests(TestCase):
    """Unit tests for djblets.webapi.fields.FileFieldType."""

    def setUp(self):
        super(FileFieldTypeTests, self).setUp()

        self.field_type = FileFieldType({})

    def test_get_value_from_data(self):
        """Testing FileFieldType.get_value_from_data"""
        value = self.field_type.get_value_from_data(
            name='var',
            fields_data={
                'var': 'field',
            },
            files_data={
                'var': 'file',
            })
        self.assertEqual(value, 'file')

    def test_clean_value(self):
        """Testing FileFieldType.clean_value"""
        uploaded_file = UploadedFile()
        self.assertEqual(self.field_type.clean_value(uploaded_file),
                         uploaded_file)

    def test_str(self):
        """Testing FileFieldType.__str__"""
        self.assertEqual(six.text_type(self.field_type), 'Uploaded file')


class IntFieldTypeTests(TestCase):
    """Unit tests for djblets.webapi.fields.IntFieldType."""

    def setUp(self):
        super(IntFieldTypeTests, self).setUp()

        self.field_type = IntFieldType({})

    def test_get_value_from_data(self):
        """Testing IntFieldType.get_value_from_data"""
        value = self.field_type.get_value_from_data(
            name='var',
            fields_data={
                'var': '10',
            },
            files_data={
                'var': '20',
            })
        self.assertEqual(value, '10')

    def test_clean_value_with_valid_values(self):
        """Testing IntFieldType.clean_value with valid values"""
        self.assertEqual(self.field_type.clean_value(100), 100)
        self.assertEqual(self.field_type.clean_value('100'), 100)

    def test_clean_value_with_invalid_values(self):
        """Testing IntFieldType.clean_value with invalid values"""
        expected_message = '"c" is not an integer'

        with self.assertRaisesMessage(ValidationError, expected_message):
            self.field_type.clean_value('c')

    def test_str(self):
        """Testing IntFieldType.__str__"""
        self.assertEqual(six.text_type(self.field_type), 'Integer')


class ListFieldTypeTests(TestCase):
    """Unit tests for djblets.webapi.fields.ListFieldType."""

    def setUp(self):
        super(ListFieldTypeTests, self).setUp()

        self.field_type = ListFieldType({})

    def test_get_value_from_data(self):
        """Testing ListFieldType.get_value_from_data"""
        value = self.field_type.get_value_from_data(
            name='var',
            fields_data={
                'var': '[1, 2, 3]',
            },
            files_data={
                'var': None,
            })
        self.assertEqual(value, '[1, 2, 3]')

    def test_clean_value_with_list(self):
        """Testing ListFieldType.clean_value with list value"""
        self.assertEqual(self.field_type.clean_value([1, 2, 3]),
                         [1, 2, 3])

    def test_clean_value_with_list_json(self):
        """Testing ListFieldType.clean_value with JSON list value"""
        self.assertEqual(self.field_type.clean_value('[1, 2, 3]'),
                         [1, 2, 3])

    def test_clean_value_with_list_and_item_type_and_valid_item(self):
        """Testing ListFieldType.clean_value with list value and item type with
        valid items
        """
        field_type = ListFieldType({
            'items': {
                'type': BooleanFieldType,
            },
        })
        self.assertEqual(field_type.clean_value(['1', 'true', False]),
                         [True, True, False])

    def test_clean_value_with_list_and_item_type_and_invalid_item(self):
        """Testing ListFieldType.clean_value with list value and item type with
        invalid item
        """
        field_type = ListFieldType({
            'items': {
                'type': ChoiceFieldType,
                'choices': ['a', 'b'],
            },
        })

        expected_message = \
            '"c" is not a valid value. Valid values are: "a", "b"'

        with self.assertRaisesMessage(ValidationError, expected_message):
            field_type.clean_value(['a', 'b', 'c'])

    def test_clean_value_with_non_list(self):
        """Testing ListFieldType.clean_value with non-list value"""
        expected_message = 'This value is not a valid list'

        with self.assertRaisesMessage(ValidationError, expected_message):
            self.field_type.clean_value(None)

    def test_clean_value_with_non_list_json(self):
        """Testing ListFieldType.clean_value with non-list value"""
        expected_message = 'This value is not a valid list'

        with self.assertRaisesMessage(ValidationError, expected_message):
            self.field_type.clean_value('{}')

    def test_clean_value_with_invalid_json(self):
        """Testing ListFieldType.clean_value with invalid JSON value"""
        expected_message = 'This value is not a valid JSON document'

        with self.assertRaisesMessage(ValidationError, expected_message):
            self.field_type.clean_value('[1, 2, 3')

    def test_str(self):
        """Testing ListFieldType.__str__"""
        self.assertEqual(six.text_type(self.field_type), 'List')

    def test_str_with_item_type(self):
        """Testing ListFieldType.__str__ with item type"""
        field_type = ListFieldType({
            'items': {
                'type': ChoiceFieldType,
                'choices': ['a', 'b'],
            },
        })

        self.assertEqual(six.text_type(field_type), 'List of One of "a", "b"')


class ResourceFieldTypeTests(TestCase):
    """Unit tests for djblets.webapi.fields.ResourceFieldType."""

    def setUp(self):
        super(ResourceFieldTypeTests, self).setUp()

        self.field_type = ResourceFieldType({
            'resource': user_resource,
        })

    def test_init_without_resource(self):
        """Testing ResourceFieldType.__init__ without resource key"""
        expected_message = 'Missing "resource" key in {}'

        with self.assertRaisesMessage(KeyError, expected_message):
            ResourceFieldType({})

    def test_init_with_resource_instance(self):
        """Testing ResourceFieldType.__init__ with resource instance"""
        self.assertEqual(self.field_type.resource, user_resource)

    def test_init_with_resource_class(self):
        """Testing ResourceFieldType.__init__ with resource class"""
        field_type = ResourceFieldType({
            'resource': UserResource,
        })
        self.assertEqual(field_type.resource, UserResource)

    def test_init_with_resource_instance_path_string(self):
        """Testing ResourceFieldType.__init__ with resource instance path
        string
        """
        field_type = ResourceFieldType({
            'resource': 'djblets.webapi.resources.user.user_resource',
        })
        self.assertEqual(field_type.resource, user_resource)

    def test_init_with_resource_class_path_string(self):
        """Testing ResourceFieldType.__init__ with resource class path string
        """
        field_type = ResourceFieldType({
            'resource': 'djblets.webapi.resources.user.UserResource',
        })
        self.assertEqual(field_type.resource, UserResource)

    def test_init_with_resource_path_string_and_missing(self):
        """Testing ResourceFieldType.__init__ with resource path string and
        resource not found
        """
        # Note that we're not checking the entirety of the string here,
        # since Python 2 and 3 differ in how they represent the module that
        # failed to import.
        expected_error = (
            'Unable to load resource "foo.bar.my_resource": No module '
            'named'
        )

        with self.assertRaisesMessage(ImportError, expected_error):
            ResourceFieldType({
                'resource': 'foo.bar.my_resource',
            })

    def test_get_value_from_data(self):
        """Testing ResourceFieldType.get_value_from_data"""
        value = self.field_type.get_value_from_data(
            name='var',
            fields_data={
                'var': 'abc',
            },
            files_data={
                'var': 'def',
            })
        self.assertEqual(value, 'abc')

    def test_clean_value(self):
        """Testing ResourceFieldType.clean_value not supported"""
        expected_message = \
            'ResourceFieldType cannot be used for request data'

        with self.assertRaisesMessage(NotImplementedError, expected_message):
            self.field_type.clean_value('abc')

    def test_str(self):
        """Testing ResourceFieldType.__str__"""
        self.assertEqual(six.text_type(self.field_type), 'UserResource')


class ResourceListFieldTypeTests(TestCase):
    """Unit tests for djblets.webapi.fields.ResourceListFieldType."""

    def setUp(self):
        super(ResourceListFieldTypeTests, self).setUp()

        self.field_type = ResourceListFieldType({
            'resource': user_resource,
        })

    def test_init_without_resource(self):
        """Testing ResourceListFieldType.__init__ without resource key"""
        expected_message = 'Missing "resource" key in {}'

        with self.assertRaisesMessage(KeyError, expected_message):
            ResourceListFieldType({})

    def test_init_with_resource_instance(self):
        """Testing ResourceListFieldType.__init__ with resource instance"""
        self.assertEqual(self.field_type.resource, user_resource)

    def test_init_with_resource_path_string(self):
        """Testing ResourceListFieldType.__init__ with resource path string"""
        field_type = ResourceListFieldType({
            'resource': 'djblets.webapi.resources.user.user_resource',
        })
        self.assertEqual(field_type.resource, user_resource)

    def test_init_with_resource_path_string_and_missing(self):
        """Testing ResourceListFieldType.__init__ with resource path string and
        resource not found
        """
        # Note that we're not checking the entirety of the string here,
        # since Python 2 and 3 differ in how they represent the module that
        # failed to import.
        expected_error = (
            'Unable to load resource "foo.bar.my_resource": No module '
            'named'
        )

        with self.assertRaisesMessage(ImportError, expected_error):
            ResourceListFieldType({
                'resource': 'foo.bar.my_resource',
            })

    def test_get_value_from_data(self):
        """Testing ResourceListFieldType.get_value_from_data"""
        value = self.field_type.get_value_from_data(
            name='var',
            fields_data={
                'var': 'abc',
            },
            files_data={
                'var': 'def',
            })
        self.assertEqual(value, 'abc')

    def test_clean_value(self):
        """Testing ResourceListFieldType.clean_value not supported"""
        expected_message = \
            'ResourceListFieldType cannot be used for request data'

        with self.assertRaisesMessage(NotImplementedError, expected_message):
            self.field_type.clean_value('abc')

    def test_str(self):
        """Testing ResourceListFieldType.__str__"""
        self.assertEqual(six.text_type(self.field_type),
                         'List of UserResource')


class StringFieldTypeTests(TestCase):
    """Unit tests for djblets.webapi.fields.StringFieldType."""

    def setUp(self):
        super(StringFieldTypeTests, self).setUp()

        self.field_type = StringFieldType({})

    def test_get_value_from_data(self):
        """Testing StringFieldType.get_value_from_data"""
        value = self.field_type.get_value_from_data(
            name='var',
            fields_data={
                'var': 'abc',
            },
            files_data={
                'var': 'def',
            })
        self.assertEqual(value, 'abc')

    def test_clean_value_with_valid_values(self):
        """Testing StringFieldType.clean_value with valid values"""
        self.assertEqual(self.field_type.clean_value('abc'), 'abc')
        self.assertEqual(self.field_type.clean_value(True), 'True')
        self.assertEqual(self.field_type.clean_value(100), '100')

    def test_str(self):
        """Testing StringFieldType.__str__"""
        self.assertEqual(six.text_type(self.field_type), 'String')
