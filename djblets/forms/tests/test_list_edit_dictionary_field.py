"""Unit tests for djblets.forms.fields.ListEditDictionaryField."""

from djblets.forms.fields import ListEditDictionaryField
from djblets.testing.testcases import TestCase


class ListEditDictionaryFieldTests(TestCase):
    """Unit tests for djblets.forms.fields.ListEditDictionaryField."""

    def test_prepare_value(self):
        """Testing ListEditDictionaryField.prepare_value"""
        field = ListEditDictionaryField()

        self.assertEqual(
            field.prepare_value({1: 'foo',
                                 2: 'bar',
                                 3: 'baz'}),
            [(1, 'foo'), (2, 'bar'), (3, 'baz')])

    def test_prepare_value_with_null_value(self):
        """Testing ListEditDictionaryField.prepare_value with a null value"""
        field = ListEditDictionaryField()

        self.assertEqual(
            field.prepare_value(None),
            [])

    def test_prepare_value_with_list_value(self):
        """Testing ListEditDictionaryField.prepare_value with a list"""
        field = ListEditDictionaryField()

        self.assertEqual(
            field.prepare_value([(1, 'foo'), (2, 'bar'), (3, 'baz')]),
            [(1, 'foo'), (2, 'bar'), (3, 'baz')])

    def test_to_python(self):
        """Testing ListEditDictionaryField.to_python"""
        field = ListEditDictionaryField()

        self.assertEqual(
            field.to_python([(1, 'foo'), (2, 'bar'), (3, 'baz')]),
            {1: 'foo',
             2: 'bar',
             3: 'baz'})
