from __future__ import unicode_literals

import json
import warnings

from django.core.exceptions import ValidationError
from django.db.models import Model
from django.utils import six

from djblets.db.fields import JSONField, JSONFormField
from djblets.testing.testcases import TestCase


class JSONFieldTests(TestCase):
    """Unit tests for JSONField."""

    def setUp(self):
        self.field = JSONField()

    def test_init_with_custom_encoder_class(self):
        """Testing JSONField initialization with custom encoder class"""
        class MyEncoder(json.JSONEncoder):
            def __init__(self, default_msg, **kwargs):
                self.default_msg = default_msg

                super(MyEncoder, self).__init__(**kwargs)

            def default(self, o):
                return self.default_msg

        with warnings.catch_warnings(record=True) as w:
            field = JSONField(
                encoder_cls=MyEncoder,
                encoder_kwargs={
                    'default_msg': 'What even is this?',
                })

        self.assertEqual(field.dumps(MyEncoder), '"What even is this?"')
        self.assertEqual(len(w), 0)

    def test_init_with_custom_encoder_instance(self):
        """Testing JSONField initialization with deprecated custom encoder
        instance
        """
        class MyEncoder(json.JSONEncoder):
            def default(self, o):
                return 'What even is this?'

        with warnings.catch_warnings(record=True) as w:
            field = JSONField(encoder=MyEncoder())

        self.assertEqual(field.dumps(MyEncoder), '"What even is this?"')
        self.assertEqual(len(w), 1)

        message = w[0].message
        self.assertIsInstance(message, DeprecationWarning)
        self.assertEqual(six.text_type(message),
                         'The encoder argument to JSONField has been '
                         'replaced by the encoder_cls and encoder_kwargs '
                         'arguments. Support for encoder is deprecated.')

    def test_dumps_with_json_dict(self):
        """Testing JSONField with dumping a JSON dictionary"""
        result = self.field.dumps({'a': 1, 'b': 2})
        self.assertTrue(isinstance(result, six.string_types))
        self.assertEqual(result, '{"a": 1, "b": 2}')

    def test_dumps_with_json_string(self):
        """Testing JSONField with dumping a JSON string"""
        result = self.field.dumps('{"a": 1, "b": 2}')
        self.assertTrue(isinstance(result, six.string_types))
        self.assertEqual(result, '{"a": 1, "b": 2}')

    def test_loading_json_dict(self):
        """Testing JSONField with loading a JSON dictionary"""
        result = self.field.loads('{"a": 1, "b": 2}')
        self.assertTrue(isinstance(result, dict))
        self.assertTrue('a' in result)
        self.assertTrue('b' in result)

    def test_loading_json_broken_dict(self):
        """Testing JSONField with loading a badly serialized JSON dictionary"""
        result = self.field.loads('{u"a": 1, u"b": 2}')
        self.assertTrue(isinstance(result, dict))
        self.assertTrue('a' in result)
        self.assertTrue('b' in result)

    def test_loading_json_array(self):
        """Testing JSONField with loading a JSON array"""
        result = self.field.loads('[1, 2, 3]')
        self.assertTrue(isinstance(result, list))
        self.assertEqual(result, [1, 2, 3])

    def test_loading_string(self):
        """Testing JSONField with loading a stored string"""
        result = self.field.loads('"foo"')
        self.assertTrue(isinstance(result, dict))
        self.assertEqual(result, {})

    def test_loading_broken_string(self):
        """Testing JSONField with loading a broken stored string"""
        result = self.field.loads('u"foo"')
        self.assertTrue(isinstance(result, dict))
        self.assertEqual(result, {})

    def test_loading_python_code(self):
        """Testing JSONField with loading Python code"""
        result = self.field.loads('locals()')
        self.assertTrue(isinstance(result, dict))
        self.assertEqual(result, {})

    def test_get_json(self):
        """Testing JSONField with get_{fieldname}_json"""
        class MyModel(Model):
            myfield = JSONField()

        model = MyModel()
        model.myfield = {
            'a': 1,
            'b': 2,
        }

        self.assertEqual(model.get_myfield_json(),
                         '{"a": 1, "b": 2}')

    def test_set_json(self):
        """Testing JSONField with set_{fieldname}_json"""
        class MyModel(Model):
            myfield = JSONField()

        model = MyModel()
        model.set_myfield_json('{"a": 1, "b": 2}')

        self.assertEqual(
            model.myfield,
            {
                'a': 1,
                'b': 2,
            })

    def test_validate_with_valid_json_string(self):
        """Testing JSONField with validating a valid JSON string"""
        self.field.run_validators('{"a": 1, "b": 2}')

    def test_validate_with_invalid_json_string(self):
        """Testing JSONField with validating an invalid JSON string"""
        self.assertRaises(ValidationError,
                          lambda: self.field.run_validators('foo'))

    def test_validate_with_json_dict(self):
        """Testing JSONField with validating a JSON dictionary"""
        self.field.run_validators({'a': 1, 'b': 2})


