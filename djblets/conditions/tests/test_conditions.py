from __future__ import unicode_literals

from django import forms
from django.utils import six
from kgb import SpyAgency

from djblets.conditions.choices import BaseConditionChoice, ConditionChoices
from djblets.conditions.conditions import Condition, ConditionSet
from djblets.conditions.errors import (ConditionChoiceNotFoundError,
                                       ConditionOperatorNotFoundError,
                                       InvalidConditionModeError,
                                       InvalidConditionValueError)
from djblets.conditions.operators import (BaseConditionOperator,
                                          ConditionOperators)
from djblets.conditions.values import ConditionValueFormField
from djblets.testing.testcases import TestCase


class BasicTestOperator(BaseConditionOperator):
    operator_id = 'basic-test-op'


class BooleanTestOperator(BaseConditionOperator):
    operator_id = 'boolean-test-op'
    value_field = ConditionValueFormField(forms.BooleanField())


class NoValueTestOperator(BaseConditionOperator):
    operator_id = 'no-value-test-op'
    value_field = None


class EqualsTestOperator(BaseConditionOperator):
    operator_id = 'equals-test-op'

    def matches(self, match_value, condition_value):
        return match_value == condition_value


class BasicTestChoice(BaseConditionChoice):
    choice_id = 'basic-test-choice'
    operators = ConditionOperators([BasicTestOperator])
    default_value_field = ConditionValueFormField(forms.CharField())


class EqualsTestChoice(BaseConditionChoice):
    choice_id = 'equals-test-choice'
    operators = ConditionOperators([EqualsTestOperator])
    default_value_field = ConditionValueFormField(forms.CharField())


