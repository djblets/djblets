from __future__ import unicode_literals

import json
import warnings

from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.db.models import Model
from django.utils import six
from djblets.siteconfig.models import SiteConfiguration

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

    def test_init_with_dict_value(self):
        """Testing JSONField initialization with initial dict value"""
        class MyModel(Model):
            myfield = JSONField()

        value = {
            'a': 1,
            'b': 2,
        }
        model = MyModel(myfield=value)

        # Make sure we're working with a copy in the model.
        value['c'] = 3

        self.assertEqual(model.myfield, {
            'a': 1,
            'b': 2,
        })
        self.assertEqual(model.get_myfield_json(),
                         '{"a": 1, "b": 2}')

    def test_init_with_dict_value_empty(self):
        """Testing JSONField initialization with initial empty dict value"""
        class MyModel(Model):
            myfield = JSONField()

        model = MyModel(myfield={})

        self.assertEqual(model.myfield, {})
        self.assertEqual(model.get_myfield_json(), '{}')

    def test_init_with_list_value(self):
        """Testing JSONField initialization with initial list value"""
        class MyModel(Model):
            myfield = JSONField()

        value = [1, 2]
        model = MyModel(myfield=value)

        # Make sure we're working with a copy in the model.
        value.append(3)

        self.assertEqual(model.myfield, [1, 2])
        self.assertEqual(model.get_myfield_json(), '[1, 2]')

    def test_init_with_list_value_empty(self):
        """Testing JSONField initialization with initial empty list value"""
        class MyModel(Model):
            myfield = JSONField()

        model = MyModel(myfield=[])

        self.assertEqual(model.myfield, [])
        self.assertEqual(model.get_myfield_json(), '[]')

    def test_init_with_json_string_value(self):
        """Testing JSONField initialization with initial JSON string value"""
        class MyModel(Model):
            myfield = JSONField()

        model = MyModel(myfield='{"a": 1, "b": 2}')

        self.assertEqual(model.myfield, {
            'a': 1,
            'b': 2,
        })
        self.assertEqual(model.get_myfield_json(),
                         '{"a": 1, "b": 2}')

    def test_init_with_json_string_value_empty(self):
        """Testing JSONField initialization with initial empty JSON string
        value
        """
        class MyModel(Model):
            myfield = JSONField()

        model = MyModel(myfield='')

        self.assertEqual(model.myfield, {})
        self.assertEqual(model.get_myfield_json(), '{}')

    def test_init_with_bad_type(self):
        """Testing JSONField initialization with initial unsupported value
        type
        """
        class MyModel(Model):
            myfield = JSONField()

        message = "%r is not a supported value type." % MyModel

        with self.assertRaisesMessage(ValidationError, message):
            MyModel(myfield=MyModel())

    def test_init_with_deferred(self):
        """Testing JSONField initialization with deferred attribute"""
        SiteConfiguration.objects.create(site=Site.objects.get_current())

        # Saving the SiteConfiguration results in a cache clear, so re-fetch
        # this in order to avoid a query below.
        Site.objects.get_current()

        # This should fetch just the SiteConfiguration, and not result in a
        # fetch of settings in JSONField.post_init.
        with self.assertNumQueries(1):
            SiteConfiguration.objects.defer('settings').get(pk=1)

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

    def test_get_prep_value_with_string(self):
        """Testing JSONField.get_prep_value with string value"""
        self.assertEqual(
            self.field.get_prep_value('{"a": 1, "b": 2}'),
            '{"a": 1, "b": 2}')

    def test_get_prep_value_with_dict(self):
        """Testing JSONField.get_prep_value with dict value"""
        self.assertEqual(
            self.field.get_prep_value({
                'a': 1,
                'b': 2,
            }),
            '{"a": 1, "b": 2}')

    def test_get_prep_value_with_none(self):
        """Testing JSONField.get_prep_value with None value"""
        self.assertIsNone(self.field.get_prep_value(None))

    def test_to_python_with_string(self):
        """Testing JSONField.to_python with string value"""
        self.assertEqual(
            self.field.to_python('{"a": 1, "b": 2}'),
            {
                'a': 1,
                'b': 2,
            })

    def test_to_python_with_dict(self):
        """Testing JSONField.to_python with dictionary value"""
        self.assertEqual(
            self.field.to_python({
                'a': 1,
                'b': 2,
            }),
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
