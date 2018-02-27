from __future__ import unicode_literals

import copy

from django.utils import six
from django.utils.datastructures import MultiValueDict

from djblets.conditions.choices import (BaseConditionChoice,
                                        BaseConditionIntegerChoice,
                                        ConditionChoices)
from djblets.conditions.operators import (BaseConditionOperator,
                                          ConditionOperators)
from djblets.conditions.values import (ConditionValueCharField,
                                       ConditionValueIntegerField)
from djblets.forms.fields import ConditionsField
from djblets.testing.testcases import TestCase


class ConditionsWidgetTests(TestCase):
    """Unit tests for djblets.forms.widgets.ConditionsWidget."""

    def test_deepcopy(self):
        """Testing ConditionsWidget.__deepcopy__"""
        class MyChoice(BaseConditionIntegerChoice):
            choice_id = 'my-choice'

        choices = ConditionChoices([MyChoice])
        field = ConditionsField(choices=choices)
        widget1 = field.widget
        widget2 = copy.deepcopy(widget1)

        widget1.mode_widget.attrs['foo'] = True
        widget1.choice_widget.attrs['foo'] = True
        widget1.operator_widget.attrs['foo'] = True
        widget1.condition_errors[0] = 'This is a test.'

        self.assertEqual(widget2.mode_widget.attrs, {})
        self.assertEqual(widget2.choice_widget.attrs, {})
        self.assertEqual(widget2.operator_widget.attrs, {})
        self.assertEqual(widget2.condition_errors, {})

        # Choices won't be modified between copies, and is a shared object,
        # so both should have the same instance.
        self.assertIs(widget1.choices, widget2.choices)

    def test_value_from_datadict(self):
        """Testing ConditionsWidget.value_from_datadict"""
        class MyChoice(BaseConditionIntegerChoice):
            choice_id = 'my-choice'

        choices = ConditionChoices([MyChoice])
        field = ConditionsField(choices=choices)

        data = MultiValueDict('')
        data.update({
            'my_conditions_mode': 'any',
            'my_conditions_last_id': '1',
            'my_conditions_choice[0]': 'my-choice',
            'my_conditions_operator[0]': 'is',
            'my_conditions_value[0]': 'my-value-1',
            'my_conditions_choice[1]': 'my-choice',
            'my_conditions_operator[1]': 'is-not',
            'my_conditions_value[1]': 'my-value-2',
        })

        self.assertEqual(
            field.widget.value_from_datadict(data, MultiValueDict(''),
                                             'my_conditions'),
            {
                'mode': 'any',
                'conditions': [
                    {
                        'choice': 'my-choice',
                        'op': 'is',
                        'value': 'my-value-1',
                    },
                    {
                        'choice': 'my-choice',
                        'op': 'is-not',
                        'value': 'my-value-2',
                    },
                ],
            })

    def test_value_from_datadict_with_missing_data(self):
        """Testing ConditionsWidget.value_from_datadict with missing data"""
        class MyChoice(BaseConditionIntegerChoice):
            choice_id = 'my-choice'

        choices = ConditionChoices([MyChoice])
        field = ConditionsField(choices=choices)

        data = MultiValueDict('')

        self.assertEqual(
            field.widget.value_from_datadict(data, MultiValueDict(''),
                                             'my_conditions'),
            {
                'mode': None,
                'conditions': [],
            })

    def test_value_from_datadict_with_missing_last_id(self):
        """Testing ConditionsWidget.value_from_datadict with missing last_id"""
        class MyChoice(BaseConditionIntegerChoice):
            choice_id = 'my-choice'

        choices = ConditionChoices([MyChoice])
        field = ConditionsField(choices=choices)

        data = MultiValueDict('')
        data.update({
            'my_conditions_mode': 'any',
            'my_conditions_choice[0]': 'my-choice',
            'my_conditions_operator[0]': 'is',
            'my_conditions_value[0]': 'my-value-1',
            'my_conditions_choice[1]': 'my-choice',
            'my_conditions_operator[1]': 'is-not',
            'my_conditions_value[1]': 'my-value-2',
        })

        self.assertEqual(
            field.widget.value_from_datadict(data, MultiValueDict(''),
                                             'my_conditions'),
            {
                'mode': 'any',
                'conditions': [],
            })

    def test_value_from_datadict_with_missing_choice_rows(self):
        """Testing ConditionsWidget.value_from_datadict with missing choice
        rows
        """
        class MyChoice(BaseConditionIntegerChoice):
            choice_id = 'my-choice'

        choices = ConditionChoices([MyChoice])
        field = ConditionsField(choices=choices)

        data = MultiValueDict('')
        data.update({
            'my_conditions_mode': 'any',
            'my_conditions_last_id': '5',
            'my_conditions_choice[5]': 'my-choice',
            'my_conditions_operator[5]': 'is-not',
            'my_conditions_value[5]': 'my-value',
        })

        self.assertEqual(
            field.widget.value_from_datadict(data, MultiValueDict(''),
                                             'my_conditions'),
            {
                'mode': 'any',
                'conditions': [
                    {
                        'choice': 'my-choice',
                        'op': 'is-not',
                        'value': 'my-value',
                    },
                ],
            })

    def test_get_context(self):
        """Testing ConditionsWidget.get_context"""
        class MyOperator1(BaseConditionOperator):
            operator_id = 'my-op-1'
            name = 'My Op 1'
            value_field = ConditionValueIntegerField()

        class MyOperator2(BaseConditionOperator):
            operator_id = 'my-op-2'
            name = 'My Op 2'
            value_field = ConditionValueCharField()

        class MyOperator3(BaseConditionOperator):
            operator_id = 'my-op-3'
            name = 'My Op 3'

        class MyChoice1(BaseConditionChoice):
            choice_id = 'my-choice-1'
            name = 'My Choice 1'
            operators = ConditionOperators([MyOperator1, MyOperator2])

        class MyChoice2(BaseConditionChoice):
            choice_id = 'my-choice-2'
            name = 'My Choice 2'
            operators = ConditionOperators([MyOperator3])

        choices = ConditionChoices([MyChoice1, MyChoice2])
        field = ConditionsField(choices=choices)

        result = field.widget.get_context(
            'my_conditions',
            {
                'mode': 'any',
                'conditions': [
                    {
                        'choice': 'my-choice-1',
                        'op': 'my-op-1',
                        'value': 'my-value-1',
                    },
                    {
                        'choice': 'my-choice-2',
                        'op': 'my-op-3',
                    },
                ],
            },
            {
                'id': 'my-conditions',
            })

        self.assertEqual(
            set(result),
            {
                'field_id', 'field_name', 'rendered_mode', 'rendered_rows',
                'serialized_choices', 'serialized_rows',
            })
        self.assertEqual(result['field_id'], 'my-conditions')
        self.assertEqual(result['field_name'], 'my_conditions')
        self.assertHTMLEqual(
            result['rendered_mode'],
            '<ul id="my_conditions_mode">\n'
            '<li><label for="my_conditions_mode_0">'
            '<input id="my_conditions_mode_0" name="my_conditions_mode"'
            ' type="radio" value="always" />'
            ' Always match</label></li>\n'
            '<li><label for="my_conditions_mode_1">'
            '<input id="my_conditions_mode_1" name="my_conditions_mode"'
            ' type="radio" value="all" />'
            ' Match <b>all</b> of the following:</label></li>\n'
            '<li><label for="my_conditions_mode_2">'
            '<input checked="checked" id="my_conditions_mode_2" '
            'name="my_conditions_mode" type="radio" value="any" />'
            ' Match <b>any</b> of the following:</label></li>\n'
            '</ul>')

        rendered_rows = result['rendered_rows']
        self.assertEqual(len(rendered_rows), 2)

        # Check the first rendered row.
        rendered_row = rendered_rows[0]
        self.assertEqual(set(six.iterkeys(rendered_row)),
                         {'choice', 'operator', 'error'})

        self.assertHTMLEqual(
            rendered_row['choice'],
            '<select id="my-conditions_choice_0"'
            ' name="my_conditions_choice[0]">\n'
            '<option value="my-choice-1" selected="selected">'
            'My Choice 1</option>\n'
            '<option value="my-choice-2">'
            'My Choice 2</option>\n'
            '</select>')

        self.assertHTMLEqual(
            rendered_row['operator'],
            '<select id="my-conditions_operator_0"'
            ' name="my_conditions_operator[0]">\n'
            '<option value="my-op-1" selected="selected">'
            'My Op 1</option>\n'
            '<option value="my-op-2">My Op 2</option>\n'
            '</select>')

        self.assertIsNone(rendered_row['error'])

        # Check the second rendered row.
        rendered_row = rendered_rows[1]
        self.assertEqual(set(six.iterkeys(rendered_row)),
                         {'choice', 'operator', 'error'})

        self.assertHTMLEqual(
            rendered_row['choice'],
            '<select id="my-conditions_choice_1"'
            ' name="my_conditions_choice[1]">\n'
            '<option value="my-choice-1">'
            'My Choice 1</option>\n'
            '<option value="my-choice-2" selected="selected">'
            'My Choice 2</option>\n'
            '</select>')

        self.assertHTMLEqual(
            rendered_row['operator'],
            '<select id="my-conditions_operator_1"'
            ' name="my_conditions_operator[1]">\n'
            '<option value="my-op-3" selected="selected">'
            'My Op 3</option>\n'
            '</select>')

        self.assertIsNone(rendered_row['error'])

        serialized_choices = result['serialized_choices']
        self.assertEqual(len(serialized_choices), 2)

        # Check the first serialized choice.
        serialized_choice = serialized_choices[0]
        self.assertEqual(set(six.iterkeys(serialized_choice)),
                         {'id', 'name', 'valueField', 'operators'})
        self.assertEqual(serialized_choice['id'], 'my-choice-1')
        self.assertEqual(serialized_choice['name'], 'My Choice 1')
        self.assertEqual(serialized_choice['valueField'], {})
        self.assertEqual(serialized_choice['valueField'], {})

        serialized_operators = serialized_choice['operators']
        self.assertEqual(len(serialized_operators), 2)

        # Check the first operator in the first serialized choice.
        serialized_operator = serialized_operators[0]
        self.assertEqual(set(six.iterkeys(serialized_operator)),
                         {'id', 'name', 'useValue', 'valueField'})
        self.assertEqual(serialized_operator['id'], 'my-op-1')
        self.assertEqual(serialized_operator['name'], 'My Op 1')
        self.assertTrue(serialized_operator['useValue'])

        serialized_value_field = serialized_operator['valueField']
        self.assertEqual(set(six.iterkeys(serialized_value_field)),
                         {'model', 'view'})

        serialized_value_model = serialized_value_field['model']
        self.assertEqual(serialized_value_model['className'],
                         'Djblets.Forms.ConditionValueField')
        self.assertHTMLEqual(serialized_value_model['data']['fieldHTML'],
                             '<input name="XXX" type="number" />')

        serialized_value_view = serialized_value_field['view']
        self.assertEqual(serialized_value_view['className'],
                         'Djblets.Forms.ConditionValueFormFieldView')
        self.assertEqual(serialized_value_view['data'], {})

        # Check the second operator in the first serialized choice.
        serialized_operator = serialized_operators[1]
        self.assertEqual(set(six.iterkeys(serialized_operator)),
                         {'id', 'name', 'useValue', 'valueField'})
        self.assertEqual(serialized_operator['id'], 'my-op-2')
        self.assertEqual(serialized_operator['name'], 'My Op 2')
        self.assertTrue(serialized_operator['useValue'])

        serialized_value_field = serialized_operator['valueField']
        self.assertEqual(set(six.iterkeys(serialized_value_field)),
                         {'model', 'view'})

        serialized_value_model = serialized_value_field['model']
        self.assertEqual(serialized_value_model['className'],
                         'Djblets.Forms.ConditionValueField')
        self.assertHTMLEqual(serialized_value_model['data']['fieldHTML'],
                             '<input name="XXX" type="text" />')

        serialized_value_view = serialized_value_field['view']
        self.assertEqual(serialized_value_view['className'],
                         'Djblets.Forms.ConditionValueFormFieldView')
        self.assertEqual(serialized_value_view['data'], {})

        self.assertEqual(
            serialized_choices[1],
            {
                'id': 'my-choice-2',
                'name': 'My Choice 2',
                'operators': [
                    {
                        'id': 'my-op-3',
                        'name': 'My Op 3',
                        'useValue': False,
                    },
                ],
                'valueField': {},
            })

        serialized_rows = result['serialized_rows']
        self.assertEqual(len(serialized_rows), 2)
        self.assertEqual(
            serialized_rows[0],
            {
                'choiceID': 'my-choice-1',
                'operatorID': 'my-op-1',
                'valid': True,
                'value': 'my-value-1',
            })
        self.assertEqual(
            serialized_rows[1],
            {
                'choiceID': 'my-choice-2',
                'operatorID': 'my-op-3',
                'valid': True,
                'value': None,
            })

    def test_get_context_with_invalid_choice(self):
        """Testing ConditionsWidget.get_context with invalid choice"""
        class MyOperator1(BaseConditionOperator):
            operator_id = 'my-op-1'
            name = 'My Op 1'
            value_field = ConditionValueIntegerField()

        class MyOperator2(BaseConditionOperator):
            operator_id = 'my-op-2'
            name = 'My Op 2'
            value_field = ConditionValueCharField()

        class MyChoice1(BaseConditionChoice):
            choice_id = 'my-choice-1'
            name = 'My Choice 1'
            operators = ConditionOperators([MyOperator1, MyOperator2])

        choices = ConditionChoices([MyChoice1])
        field = ConditionsField(choices=choices)

        result = field.widget.get_context(
            'my_conditions',
            {
                'mode': 'any',
                'conditions': [
                    {
                        'choice': 'invalid-choice',
                        'op': 'my-op-1',
                        'value': 'my-value-1',
                    },
                ],
            },
            {
                'id': 'my-conditions',
            })

        rendered_rows = result['rendered_rows']
        self.assertEqual(len(rendered_rows), 1)

        rendered_row = rendered_rows[0]
        self.assertEqual(set(six.iterkeys(rendered_row)),
                         {'choice', 'operator', 'error'})
        self.assertHTMLEqual(
            rendered_row['choice'],
            '<select disabled="disabled" id="my-conditions_choice_0"'
            ' name="my_conditions_choice[0]">\n'
            '<option value="my-choice-1">My Choice 1</option>\n'
            '<option value="invalid-choice" selected="selected">'
            'invalid-choice</option>\n'
            '</select>'
            '<input name="my_conditions_choice[0]" type="hidden"'
            ' value="invalid-choice" />')

        self.assertHTMLEqual(
            rendered_row['operator'],
            '<select disabled="disabled" id="my-conditions_operator_0"'
            ' name="my_conditions_operator[0]">\n'
            '<option value="my-op-1" selected="selected">'
            'my-op-1</option>\n'
            '</select>'
            '<input name="my_conditions_operator[0]" type="hidden"'
            ' value="my-op-1" />')

        self.assertEqual(
            rendered_row['error'],
            'This choice no longer exists. You will need to '
            'delete the condition in order to make changes.')

        serialized_choices = result['serialized_choices']
        self.assertEqual(len(serialized_choices), 1)
        self.assertEqual(serialized_choices[0]['id'], 'my-choice-1')

        serialized_rows = result['serialized_rows']
        self.assertEqual(
            serialized_rows,
            [{
                'choiceID': 'invalid-choice',
                'operatorID': 'my-op-1',
                'valid': False,
                'value': 'my-value-1',
                'error': ('This choice no longer exists. You will need to '
                          'delete the condition in order to make changes.'),
            }])

    def test_get_context_with_invalid_operator(self):
        """Testing ConditionsWidget.get_context with invalid operator"""
        class MyOperator1(BaseConditionOperator):
            operator_id = 'my-op-1'
            name = 'My Op 1'
            value_field = ConditionValueIntegerField()

        class MyChoice1(BaseConditionChoice):
            choice_id = 'my-choice'
            name = 'My Choice'
            operators = ConditionOperators([MyOperator1])

        choices = ConditionChoices([MyChoice1])
        field = ConditionsField(choices=choices)

        result = field.widget.get_context(
            'my_conditions',
            {
                'mode': 'any',
                'conditions': [
                    {
                        'choice': 'my-choice',
                        'op': 'invalid-op',
                        'value': 'my-value-1',
                    },
                ],
            },
            {
                'id': 'my-conditions',
            })

        rendered_rows = result['rendered_rows']
        self.assertEqual(len(rendered_rows), 1)

        rendered_row = rendered_rows[0]
        self.assertEqual(set(six.iterkeys(rendered_row)),
                         {'choice', 'operator', 'error'})
        self.assertHTMLEqual(
            rendered_row['choice'],
            '<select disabled="disabled" id="my-conditions_choice_0"'
            ' name="my_conditions_choice[0]">\n'
            '<option value="my-choice" selected="selected">'
            'My Choice</option>\n'
            '</select>'
            '<input name="my_conditions_choice[0]" type="hidden"'
            ' value="my-choice" />')

        self.assertHTMLEqual(
            rendered_row['operator'],
            '<select disabled="disabled" id="my-conditions_operator_0"'
            ' name="my_conditions_operator[0]">\n'
            '<option value="invalid-op" selected="selected">'
            'invalid-op</option>\n'
            '</select>'
            '<input name="my_conditions_operator[0]" type="hidden"'
            ' value="invalid-op" />')

        self.assertEqual(
            rendered_row['error'],
            'This operator no longer exists. You will need to '
            'delete the condition in order to make changes.')

        serialized_choices = result['serialized_choices']
        self.assertEqual(len(serialized_choices), 1)
        self.assertEqual(serialized_choices[0]['id'], 'my-choice')

        serialized_rows = result['serialized_rows']
        self.assertEqual(
            serialized_rows,
            [{
                'choiceID': 'my-choice',
                'operatorID': 'invalid-op',
                'valid': False,
                'value': 'my-value-1',
                'error': ('This operator no longer exists. You will need to '
                          'delete the condition in order to make changes.'),
            }])

    def test_get_context_with_condition_errors(self):
        """Testing ConditionsWidget.get_context with condition errors"""
        class MyOperator1(BaseConditionOperator):
            operator_id = 'my-op-1'
            name = 'My Op 1'
            value_field = ConditionValueIntegerField()

        class MyChoice1(BaseConditionChoice):
            choice_id = 'my-choice'
            name = 'My Choice'
            operators = ConditionOperators([MyOperator1])

        choices = ConditionChoices([MyChoice1])
        field = ConditionsField(choices=choices)
        field.widget.condition_errors[0] = 'This is an error.'

        result = field.widget.get_context(
            'my_conditions',
            {
                'mode': 'any',
                'conditions': [
                    {
                        'choice': 'my-choice',
                        'op': 'my-op-1',
                        'value': 'my-value-1',
                    },
                ],
            },
            {
                'id': 'my-conditions',
            })

        rendered_rows = result['rendered_rows']
        self.assertEqual(len(rendered_rows), 1)

        rendered_row = rendered_rows[0]
        self.assertEqual(set(six.iterkeys(rendered_row)),
                         {'choice', 'operator', 'error'})
        self.assertHTMLEqual(
            rendered_row['choice'],
            '<select id="my-conditions_choice_0"'
            ' name="my_conditions_choice[0]">\n'
            '<option value="my-choice" selected="selected">'
            'My Choice</option>\n'
            '</select>')

        self.assertHTMLEqual(
            rendered_row['operator'],
            '<select id="my-conditions_operator_0"'
            ' name="my_conditions_operator[0]">\n'
            '<option value="my-op-1" selected="selected">'
            'My Op 1</option>\n'
            '</select>')

        self.assertEqual(rendered_row['error'], 'This is an error.')

        serialized_choices = result['serialized_choices']
        self.assertEqual(len(serialized_choices), 1)
        self.assertEqual(serialized_choices[0]['id'], 'my-choice')

        serialized_rows = result['serialized_rows']
        self.assertEqual(
            serialized_rows,
            [{
                'choiceID': 'my-choice',
                'operatorID': 'my-op-1',
                'valid': True,
                'value': 'my-value-1',
                'error': 'This is an error.',
            }])

    def test_render(self):
        """Testing ConditionsWidget.render"""
        class MyOperator(BaseConditionOperator):
            operator_id = 'my-op'
            name = 'My Op'
            value_field = ConditionValueIntegerField()

        class MyChoice(BaseConditionChoice):
            choice_id = 'my-choice'
            name = 'My Choice'
            operators = ConditionOperators([MyOperator])

        choices = ConditionChoices([MyChoice])
        field = ConditionsField(choices=choices)

        rendered = field.widget.render(
            'my_conditions',
            {
                'mode': 'any',
                'conditions': [
                    {
                        'choice': 'my-choice',
                        'op': 'my-op',
                        'value': 'my-value-1',
                    },
                ],
            },
            {
                'id': 'my-conditions',
            })

        self.assertIn('<div class="conditions-field" id="my-conditions">',
                      rendered)
        self.assertIn('<input type="hidden" name="my_conditions_last_id"'
                      ' value="1">',
                      rendered)
        self.assertRegexpMatches(
            rendered,
            '<option value="my-choice" selected(="selected")?>My Choice'
            '</option>')
        self.assertRegexpMatches(
            rendered,
            '<option value="my-op" selected(="selected")?>My Op</option>')
        self.assertIn('<span class="conditions-field-value"></span>',
                      rendered)