class ConditionTests(SpyAgency, TestCase):
    """Unit tests for djblets.conditions.conditions.Condition."""

    def test_deserialize(self):
        """Testing Condition.deserialize"""
        choices = ConditionChoices([BasicTestChoice])

        condition = Condition.deserialize(
            choices,
            {
                'choice': 'basic-test-choice',
                'op': 'basic-test-op',
                'value': 'my-value',
            })

        self.assertEqual(condition.choice.__class__, BasicTestChoice)
        self.assertEqual(condition.operator.__class__, BasicTestOperator)
        self.assertEqual(condition.value, 'my-value')
        self.assertEqual(condition.raw_value, 'my-value')

    def test_deserialize_with_choice_kwargs(self):
        """Testing Condition.deserialize with choice_kwargs"""
        choices = ConditionChoices([BasicTestChoice])

        condition = Condition.deserialize(
            choices,
            {
                'choice': 'basic-test-choice',
                'op': 'basic-test-op',
                'value': 'my-value',
            },
            choice_kwargs={
                'abc': 123,
            })

        self.assertEqual(condition.choice.__class__, BasicTestChoice)
        self.assertEqual(condition.choice.extra_state, {'abc': 123})
        self.assertEqual(condition.operator.__class__, BasicTestOperator)
        self.assertEqual(condition.value, 'my-value')
        self.assertEqual(condition.raw_value, 'my-value')

    def test_deserialize_with_op_value_field(self):
        """Testing Condition.deserialize with operator's value_field"""
        class MyChoice(BaseConditionChoice):
            choice_id = 'my-choice'
            operators = ConditionOperators([BooleanTestOperator])
            default_value_field = ConditionValueFormField(forms.CharField())

        choices = ConditionChoices([MyChoice])

        condition = Condition.deserialize(
            choices,
            {
                'choice': 'my-choice',
                'op': 'boolean-test-op',
                'value': True,
            })

        self.assertEqual(condition.choice.__class__, MyChoice)
        self.assertEqual(condition.operator.__class__, BooleanTestOperator)
        self.assertEqual(condition.value, True)
        self.assertEqual(condition.raw_value, True)

    def test_deserialize_with_no_value_field(self):
        """Testing Condition.deserialize with no value_field"""
        class MyChoice(BaseConditionChoice):
            choice_id = 'my-choice'
            operators = ConditionOperators([NoValueTestOperator])
            default_value_field = ConditionValueFormField(forms.CharField())

        choices = ConditionChoices([MyChoice])

        condition = Condition.deserialize(
            choices,
            {
                'choice': 'my-choice',
                'op': 'no-value-test-op',
                'value': True,
            })

        self.assertEqual(condition.choice.__class__, MyChoice)
        self.assertEqual(condition.operator.__class__, NoValueTestOperator)
        self.assertEqual(condition.value, None)
        self.assertEqual(condition.raw_value, None)

    def test_deserialize_with_missing_choice(self):
        """Testing Condition.deserialize with missing choice in data"""
        choices = ConditionChoices()

        with self.assertRaises(ConditionChoiceNotFoundError) as cm:
            Condition.deserialize(
                choices,
                {
                    'op': 'my-op',
                    'value': 'my-value',
                },
                condition_index=1)

        e = cm.exception
        self.assertEqual(six.text_type(e), 'A choice is required.')
        self.assertEqual(e.condition_index, 1)

    def test_deserialize_with_missing_operator(self):
        """Testing Condition.deserialize with missing operator in data"""
        choices = ConditionChoices()

        with self.assertRaises(ConditionOperatorNotFoundError) as cm:
            Condition.deserialize(
                choices,
                {
                    'choice': 'my-choice',
                    'value': 'my-value',
                },
                condition_index=1)

        e = cm.exception
        self.assertEqual(six.text_type(e), 'An operator is required.')
        self.assertEqual(e.condition_index, 1)

    def test_deserialize_with_missing_value(self):
        """Testing Condition.deserialize with missing value in data"""
        choices = ConditionChoices([BasicTestChoice])

        with self.assertRaises(InvalidConditionValueError) as cm:
            Condition.deserialize(
                choices,
                {
                    'choice': 'basic-test-choice',
                    'op': 'basic-test-op',
                },
                condition_index=1)

        e = cm.exception
        self.assertEqual(six.text_type(e), 'A value is required.')
        self.assertEqual(e.condition_index, 1)

    def test_deserialize_with_invalid_choice(self):
        """Testing Condition.deserialize with invalid choice in data"""
        choices = ConditionChoices()

        with self.assertRaises(ConditionChoiceNotFoundError) as cm:
            Condition.deserialize(
                choices,
                {
                    'choice': 'invalid-choice',
                    'op': 'my-op',
                    'value': 'my-value',
                },
                condition_index=1)

        e = cm.exception
        self.assertEqual(six.text_type(e),
                         'No condition choice was found matching '
                         '"invalid-choice".')
        self.assertEqual(e.choice_id, 'invalid-choice')
        self.assertEqual(e.condition_index, 1)

    def test_deserialize_with_invalid_operator(self):
        """Testing Condition.deserialize with invalid operator in data"""
        class MyChoice(BaseConditionChoice):
            choice_id = 'my-choice'
            operators = ConditionOperators()

        choices = ConditionChoices([MyChoice])

        with self.assertRaises(ConditionOperatorNotFoundError) as cm:
            Condition.deserialize(
                choices,
                {
                    'choice': 'my-choice',
                    'op': 'invalid-op',
                    'value': 'my-value',
                },
                condition_index=1)

        e = cm.exception
        self.assertEqual(six.text_type(e),
                         'No operator was found matching '
                         '"invalid-op".')
        self.assertEqual(e.operator_id, 'invalid-op')
        self.assertEqual(e.condition_index, 1)

    def test_deserialize_with_invalid_value(self):
        """Testing Condition.deserialize with invalid value in data"""
        class MyChoice(BaseConditionChoice):
            choice_id = 'my-choice'
            operators = ConditionOperators([BasicTestOperator])
            default_value_field = ConditionValueFormField(forms.IntegerField())

        choices = ConditionChoices([MyChoice])

        with self.assertRaises(InvalidConditionValueError) as cm:
            Condition.deserialize(
                choices,
                {
                    'choice': 'my-choice',
                    'op': 'basic-test-op',
                    'value': 'invalid-value'
                },
                condition_index=1)

        e = cm.exception
        self.assertEqual(six.text_type(e), 'Enter a whole number.')
        self.assertEqual(e.code, 'invalid')
        self.assertEqual(e.condition_index, 1)

    def test_serialize(self):
        """Testing Condition.serialize"""
        class MyChoice(BaseConditionChoice):
            choice_id = 'my-choice'
            operators = ConditionOperators([BasicTestOperator])
            default_value_field = ConditionValueFormField(forms.IntegerField())

        choice = MyChoice()
        condition = Condition(choice, choice.get_operator('basic-test-op'),
                              123)

        self.assertEqual(
            condition.serialize(),
            {
                'choice': 'my-choice',
                'op': 'basic-test-op',
                'value': 123,
            })

    def test_serialize_without_value_field(self):
        """Testing Condition.serialize without a value_field"""
        class MyChoice(BaseConditionChoice):
            choice_id = 'my-choice'
            operators = ConditionOperators([BasicTestOperator])

        choice = MyChoice()
        condition = Condition(choice, choice.get_operator('basic-test-op'))

        self.assertEqual(
            condition.serialize(),
            {
                'choice': 'my-choice',
                'op': 'basic-test-op',
            })

    def test_matches_with_match(self):
        """Testing Condition.matches with match"""
        choice = EqualsTestChoice()
        condition = Condition(choice, choice.get_operator('equals-test-op'),
                              'abc123')
        self.assertTrue(condition.matches('abc123'))

    def test_matches_with_no_match(self):
        """Testing Condition.matches with no match"""
        choice = EqualsTestChoice()
        condition = Condition(choice, choice.get_operator('equals-test-op'),
                              'abc123')
        self.assertFalse(condition.matches('def123'))


