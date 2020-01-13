"""Custom widgets for Django form fields.

This module contains widgets that correspond to fields provided in
:py:mod:`djblets.forms.fields`.
"""

from __future__ import unicode_literals

import copy
from contextlib import contextmanager

from django.forms import widgets
from django.forms.widgets import HiddenInput
from django.template.context import Context
from django.utils import six
from django.utils.html import format_html_join
from django.utils.six.moves import filter, range
from django.utils.translation import ugettext as _

from djblets.conditions import ConditionSet
from djblets.conditions.errors import (ConditionChoiceNotFoundError,
                                       ConditionOperatorNotFoundError)
from djblets.util.compat.django.template.loader import render_to_string


class ConditionsWidget(widgets.Widget):
    """A widget used to request a list of conditions from the user.

    This is used by :js:class:`~djblets.forms.fields.ConditionsField` to allow
    the user to specify a list of possible conditions, composed of choices,
    operators, and values.

    The conditions are displayed as rows of fields. Each row contains a
    ``<select>`` for the condition choice, operator choice, and a
    choice-provided field for a value.

    Additional conditions can be added by the user dynamically.

    Attributes:
        choices (djblets.conditions.choices.ConditionChoices):
            The condition choices for the field.

        mode_widget (django.forms.widgets.RadioSelect):
            The widget for selecting the mode.

        choice_widget (django.forms.widgets.Select):
            The widget for selecting choices. One of these will be rendered
            for every row.

        operator_widget (django.forms.widgets.Select):
            The widget for selecting operators. One of these will be
            rendered for every row.

        choice_kwargs (dict):
            Optional keyword arguments to pass to each
            :py:class:`~djblets.conditions.choices.BaseConditionChoice`
            constructor. This is useful for more advanced conditions that
            need additional data from the form.

            This can be updated dynamically by the form during initialization.
    """

    #: The name of the template used to render the widget.
    template_name = 'djblets_forms/conditions_widget.html'

    def __init__(self, choices, mode_widget, choice_widget, operator_widget,
                 choice_kwargs=None, attrs=None):
        """Initialize the widget.

        Args:
            choices (djblets.conditions.choices.ConditionChoices):
                The condition choices for the field.

            mode_widget (django.forms.widgets.RadioSelect):
                The widget for selecting the mode.

            choice_widget (django.forms.widgets.Select):
                The widget for selecting choices. One of these will be rendered
                for every row.

            operator_widget (django.forms.widgets.Select):
                The widget for selecting operators. One of these will be
                rendered for every row.

            choice_kwargs (dict):
                Optional keyword arguments to pass to each
                :py:class:`~djblets.conditions.choices.BaseConditionChoice`
                constructor. This is useful for more advanced conditions that
                need additional data from the form.

            attrs (dict, optional):
                Additional HTML element attributes for the widget.
        """
        super(ConditionsWidget, self).__init__(attrs=attrs)

        self.choices = choices
        self.mode_widget = mode_widget
        self.choice_widget = choice_widget
        self.operator_widget = operator_widget
        self.choice_kwargs = choice_kwargs
        self.condition_errors = {}

    @property
    def media(self):
        """Media needed for the widget.

        This is used by the form to return all CSS/JavaScript media that the
        page will need in order to render this widget and any widgets used
        in the condition value fields.

        Returns:
            django.forms.widgets.Media:
            The media to include on the path.
        """
        media = (widgets.Media() +
                 self.choice_widget.media +
                 self.operator_widget.media)

        choices = self.choices.get_choices(choice_kwargs=self.choice_kwargs)

        for choice in choices:
            default_value_field = choice.default_value_field

            if callable(default_value_field):
                default_value_field = default_value_field()

            if hasattr(default_value_field, 'widget'):
                media += default_value_field.widget.media

            for operator in choice.get_operators():
                if operator.has_custom_value_field:
                    if (operator.value_field and
                        hasattr(operator.value_field, 'widget')):
                        media += operator.value_field.widget.media

        return media

    def value_from_datadict(self, data, files, name):
        """Return a value for the field from a submitted form.

        This serializes the data POSTed for the form into a format that the
        field can use and validate.

        Args:
            data (django.http.request.QueryDict):
                The dictionary containing form data.

            files (django.http.request.QueryDict):
                The dictionary containing uploaded files.

            name (unicode):
                The field name for the value to load.

        Returns:
            object:
            The value from the form data.
        """
        try:
            last_id = int(data['%s_last_id' % name]) + 1
        except (KeyError, ValueError):
            last_id = 0

        conditions = []

        for i in range(last_id):
            choice_id = data.get('%s_choice[%s]' % (name, i))

            if choice_id is None:
                # There's no choice with this ID. It was probably deleted.
                continue

            operator_id = data.get('%s_operator[%s]' % (name, i))
            value_name = '%s_value[%s]' % (name, i)

            try:
                choice = self.choices.get_choice(
                    choice_id,
                    choice_kwargs=self.choice_kwargs)
                operator = choice.get_operator(operator_id)
                value_field = self._get_value_field(operator)

                if value_field is None:
                    value = None
                else:
                    value = value_field.get_from_form_data(
                        data, files, value_name)
            except (ConditionChoiceNotFoundError,
                    ConditionOperatorNotFoundError):
                value = data.get(value_name)

            conditions.append({
                'choice': choice_id,
                'op': operator_id,
                'value': value,
            })

        return {
            'mode': data.get('%s_mode' % name),
            'conditions': conditions,
        }

    def render(self, name, value, attrs=None):
        """Render the widget to HTML.

        This will serialize all the choices, operators, and existing
        conditions and render an HTML representation, along with setting up
        JavaScript support for configuring the conditions.

        Args:
            name (unicode):
                The base form field name of the widget.

            value (dict):
                The serialized condition set for the field.

            attrs (dict, optional):
                Additional HTML element attributes for the fields.

        Returns:
            django.utils.safestring.SafeText:
            The rendered HTML for the widget.
        """
        return render_to_string(self.template_name,
                                self.get_context(name, value, attrs))

    def get_context(self, name, value, attrs):
        """Return context for the widget.

        This will serialize all the choices, operators, and existing
        conditions needed to render the widget.

        Args:
            name (unicode):
                The base form field name of the widget.

            value (dict):
                The serialized condition set for the field.

            attrs (dict):
                Additional HTML element attributes for the fields.

        Returns:
            dict:
            The context data for the widget.
        """
        widget_attrs = self.build_attrs(attrs)
        widget_id = widget_attrs.get('id')
        rendered_rows = []
        rows = []

        # Render the mode radio buttons.
        mode_attrs = widget_attrs

        if widget_id:
            mode_attrs = dict(mode_attrs, id='%s_mode' % name)

        rendered_mode = self.mode_widget.render(
            name='%s_mode' % name,
            value=value.get('mode', ConditionSet.MODE_ALL),
            attrs=mode_attrs)

        for i, condition in enumerate(value['conditions']):
            choice_id = condition['choice']
            operator_id = condition['op']
            condition_value = condition.get('value')
            error = None

            # Try to load the necessary choice and operator.
            #
            # Since these may be dynamically registered, we need to take care
            # not to break or lose information at this stage if the choice or
            # operator is missing. We'll just show the raw data. It won't save,
            # but the user will at least get a suitable error.
            try:
                choice = self.choices.get_choice(
                    choice_id,
                    choice_kwargs=self.choice_kwargs)
                operator = choice.get_operator(operator_id)
                error = self.condition_errors.get(i)
            except ConditionChoiceNotFoundError:
                choice = None
                operator = None
                error = _('This choice no longer exists. You will need to '
                          'delete the condition in order to make changes.')
            except ConditionOperatorNotFoundError:
                operator = None
                error = _('This operator no longer exists. You will need to '
                          'delete the condition in order to make changes.')

            valid = (choice is not None and operator is not None)

            if not valid:
                # Set the dropdowns to be non-editable.
                widget_attrs = dict(widget_attrs, disabled='disabled')

            if choice is None:
                choices = ((choice_id, choice_id),)
            else:
                # Set this to empty so that it'll use the default for the
                # field.
                choices = ()

            if operator is None:
                operators = ((operator_id, operator_id),)
            else:
                # Build the operators specific to this choice.
                operators = (
                    (operator.operator_id, operator.name)
                    for operator in choice.operators
                )

            # Render the list of condition choices.
            choice_name = '%s_choice[%s]' % (name, i)
            choice_attrs = widget_attrs

            if widget_id:
                choice_attrs = dict(choice_attrs,
                                    id='%s_choice_%s' % (widget_id, i))

            with self._add_widget_choices(self.choice_widget, choices):
                rendered_choice = self.choice_widget.render(
                    name=choice_name,
                    value=choice_id,
                    attrs=choice_attrs)

            # Render the list of operators.
            operator_name = '%s_operator[%s]' % (name, i)
            operator_attrs = widget_attrs

            if widget_id:
                operator_attrs = dict(operator_attrs,
                                      id='%s_operator_%s' % (widget_id, i))

            with self._add_widget_choices(self.operator_widget, operators):
                rendered_operator = self.operator_widget.render(
                    name=operator_name,
                    value=operator_id,
                    attrs=operator_attrs)

            if valid:
                value_field = self._get_value_field(operator)

                if value_field is not None:
                    condition_value = \
                        value_field.prepare_value_for_widget(condition_value)
            else:
                # Prepare a hidden input with the values we want to retain,
                # as part of the condition. This is needed so that we can
                # disable the form fields without losing that state when
                # submitting the form (since browsers don't send along data
                # from disabled form fields).
                hidden = widgets.HiddenInput()
                rendered_choice += hidden.render(name=choice_name,
                                                 value=choice_id)
                rendered_operator += hidden.render(name=operator_name,
                                                   value=operator_id)

            # Render the value widget.
            value_attrs = widget_attrs

            if widget_id:
                value_attrs = dict(value_attrs,
                                   id='%s_value_%s' % (widget_id, i))

            # Store the information for the template.
            rendered_rows.append({
                'choice': rendered_choice,
                'operator': rendered_operator,
                'error': error,
            })

            row_data = {
                'choiceID': choice_id,
                'operatorID': operator_id,
                'value': condition_value,
                'valid': valid,
            }

            if error:
                row_data['error'] = error

            rows.append(row_data)

        return {
            'field_id': widget_id,
            'field_name': name,
            'rendered_mode': rendered_mode,
            'rendered_rows': rendered_rows,
            'serialized_choices': [
                self._serialize_choice(temp_choice)
                for temp_choice in self.choices.get_choices(
                    choice_kwargs=self.choice_kwargs)
            ],
            'serialized_rows': rows,
        }

    def _serialize_choice(self, choice):
        """Return a serialized choice for the widget.

        This contains information needed by the JavaScript UI to render the
        choice and its related objects. It's not equivalent to the standard
        serialized version of a choice (which is meant for state storage and
        not widget data).

        Args:
            choice (djblets.conditions.choices.BaseConditionChoice):
                The choice to serialize.

        Returns:
            dict:
            The serialized choice.
        """
        return {
            'id': choice.choice_id,
            'name': choice.name,
            'valueField': self._serialize_value_field(
                self._normalize_value_field(choice.default_value_field)),
            'operators': [
                self._serialize_operator(operator)
                for operator in choice.get_operators()
            ]
        }

    def _serialize_operator(self, operator):
        """Return a serialized operator for the widget.

        This contains information needed by the JavaScript UI to render the
        operator and its related objects. It's not equivalent to the standard
        serialized version of an operator (which is meant for state storage and
        not widget data).

        Args:
            operator (djblets.conditions.operators.BaseConditionOperator):
                The operator to serialize.

        Returns:
            dict:
            The serialized operator.
        """
        data = {
            'id': operator.operator_id,
            'name': operator.name,
            'useValue': True,
        }

        value_field = self._get_value_field(operator)

        if value_field is None:
            # This operator doesn't want any kind of value field.
            data['useValue'] = False
        elif operator.has_custom_value_field:
            # This operator has a field that differs from the default for the
            # choice, so specify it.
            data['valueField'] = self._serialize_value_field(value_field)

        return data

    def _serialize_value_field(self, value_field):
        """Return a serialized value field for the widget.

        The serialized contents will be used to create a JavaScript widget
        for the field.

        Args:
            value_field (djblets.conditions.values.BaseConditionValueField):
                The value field to serialize.

        Returns:
            dict:
            Serialized state for the value field.
        """
        if value_field:
            return {
                'model': {
                    'className': value_field.js_model_class,
                    'data': value_field.get_js_model_data(),
                },
                'view': {
                    'className': value_field.js_view_class,
                    'data': value_field.get_js_view_data(),
                },
            }
        else:
            return {}

    def _get_value_field(self, operator):
        """Return the normalized value field for an operator.

        If the operator's value field is a function, the resulting value field
        from calling that function will be returned. Otherwise, the value field
        will be returned directly.

        Args:
            operator (djblets.conditions.operators.BaseConditionOperator):
                The operator containing the value field.

        Returns:
            djblets.conditions.values.BaseConditionValueField:
            The resulting value field.
        """
        return self._normalize_value_field(operator.value_field)

    def _normalize_value_field(self, value_field):
        """Normalize and return a value field.

        If ``value_field`` is a function, the resulting value field from
        calling that function will be returned. Otherwise, ``value_field``
        will be returned directly.

        Args:
            value_field (object):
            A :py:class:`~djblets.conditions.values.BaseConditionValueField`
            or a function returning one.

        Returns:
            djblets.conditions.values.BaseConditionValueField:
            The resulting value field.
        """
        if six.callable(value_field):
            value_field = value_field()

        return value_field

    @contextmanager
    def _add_widget_choices(self, widget, choices):
        """Temporarily add choices to a widget.

        This temporary appends the provided list of choices to a widget's
        existing list, allowing some additional choices to be there for
        rendering purposes. After the caller's logic is done, the list of
        choices will be reset.

        Args:
            widget (django.forms.fields.widgets.ChoiceInput):
                The choice widget.

            choices (list):
                The list of choices to temporarily append.
        """
        old_choices = widget.choices
        widget.choices = widget.choices + list(choices)

        yield

        widget.choices = old_choices

    def __deepcopy__(self, memo):
        """Return a deep copy of the widget.

        This will return a deep copy of this widget and all subwidgets, so that
        a particular form instance can easily manipulate state without
        affecting other instances.

        Only the state that may be manipulated by an instance will be deep
        copied.

        Args:
            memo (dict):
                The memo dictionary used to track IDs to objects.

        Returns:
            ConditionsWidget:
            A deep copy of this widget's instance.
        """
        obj = super(ConditionsWidget, self).__deepcopy__(memo)
        obj.mode_widget = copy.deepcopy(self.mode_widget, memo)
        obj.choice_widget = copy.deepcopy(self.choice_widget, memo)
        obj.operator_widget = copy.deepcopy(self.operator_widget, memo)
        obj.condition_errors = copy.deepcopy(self.condition_errors, memo)
        obj.choice_kwargs = self.choice_kwargs.copy()

        return obj


