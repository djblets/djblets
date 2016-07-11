from __future__ import unicode_literals

from djblets.conditions.choices import BaseConditionChoice
from djblets.conditions.errors import ConditionOperatorNotFoundError
from djblets.conditions.operators import (BaseConditionOperator,
                                          ConditionOperators)
from djblets.conditions.values import BaseConditionValueField
from djblets.testing.testcases import TestCase


class BaseConditionOperatorTests(TestCase):
    """Unit tests for djblets.conditions.operators.BaseConditionOperator."""

    def test_value_field_with_default(self):
        """Testing BaseConditionOperator.value_field with default choice field
        """
        class MyOperator(BaseConditionOperator):
            operator_id = 'my-op'

        class MyChoice(BaseConditionChoice):
            operators = ConditionOperators([
                MyOperator,
            ])

            default_value_field = BaseConditionValueField()

        choice = MyChoice()
        op = choice.get_operator('my-op')
        self.assertEqual(op.value_field, choice.default_value_field)
        self.assertFalse(op.has_custom_value_field)

    def test_value_field_with_custom(self):
        """Testing BaseConditionOperator.value_field with custom choice field
        """
        class MyOperator(BaseConditionOperator):
            operator_id = 'my-op'

            value_field = BaseConditionValueField()

        class MyChoice(BaseConditionChoice):
            operators = ConditionOperators([
                MyOperator,
            ])

            default_value_field = BaseConditionValueField()

        choice = MyChoice()
        op = choice.get_operator('my-op')
        self.assertNotEqual(op.value_field, choice.default_value_field)
        self.assertTrue(op.has_custom_value_field)


class ConditionOperatorsTests(TestCase):
    """Unit tests for djblets.conditions.operators.ConditionOperators."""

    def test_init_with_class_operators(self):
        """Testing ConditionOperators initialization with class-defined operators
        """
        class MyOperator1(BaseConditionOperator):
            operator_id = 'my-operator-1'

        class MyOperators(ConditionOperators):
            operator_classes = [
                MyOperator1,
            ]

        operators = MyOperators()
        self.assertEqual(list(operators), [MyOperator1])

    def test_init_with_caller_operators(self):
        """Testing ConditionOperators initialization with caller-defined operators
        """
        class MyOperator1(BaseConditionOperator):
            operator_id = 'my-operator-1'

        class MyOperator2(BaseConditionOperator):
            operator_id = 'my-operator-2'

        class MyOperators(ConditionOperators):
            operator_classes = [
                MyOperator1,
            ]

        operators = MyOperators([MyOperator2])
        self.assertEqual(list(operators), [MyOperator2])

    def test_get_operator(self):
        """Testing ConditionOperators.get_operator"""
        class MyOperator1(BaseConditionOperator):
            operator_id = 'my-operator-1'

        class MyChoice(BaseConditionChoice):
            operators = ConditionOperators([MyOperator1])

        choice = MyChoice()
        self.assertEqual(
            choice.operators.get_operator('my-operator-1', choice).__class__,
            MyOperator1)

    def test_get_operator_with_invalid_id(self):
        """Testing ConditionOperators.get_operator with invalid ID"""
        operators = ConditionOperators()

        with self.assertRaises(ConditionOperatorNotFoundError):
            operators.get_operator('invalid', None)
