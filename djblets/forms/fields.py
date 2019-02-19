"""Additional fields for Django forms."""

from __future__ import unicode_literals

import logging

from django import forms
from django.utils import six
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _, ugettext
import pytz

from djblets.conditions.conditions import ConditionSet
from djblets.conditions.errors import (ConditionChoiceNotFoundError,
                                       ConditionOperatorNotFoundError,
                                       InvalidConditionModeError,
                                       InvalidConditionValueError)
from djblets.forms.widgets import ConditionsWidget


TIMEZONE_CHOICES = tuple(zip(pytz.common_timezones, pytz.common_timezones))


class TimeZoneField(forms.ChoiceField):
    """A form field that only allows pytz common timezones as the choices."""

    def __init__(self, choices=TIMEZONE_CHOICES, *args, **kwargs):
        super(TimeZoneField, self).__init__(choices, *args, **kwargs)


class ConditionsField(forms.Field):
    """A form field for customizing conditions required for an operation.

    This field is used for defining conditions under which something should
    be processed or run. It takes a condition choice registry (subclass of
    :py:class:`~djblets.conditions.choices.BaseConditionChoiceRegistry`), which
    defines all the possible condition choices, each containing possible
    operators for that choice (such as "is," "is not," "starts with," etc.) and
    possible fields for inputting values.

    Attributes:
        choices (djblets.conditions.choices.ConditionChoices):
            The condition choies for the field.

        choice_kwargs (dict):
            Optional keyword arguments to pass to each
            :py:class:`~djblets.conditions.choices.BaseConditionChoice`
            constructor. This is useful for more advanced conditions that
            need additional data from the form.

            This can be updated dynamically by the form during initialization.
    """

    widget = ConditionsWidget

    default_error_messages = {
        'condition_errors': _('There was an error with one of your '
                              'conditions.'),
        'invalid_mode': _('Must select either "All" or "Any".'),
        'value_required': _('A value is required for this condition.'),
    }

    def __init__(self, choices, choice_kwargs=None, *args, **kwargs):
        """Initialize the field.

        Args:
            choices (djblets.conditions.choices.BaseConditionChoicesRegistry):
                The registry of choices available for the conditions.

                This should either be a class, or a function that returns
                an instance. Note that the class will be constructed or the
                function called when the field is first instantiated.

            choice_kwargs (dict, optional):
                Optional keyword arguments to pass to each
                :py:class:`~djblets.conditions.choices.BaseConditionChoice`
                constructor. This is useful for more advanced conditions that
                need additional data from the form.

            *args (tuple):
                Extra positional arguments for the field.

            **kwargs (dict):
                Extra keyword arguments for the field.
        """
        if callable(choices):
            choices = choices()

        for choice in choices:
            if choice.operators is None or len(choice.operators) == 0:
                logging.error('%s must define a non-empty "operators" '
                              'attribute.',
                              choice.__name__)

                raise ValueError(
                    _('%s must define a non-empty "operators" attribute.')
                    % choice.__name__)

        widget_cls = kwargs.get('widget', self.widget)

        self.choices = choices

        self.mode_field = forms.ChoiceField(
            required=True,
            choices=(
                (ConditionSet.MODE_ALWAYS,
                 mark_safe(_('Always match'))),
                (ConditionSet.MODE_ALL,
                 mark_safe(_('Match <b>all</b> of the following:'))),
                (ConditionSet.MODE_ANY,
                 mark_safe(_('Match <b>any</b> of the following:')))
            ),
            widget=forms.widgets.RadioSelect())

        self.choice_field = forms.ChoiceField(
            required=True,
            choices=(
                (choice.choice_id, choice.name)
                for choice in choices
            ))

        self.operator_field = forms.ChoiceField(required=True)

        super(ConditionsField, self).__init__(
            widget=widget_cls(choices=choices,
                              mode_widget=self.mode_field.widget,
                              choice_widget=self.choice_field.widget,
                              operator_widget=self.operator_field.widget,
                              choice_kwargs=choice_kwargs or {}),
            *args, **kwargs)

    @property
    def choice_kwargs(self):
        """The keyword arguments passed to ConditionChoice functions."""
        return self.widget.choice_kwargs

    @choice_kwargs.setter
    def choice_kwargs(self, value):
        """The keyword arguments passed to ConditionChoice functions.

        Args:
            value (dict):
                The new condition choices value to set.
        """
        self.widget.choice_kwargs = value

    def prepare_value(self, data):
        """Prepare the value for loading into the field.

        This will handle both a loaded
        :py:class:`~djblets.conditions.conditions.ConditionSet` instance or a
        serialized version of one (used when the form is saved), allowing
        either to be fed in.

        Args:
            data (object):
                The data as either a
                :py:class:`~djblets.conditions.conditions.ConditionSet`
                instance or a serialized dictionary.

        Returns:
            dict:
            The resulting serialized condition set for the widget.

        Raises:
            ValueError:
                The value provided is not valid for the widget.
        """
        if isinstance(data, ConditionSet):
            data = data.serialize()
        elif data is None:
            data = {
                'mode': ConditionSet.DEFAULT_MODE,
                'conditions': [],
            }

        if not isinstance(data, dict):
            raise ValueError(
                ugettext('%r is not a valid value for a %s')
                % (data, self.__class__.__name__))

        return data

    def to_python(self, value):
        """Parse and return conditions from the field's data.

        This takes the serialized values provided by the field's widget,
        ensures they're valid, and returns a list of the resulting conditions.

        Args:
            value (dict):
                The raw form data, as provided by the widget.

        Returns:
            djblets.conditions.conditions.ConditionSet:
            The resulting condition set from the form.
        """
        if not value:
            # Let validate() handle this. It will be run by clean() after this
            # method returns.
            return None

        try:
            condition_set = ConditionSet.deserialize(
                self.choices,
                value,
                choice_kwargs=self.widget.choice_kwargs)
        except InvalidConditionModeError as e:
            raise forms.ValidationError(six.text_type(e),
                                        code='invalid_mode')
        except (ConditionChoiceNotFoundError,
                ConditionOperatorNotFoundError,
                InvalidConditionValueError) as e:
            if getattr(e, 'code', None) == 'required':
                self.widget.condition_errors[e.condition_index] = \
                    self.error_messages['value_required']
            else:
                self.widget.condition_errors[e.condition_index] = \
                    six.text_type(e)

            raise forms.ValidationError(
                self.error_messages['condition_errors'],
                code='condition_errors')

        return condition_set