class JSONFormFieldTests(TestCase):
    """Unit tests for djblets.db.fields.JSONFormField."""

    def test_init_with_custom_encoder_class(self):
        """Testing JSONFormField initialization with custom encoder class"""
        class MyEncoder(json.JSONEncoder):
            def __init__(self, default_msg, **kwargs):
                self.default_msg = default_msg

                super(MyEncoder, self).__init__(**kwargs)

            def default(self, o):
                return self.default_msg

        field = JSONFormField(
            encoder_cls=MyEncoder,
            encoder_kwargs={
                'default_msg': 'What even is this?',
            })

        self.assertEqual(
            field.prepare_value({
                'a': 1,
                'b': 2,
                'cls': MyEncoder,
            }),
            '{\n'
            '  "a": 1,\n'
            '  "b": 2,\n'
            '  "cls": "What even is this?"\n'
            '}')

    def test_init_with_custom_encoder_instance(self):
        """Testing JSONFormField initialization with custom encoder instance"""
        class MyEncoder(json.JSONEncoder):
            def default(self, o):
                return 'What even is this?'

        field = JSONFormField(encoder=MyEncoder())

        self.assertEqual(
            field.prepare_value({
                'cls': MyEncoder,
            }),
            '{"cls": "What even is this?"}')

    def test_prepare_value_with_serialized(self):
        """Testing JSONFormField.prepare_value with serialized data"""
        field = JSONFormField()
        self.assertEqual(field.prepare_value('{"a": 1, "b": 2}'),
                         '{"a": 1, "b": 2}')

    def test_prepare_value_with_deserialized(self):
        """Testing JSONFormField.prepare_value with deserialized data"""
        field = JSONFormField()
        self.assertEqual(field.prepare_value({'a': 1, 'b': 2}),
                         '{\n'
                         '  "a": 1,\n'
                         '  "b": 2\n'
                         '}')

    def test_to_python_with_serialized(self):
        """Testing JSONFormField.to_python with serialized data"""
        field = JSONFormField()
        self.assertEqual(field.to_python('{"a": 1, "b": 2}'),
                         {'a': 1, 'b': 2})

    def test_to_python_with_deserialized(self):
        """Testing JSONFormField.to_python with deserialized data"""
        field = JSONFormField()
        self.assertEqual(field.to_python({"a": 1, "b": 2}),
                         {'a': 1, 'b': 2})

    def test_to_python_with_empty_string(self):
        """Testing JSONFormField.to_python with empty string"""
        field = JSONFormField()
        self.assertIsNone(field.to_python(''))

    def test_to_python_with_empty_non_string(self):
        """Testing JSONFormField.to_python with empty non-string value"""
        field = JSONFormField()
        self.assertEqual(field.to_python({}), {})
        self.assertEqual(field.to_python([]), [])

    def test_to_python_with_validation_error(self):
        """Testing JSONFormField.to_python with bad JSON data triggering
        ValidationError
        """
        field = JSONFormField()

        with self.assertRaises(ValidationError) as cm:
            field.to_python('{a: 1}')

        self.assertEqual(cm.exception.message,
                         'Expecting property name enclosed in double quotes: '
                         'line 1 column 2 (char 1)')
        self.assertEqual(cm.exception.code, 'invalid')
        self.assertEqual(cm.exception.params, {
            'value': '{a: 1}',
        })
