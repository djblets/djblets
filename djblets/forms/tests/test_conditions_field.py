from __future__ import unicode_literals

from django.forms import Form, ValidationError

from djblets.conditions.choices import (BaseConditionChoice,
                                        BaseConditionIntegerChoice,
                                        BaseConditionStringChoice,
                                        ConditionChoices)
from djblets.conditions.conditions import ConditionSet
from djblets.forms.fields import ConditionsField
from djblets.testing.testcases import TestCase


class ConditionsFieldTests(TestCase):
    """Unit tests for djblets.forms.fields.ConditionsField."""

    def test_init_with_choices_instance(self):
        """Testing ConditionsField initialization with choices instance"""
        choices = ConditionChoices([BaseConditionStringChoice])
        field = ConditionsField(choices=choices)

        self.assertIs(field.choices, choices)

    def test_init_with_choices_subclass(self):
        """Testing ConditionsField initialization with choices subclass"""
        class MyChoices(ConditionChoices):
            choice_classes = [BaseConditionStringChoice]

        field = ConditionsField(choices=MyChoices)

        self.assertIs(field.choices.__class__, MyChoices)

    def test_init_with_choice_kwargs(self):
        """Testing ConditionsField initialization with choice_kwargs"""
        choices = ConditionChoices([BaseConditionStringChoice])
        field = ConditionsField(choices=choices, choice_kwargs={'abc': 123})

        self.assertEqual(field.widget.choice_kwargs, field.choice_kwargs)

    def test_init_with_missing_operators(self):
        """Testing ConditionsField initialization with choices missing
        operators
        """
        class MyChoice(BaseConditionChoice):
            choice_id = 'my-choice'

        choices = ConditionChoices([MyChoice])
        msg = 'MyChoice must define a non-empty "operators" attribute.'

        with self.assertRaisesMessage(ValueError, msg):
            ConditionsField(choices=choices)

    def test_choice_kwargs_with_multiple_instances(self):
        """Testing ConditionsField.choice_kwargs works with multiple instances
        """
        # This tests for a bug that existed prior to Djblets 1.0.10, where
        # data set in choice_kwargs in one instance of a form would get shared
        # amongst other instances.
        class MyForm(Form):
            conditions = ConditionsField(
                choices=ConditionChoices([BaseConditionStringChoice]))

        form1 = MyForm()
        form2 = MyForm()

        form1.fields['conditions'].choice_kwargs['a'] = 1

        self.assertNotIn('a', form2.fields['conditions'].choice_kwargs)

    def test_prepare_value_with_condition_set(self):
        """Testing ConditionsField.prepare_value with ConditionSet"""
        choices = ConditionChoices([BaseConditionStringChoice])
        field = ConditionsField(choices=choices)

        self.assertEqual(
            field.prepare_value(ConditionSet()),
            {
                'mode': 'all',
                'conditions': [],
            })

    def test_prepare_value_with_serialized_data(self):
        """Testing ConditionsField.prepare_value with serialized data"""
        choices = ConditionChoices([BaseConditionStringChoice])
        field = ConditionsField(choices=choices)

        data = {
            'mode': 'all',
            'conditions': [],
        }

        self.assertEqual(field.prepare_value(data), data)

    def test_to_python(self):
        """Testing ConditionsField.to_python"""
        class MyChoice(BaseConditionStringChoice):
            choice_id = 'my-choice'

        choices = ConditionChoices([MyChoice])
        field = ConditionsField(choices=choices)

        condition_set = field.to_python({
            'mode': 'any',
            'conditions': [{
                'choice': 'my-choice',
                'op': 'is',
                'value': 'my-value',
            }]
        })

        self.assertEqual(condition_set.mode, ConditionSet.MODE_ANY)
        self.assertEqual(len(condition_set.conditions), 1)

        condition = condition_set.conditions[0]
        self.assertEqual(condition.choice.choice_id, 'my-choice')
        self.assertEqual(condition.operator.operator_id, 'is')
        self.assertEqual(condition.value, 'my-value')

    def test_to_python_with_choice_kwargs(self):
        """Testing ConditionsField.to_python with choice_kwargs set"""
        class MyChoice(BaseConditionStringChoice):
            choice_id = 'my-choice'

        choices = ConditionChoices([MyChoice])
        field = ConditionsField(choices=choices,
                                choice_kwargs={'abc': 123})

        condition_set = field.to_python({
            'mode': 'any',
            'conditions': [{
                'choice': 'my-choice',
                'op': 'is',
                'value': 'my-value',
            }]
        })

        self.assertEqual(condition_set.mode, ConditionSet.MODE_ANY)
        self.assertEqual(len(condition_set.conditions), 1)

        choice = condition_set.conditions[0].choice
        self.assertEqual(choice.choice_id, 'my-choice')
        self.assertEqual(choice.extra_state, {'abc': 123})

    def test_to_python_with_mode_error(self):
        """Testing ConditionsField.to_python with mode error"""
        choices = ConditionChoices()
        field = ConditionsField(choices=choices)

        with self.assertRaises(ValidationError) as cm:
            field.to_python({
                'mode': 'invalid',
                'conditions': [],
            })

        self.assertEqual(cm.exception.messages,
                         ['"invalid" is not a valid condition mode.'])
        self.assertEqual(cm.exception.code, 'invalid_mode')

    def test_to_python_with_choice_not_found_error(self):
        """Testing ConditionsField.to_python with choice not found error"""
        choices = ConditionChoices()
        field = ConditionsField(choices=choices)

        with self.assertRaises(ValidationError) as cm:
            field.to_python({
                'mode': 'any',
                'conditions': [{
                    'choice': 'invalid-choice',
                    'op': 'is',
                    'value': 'my-value',
                }],
            })

        self.assertEqual(cm.exception.messages,
                         ['There was an error with one of your conditions.'])
        self.assertEqual(cm.exception.code, 'condition_errors')
        self.assertEqual(
            field.widget.condition_errors,
            {
                0: 'No condition choice was found matching "invalid-choice".',
            })

    def test_to_python_with_operator_not_found_error(self):
        """Testing ConditionsField.to_python with operator not found error"""
        class MyChoice(BaseConditionStringChoice):
            choice_id = 'my-choice'

        choices = ConditionChoices([MyChoice])
        field = ConditionsField(choices=choices)

        with self.assertRaises(ValidationError) as cm:
            field.to_python({
                'mode': 'any',
                'conditions': [{
                    'choice': 'my-choice',
                    'op': 'invalid-op',
                    'value': 'my-value',
                }],
            })

        self.assertEqual(cm.exception.messages,
                         ['There was an error with one of your conditions.'])
        self.assertEqual(cm.exception.code, 'condition_errors')
        self.assertEqual(
            field.widget.condition_errors,
            {
                0: 'No operator was found matching "invalid-op".',
            })

    def test_to_python_with_invalid_value_error(self):
        """Testing ConditionsField.to_python with invalid value error"""
        class MyChoice(BaseConditionIntegerChoice):
            choice_id = 'my-choice'

        choices = ConditionChoices([MyChoice])
        field = ConditionsField(choices=choices)

        with self.assertRaises(ValidationError) as cm:
            field.to_python({
                'mode': 'any',
                'conditions': [{
                    'choice': 'my-choice',
                    'op': 'is',
                    'value': 'invalid-value',
                }],
            })

        self.assertEqual(cm.exception.messages,
                         ['There was an error with one of your conditions.'])
        self.assertEqual(cm.exception.code, 'condition_errors')
        self.assertEqual(
            field.widget.condition_errors,
            {
                0: 'Enter a whole number.',
            })

    def test_to_python_with_value_required_error(self):
        """Testing ConditionsField.to_python with value required error"""
        class MyChoice(BaseConditionStringChoice):
            choice_id = 'my-choice'

        choices = ConditionChoices([MyChoice])
        field = ConditionsField(choices=choices)

        with self.assertRaises(ValidationError) as cm:
            field.to_python({
                'mode': 'any',
                'conditions': [{
                    'choice': 'my-choice',
                    'op': 'is',
                }],
            })

        self.assertEqual(cm.exception.messages,
                         ['There was an error with one of your conditions.'])
        self.assertEqual(cm.exception.code, 'condition_errors')
        self.assertEqual(
            field.widget.condition_errors,
            {
                0: 'A value is required.',
            })
