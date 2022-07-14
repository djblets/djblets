"""Unit tests for djblets.forms.fields.ListEditField."""

from djblets.forms.fields import ListEditField
from djblets.testing.testcases import TestCase


class ListEditFieldTests(TestCase):
    """Unit tests for djblets.forms.fields.ListEditField."""

    def test_prepare_value(self):
        """Testing ListEditField.prepare_value"""
        field = ListEditField()

        self.assertEqual(
            field.prepare_value(' foo,  bar , baz '),
            ['foo', 'bar', 'baz'])

    def test_prepare_value_with_custom_separator(self):
        """Testing ListEditField.prepare_value with a custom separator"""
        field = ListEditField(sep=';')

        self.assertEqual(
            field.prepare_value(' foo;  bar ; baz '),
            ['foo', 'bar', 'baz'])

    def test_prepare_value_with_null_value(self):
        """Testing ListEditField.prepare_value with a null value"""
        field = ListEditField()

        self.assertEqual(
            field.prepare_value(None),
            [''])

    def test_prepare_value_with_list_value(self):
        """Testing ListEditField.prepare_value with a list"""
        field = ListEditField()

        self.assertEqual(
            field.prepare_value(['foo', 'bar', 'baz']),
            ['foo', 'bar', 'baz'])

    def test_to_python(self):
        """Testing ListEditField.to_python"""
        field = ListEditField()

        self.assertEqual(
            field.to_python(['foo', 'bar', 'baz']),
            'foo,bar,baz')

    def test_to_python_with_custom_separator(self):
        """Testing ListEditField.to_python with a custom separator"""
        field = ListEditField(sep=';')

        self.assertEqual(
            field.to_python(['foo', 'bar', 'baz']),
            'foo;bar;baz')
