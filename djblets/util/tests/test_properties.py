"""Unit tests for djblets.util.properties."""

from __future__ import unicode_literals

from django.utils import six

from djblets.testing.testcases import TestCase
from djblets.util.properties import AliasProperty, TypedProperty


class MyDeprecationWarning(DeprecationWarning):
    pass


class AliasPropertyTests(TestCase):
    """Unit tests for djblets.util.properties.AliasProperty."""

    def test_set(self):
        """Testing AliasProperty.__set__"""
        class MyObject(object):
            prop = AliasProperty('other_prop')
            other_prop = 100

        obj = MyObject()

        with self.assertNoWarnings():
            obj.prop = 42

        self.assertEqual(obj.other_prop, 42)

    def test_set_with_deprecated(self):
        """Testing AliasProperty.__set__ with deprecated=True"""
        class MyObject(object):
            prop = AliasProperty('other_prop',
                                 deprecated=True,
                                 deprecation_warning=MyDeprecationWarning)
            other_prop = 100

        obj = MyObject()

        expected_message = (
            'MyObject.prop is deprecated. Please set MyObject.other_prop '
            'instead.'
        )

        with self.assertWarns(MyDeprecationWarning, expected_message):
            obj.prop = 42

        self.assertEqual(obj.other_prop, 42)

    def test_set_with_convert_to_func(self):
        """Testing AliasProperty.__set__ with convert_to_func"""
        class MyObject(object):
            prop = AliasProperty('other_prop',
                                 convert_to_func=six.text_type)
            other_prop = '100'

        obj = MyObject()

        with self.assertNoWarnings():
            obj.prop = 42

        self.assertEqual(obj.other_prop, '42')

    def test_set_with_convert_to_func_and_none(self):
        """Testing AliasProperty.__set__ with convert_to_func and value=None"""
        class MyObject(object):
            prop = AliasProperty('other_prop',
                                 convert_to_func=six.text_type)
            other_prop = 100

        obj = MyObject()

        with self.assertNoWarnings():
            obj.prop = None

        self.assertIsNone(obj.other_prop)

    def test_get(self):
        """Testing AliasProperty.__get__"""
        class MyObject(object):
            prop = AliasProperty('other_prop')
            other_prop = 100

        obj = MyObject()

        with self.assertNoWarnings():
            self.assertEqual(obj.prop, 100)

    def test_get_with_deprecated(self):
        """Testing AliasProperty.__get__ with deprecated=True"""
        class MyObject(object):
            prop = AliasProperty('other_prop',
                                 deprecated=True,
                                 deprecation_warning=MyDeprecationWarning)
            other_prop = 100

        obj = MyObject()

        expected_message = (
            'MyObject.prop is deprecated. Please access MyObject.other_prop '
            'instead.'
        )

        with self.assertWarns(MyDeprecationWarning, expected_message):
            self.assertEqual(obj.prop, 100)

    def test_get_with_convert_from_func(self):
        """Testing AliasProperty.__get__ with convert_from_func"""
        class MyObject(object):
            prop = AliasProperty('other_prop',
                                 convert_from_func=six.text_type)
            other_prop = 100

        obj = MyObject()

        with self.assertNoWarnings():
            self.assertEqual(obj.prop, '100')

    def test_get_with_convert_from_func_and_none(self):
        """Testing AliasProperty.__get__ with convert_from_func and value=None
        """
        class MyObject(object):
            prop = AliasProperty('other_prop',
                                 convert_to_func=six.text_type)
            other_prop = None

        obj = MyObject()

        with self.assertNoWarnings():
            self.assertIsNone(obj.prop)


class TypedPropertyTests(TestCase):
    """Unit tests for djblets.util.properties.TypedProperty."""

    def test_with_valid_type(self):
        """Testing TypedProperty with valid type"""
        class MyObject(object):
            prop = TypedProperty((int, bool))

        obj = MyObject()

        obj.prop = 100
        self.assertEqual(obj.prop, 100)

        obj.prop = True
        self.assertIs(obj.prop, True)

    def test_with_invalid_type(self):
        """Testing TypedProperty with invalid type"""
        class MyObject(object):
            prop = TypedProperty((six.text_type,))

        obj = MyObject()

        expected_message = 'int (100) is not a valid type for this property.'

        with self.assertRaisesMessage(TypeError, expected_message):
            obj.prop = 100

    def test_set_with_none_and_allow_none_true(self):
        """Testing TypedProperty.__set__ with None value and allow_none=True"""
        class MyObject(object):
            prop = TypedProperty((int, bool), allow_none=True)

        obj = MyObject()
        obj.prop = None
        self.assertIsNone(obj.prop)

    def test_set_with_none_and_allow_none_false(self):
        """Testing TypedProperty.__set__ with None value and allow_none=False
        """
        class MyObject(object):
            prop = TypedProperty((int, bool), allow_none=False)

        obj = MyObject()

        expected_message = 'None is not a valid value for this property.'

        with self.assertRaisesMessage(TypeError, expected_message):
            obj.prop = None

    def test_get_with_default(self):
        """Testing TypedProperty.__get__ with default value"""
        class MyObject(object):
            prop = TypedProperty((int, bool), default=100)

        obj = MyObject()
        self.assertEqual(obj.prop, 100)