class ConditionSetTests(TestCase):
    """Unit tests for djblets.conditions.conditions.ConditionSet."""

    def test_deserialize(self):
        """Testing ConditionSet.deserialize"""
        choices = ConditionChoices([BasicTestChoice])

        condition_set = ConditionSet.deserialize(
            choices,
            {
                'mode': 'any',
                'conditions': [
                    {
                        'choice': 'basic-test-choice',
                        'op': 'basic-test-op',
                        'value': 'my-value',
                    },
                ],
            })

        self.assertEqual(condition_set.mode, ConditionSet.MODE_ANY)
        self.assertEqual(len(condition_set.conditions), 1)
        self.assertEqual(condition_set.conditions[0].choice.choice_id,
                         'basic-test-choice')

    def test_deserialize_with_choice_kwargs(self):
        """Testing ConditionSet.deserialize with choice_kwargs"""
        choices = ConditionChoices([BasicTestChoice])

        condition_set = ConditionSet.deserialize(
            choices,
            {
                'mode': 'any',
                'conditions': [
                    {
                        'choice': 'basic-test-choice',
                        'op': 'basic-test-op',
                        'value': 'my-value',
                    },
                ],
            },
            choice_kwargs={
                'abc': 123,
            })

        self.assertEqual(condition_set.mode, ConditionSet.MODE_ANY)
        self.assertEqual(len(condition_set.conditions), 1)

        choice = condition_set.conditions[0].choice
        self.assertEqual(choice.choice_id, 'basic-test-choice')
        self.assertEqual(choice.extra_state, {'abc': 123})

    def test_deserialize_with_invalid_mode(self):
        """Testing ConditionSet.deserialize with invalid mode"""
        choices = ConditionChoices([BasicTestChoice])

        with self.assertRaises(InvalidConditionModeError):
            ConditionSet.deserialize(
                choices,
                {
                    'mode': 'invalid',
                    'conditions': [
                        {
                            'choice': 'basic-test-choice',
                            'op': 'basic-test-op',
                            'value': 'my-value',
                        },
                    ],
                })

    def test_matches_with_always_mode(self):
        """Testing ConditionSet.matches with "always" mode"""
        condition_set = ConditionSet(ConditionSet.MODE_ALWAYS, [])
        self.assertTrue(condition_set.matches(value='abc123'))

    def test_matches_with_all_mode_and_match(self):
        """Testing ConditionSet.matches with "all" mode and match"""
        choice = EqualsTestChoice()

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(choice, choice.get_operator('equals-test-op'), 'abc123'),
            Condition(choice, choice.get_operator('equals-test-op'), 'abc123'),
        ])

        self.assertTrue(condition_set.matches(value='abc123'))

    def test_matches_with_all_mode_and_no_match(self):
        """Testing ConditionSet.matches with "all" mode and no match"""
        choice = EqualsTestChoice()

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(choice, choice.get_operator('equals-test-op'), 'abc123'),
            Condition(choice, choice.get_operator('equals-test-op'), 'def123'),
        ])

        self.assertFalse(condition_set.matches(value='abc123'))

    def test_matches_with_any_mode_and_match(self):
        """Testing ConditionSet.matches with "any" mode and match"""
        choice = EqualsTestChoice()

        condition_set = ConditionSet(ConditionSet.MODE_ANY, [
            Condition(choice, choice.get_operator('equals-test-op'), 'abc123'),
            Condition(choice, choice.get_operator('equals-test-op'), 'def123'),
        ])

        self.assertTrue(condition_set.matches(value='abc123'))

    def test_matches_with_any_mode_and_no_match(self):
        """Testing ConditionSet.matches with "any" mode and no match"""
        choice = EqualsTestChoice()

        condition_set = ConditionSet(ConditionSet.MODE_ANY, [
            Condition(choice, choice.get_operator('equals-test-op'), 'abc123'),
            Condition(choice, choice.get_operator('equals-test-op'), 'def123'),
        ])

        self.assertFalse(condition_set.matches(value='foo'))

    def test_matches_with_custom_value_kwargs(self):
        """Testing ConditionSet.matches with custom value keyword arguments"""
        class CustomEqualsChoice(EqualsTestChoice):
            value_kwarg = 'my_value'

        choice = CustomEqualsChoice()

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(choice, choice.get_operator('equals-test-op'),
                      'abc123'),
        ])

        self.assertTrue(condition_set.matches(my_value='abc123'))
        self.assertFalse(condition_set.matches(value='abc123'))

    def test_matches_with_all_mode_and_custom_value_kwargs_multiple(self):
        """Testing ConditionSet.matches with "all" mode and multiple custom
        value keyword arguments across multiple choices
        """
        class CustomEqualsChoice1(EqualsTestChoice):
            value_kwarg = 'my_value1'

        class CustomEqualsChoice2(EqualsTestChoice):
            value_kwarg = 'my_value2'

        choice1 = CustomEqualsChoice1()
        choice2 = CustomEqualsChoice2()

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(choice1, choice1.get_operator('equals-test-op'),
                      'abc123'),
            Condition(choice2, choice2.get_operator('equals-test-op'),
                      'def456'),
        ])

        self.assertTrue(condition_set.matches(my_value1='abc123',
                                              my_value2='def456'))
        self.assertFalse(condition_set.matches(my_value1='abc123'))
        self.assertFalse(condition_set.matches(my_value2='def456'))
        self.assertFalse(condition_set.matches(my_value1='abc123',
                                               my_value2='xxx'))

    def test_matches_with_any_mode_and_custom_value_kwargs_multiple(self):
        """Testing ConditionSet.matches with "any" mode and multiple custom
        value keyword arguments across multiple choices
        """
        class CustomEqualsChoice1(EqualsTestChoice):
            value_kwarg = 'my_value1'

        class CustomEqualsChoice2(EqualsTestChoice):
            value_kwarg = 'my_value2'

        choice1 = CustomEqualsChoice1()
        choice2 = CustomEqualsChoice2()

        condition_set = ConditionSet(ConditionSet.MODE_ANY, [
            Condition(choice1, choice1.get_operator('equals-test-op'),
                      'abc123'),
            Condition(choice2, choice2.get_operator('equals-test-op'),
                      'def456'),
        ])

        self.assertTrue(condition_set.matches(my_value1='abc123',
                                              my_value2='def456'))
        self.assertTrue(condition_set.matches(my_value1='abc123'))
        self.assertTrue(condition_set.matches(my_value2='def456'))
        self.assertTrue(condition_set.matches(my_value1='abc123',
                                              my_value2='xxx'))
        self.assertFalse(condition_set.matches(my_value1='xxx',
                                               my_value2='xxx'))

    def test_serialize(self):
        """Testing ConditionSet.serialize"""
        basic_choice = BasicTestChoice()
        equals_choice = EqualsTestChoice()

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(basic_choice,
                      basic_choice.get_operator('basic-test-op'),
                      'abc123'),
            Condition(equals_choice,
                      equals_choice.get_operator('equals-test-op'),
                      'def123'),
        ])

        result = condition_set.serialize()

        self.assertEqual(
            result,
            {
                'mode': 'all',
                'conditions': [
                    {
                        'choice': 'basic-test-choice',
                        'op': 'basic-test-op',
                        'value': 'abc123',
                    },
                    {
                        'choice': 'equals-test-choice',
                        'op': 'equals-test-op',
                        'value': 'def123',
                    },
                ],
            })