class CopyableTextInput(widgets.TextInput):
    """A TextInput widget that renders a link to copy its contents."""

    template_name = 'djblets_forms/copyable_text_input.html'

    def render(self, name, value, attrs=None):
        """Render the widget.

        Args:
            name (unicode):
                The name of the widget.

            value (unicode):
                The value of the widget.

            attrs (dict):
                The attributes of the widget.

        Returns:
            django.utils.safestring.SafeText:
            The rendered widget.
        """
        field = super(CopyableTextInput, self).render(name, value, attrs)

        return render_to_string(
            self.template_name,
            {
                'field': field,
                'id': attrs['id'],
            })


class ListEditWidget(widgets.Widget):
    """A widget for editing a list of separated values.

    .. note: The ``djblets-forms`` CSS and JS bundles are required to use this
             widget.
    """

    template_name = 'djblets_forms/list_edit_widget.html'

    def __init__(self, attrs=None, sep=','):
        """Initialize the widget.

        Args:
            attrs (dict, optional):
                The attributes of the ``<input>`` elements.

            sep (unicode, optional):
                The item separator.
        """
        super(ListEditWidget, self).__init__(attrs)

        self._sep = sep

    def render(self, name, value, attrs=None):
        """Render the widget.

        Args:
            name (unicode):
                The field name.

            value (unicode):
                The field value.

            attrs (dict, optional):
                Additional attributes.

        Returns:
            django.utils.safestring.SafeText:
            The rendered widget.
        """
        attrs = self.build_attrs(attrs)
        id_ = attrs.pop('id')

        if 'class' in attrs:
            attrs['class'] += ' djblets-c-list-edit-widget__input'
        else:
            attrs['class'] = 'djblets-c-list-edit-widget__input'

        value = value or ''
        value_list = list(
            filter(len, (item.strip() for item in value.split(self._sep)))
        )

        return render_to_string(
            self.template_name,
            {
                'name': name,
                'value': value,
                'attrs': format_html_join('', ' {0}="{1}"',
                                          sorted(six.iteritems(attrs))),
                'id': id_,
                'remove_text': _('Remove this item.'),
                'sep': self._sep,
                'value_list': value_list,
            })

    def id_for_label(self, id_):
        """Return the main ID to use for this widget.

        This intentionally returns ``None`` since there are multiple fields
        under this widget.

        Args:
            id_ (unicode):
                The ID of the element.

        Returns:
            unicode:
            ``None`` so that no ``for=`` attribute is rendered on the label.
        """
        return None


class RelatedObjectWidget(HiddenInput):
    """A base class form widget that lets people select one or more objects.

    This is a base class. Extended classes must define their own render()
    method, to render their own widget with their own data.

    This should be used with relatedObjectSelectorView.es6.js, which extends
    a Backbone view to display data.
    """

    # We inherit from HiddenInput in order for the superclass to render a
    # hidden <input> element, but the Djblets siteconfig field template we use
    # doesn't display labels, help text, errors etc. when ``is_hidden`` is
    # True. Setting it to False still gives us the rendering and data handling
    # we want but renders fieldset fields correctly.
    is_hidden = False

    def __init__(self, multivalued=True):
        """Initialize the RelatedObjectWidget.

        Args:
            local_site_name (unicode, optional):
                The name of the LocalSite where the widget is being rendered.

            multivalued (bool, optional):
                Whether or not the widget should allow selecting multiple
                values.
        """
        super(RelatedObjectWidget, self).__init__()

        self.multivalued = multivalued
