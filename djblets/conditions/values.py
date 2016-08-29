"""Base support and standard value field wrappers for conditions."""

from __future__ import unicode_literals

import re

from django import forms
from django.utils.translation import ugettext_lazy as _

from djblets.conditions.errors import InvalidConditionValueError


class BaseConditionValueField(object):
    """Base class for a field for editing and representing condition values.

    This is used to provide a field in the UI that can be used for editing a
    condition value. It's responsible for rendering the field, preparing
    data for the field, retrieving the data from the HTML form data, and
    handling JSON-safe serialization/deserialization of values.

    Subclasses can specify custom logic for all these operations, and can
    specify the JavaScript counterparts for the class used to edit the values.
    """

    #: The JavaScript model class for representing field state.
    #:
    #: This is instantiated on the web UI and is used to store any model
    #: data provided by :py:meth:`get_js_model_data`.
    #:
    #: The default is a simple model that just stores the model data as
    #: attributes.
    js_model_class = 'Djblets.Forms.ConditionValueField'

    #: The JavaScript view class for editing fields.
    #:
    #: This is instantiated on the web UI and is used to provide an editor
    #: for the condition's value.
    #:
    #: It's passed any options that are returned from
    #: :py:meth:`get_js_model_data`.
    js_view_class = None

    def serialize_value(self, value):
        """Serialize a Python object into a JSON-compatible serialized form.

        This is responsible for taking a Python value/object of some sort
        (string, list, or anything more complex) and returning a
        JSON-compatible form for serialization.

        By default, this returns the value as-is.

        Args:
            value (object):
                The value to serialize.

        Returns:
            object:
            The JSON-compatible serialized value.
        """
        return value

    def deserialize_value(self, serialized_value):
        """Deserialize a value back into a Python object.

        This is responsible for taking a value serialized by
        :py:meth:`serialize_value` and returning a suitable Python
        object/value.

        By default, this returns the value as-is.

        Args:
            serialized_value (object):
                The serialized value to deserialize.

        Returns:
            object:
            The deserialized value.

        Raises:
            djblets.conditions.errors.InvalidConditionValueError:
                Error deserializing or validating the data.
        """
        return serialized_value

    def get_from_form_data(self, data, files, name):
        """Return a value from a form data dictionary.

        This attempts to return the value for a condition from Django form
        data. It's passed a dictionary of data, uploaded files, and the name
        of the appropriate value field.

        Subclasses can override this to normalize the value before returning.

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
        return data.get(name, None)

    def prepare_value_for_widget(self, value):
        """Return a value suitable for use in the widget.

        The value will be passed to the widget's JavaScript UI. It can be
        used in special cases where a Python object needs to be converted
        to another form in order to work properly client-side.

        By default, the value is returned as-is.

        Args:
            value (object):
                The value to prepare for the widget.

        Returns:
            object:
            The value prepared for the widget.
        """
        return value

    def get_js_model_data(self):
        """Return data for the JavaScript model for this field.

        The returned data will be set as attributes on the Backbone model
        pointed to by :py:attr:`js_model_class`.

        By default, this includes the rendered HTML as ``fieldHTML``, which
        should generally be provided (but is not required, depending on the
        field).

        Returns:
            dict:
            The model data. This must be serializable as JSON.
        """
        return {
            'fieldHTML': self.render_html(),
        }

    def get_js_view_data(self):
        """Return data for the JavaScript view for this field.

        The returned data will be set as options on the Backbone view pointed
        to by :py:attr:`js_view_class`.

        This is empty by default.

        Returns:
            dict:
            The view data. This must be serializable as JSON.
        """
        return {}

    def render_html(self):
        """Return rendered HTML for the field.

        The rendered HTML will be inserted dynamically by the JavaScript UI.

        This must be implemented by subclasses.

        Returns:
            unicode:
            The rendered HTML for the field. This does not need to be marked as
            safe (but can be), as it will be passed in as an escaped JavaScript
            string.
        """
        raise NotImplementedError


class ConditionValueFormField(BaseConditionValueField):
    """Condition value wrapper for HTML form fields.

    This allows the usage of standard HTML form fields (through Django's
    :py:mod:`django.forms` module) for rendering and accepting condition
    values.

    Callers simply need to instantiate the class along with a form field.

    The rendered field must support setting and getting a ``value``
    attribute on the DOM element, like a standard HTML form field.

    Example:
        value_field = ConditionValueFormField(
            forms.ModelMultipleChoiceField(queryset=MyModel.objects.all()))
    """

    js_model_class = 'Djblets.Forms.ConditionValueField'
    js_view_class = 'Djblets.Forms.ConditionValueFormFieldView'

    def __init__(self, field):
        """Initialize the value field.

        Args:
            field (django.forms.fields.Field):
                The Django form field instance for the value. This may also
                be a callable that returns a field.
        """
        super(ConditionValueFormField, self).__init__()

        self.field = field

    @property
    def field(self):
        """The form field to use for the value.

        This will always return a :py:class:`~django.forms.fields.Field`,
        but can be given a callable that returns a field when set.
        """
        if callable(self._field):
            self._field = self._field()

        return self._field

    # Note that the docstring will be inherited from the field property.
    @field.setter
    def field(self, field):
        self._field = field

    def serialize_value(self, value):
        """Serialize a Python object into a JSON-compatible serialized form.

        This is responsible for taking a Python value/object of some sort
        (string, list, or anything more complex) and returning a
        JSON-compatible form for serialization. It will use the form field
        to do this (through :py:meth:`Field.prepare_value()
        <django.forms.fields.Field.prepare_value>`).

        Args:
            value (object):
                The value to serialize.

        Returns:
            object:
            The JSON-compatible serialized value.
        """
        return self.field.prepare_value(value)

    def deserialize_value(self, value_data):
        """Deserialize a value back into a Python object.

        This is responsible for taking a value serialized by
        :py:meth:`serialize_value` and returning a suitable Python
        object/value. It will use the form field to do this (through
        :py:meth:`Field.clean() <django.forms.fields.Field.clean>`).

        By default, this returns the value as-is.

        Args:
            serialized_value (object):
                The serialized value to deserialize.

        Returns:
            object:
            The deserialized value.

        Raises:
            djblets.conditions.errors.InvalidConditionValueError:
                Error deserializing or validating the data.
        """
        try:
            return self.field.clean(value_data)
        except forms.ValidationError as e:
            raise InvalidConditionValueError('; '.join(e.messages),
                                             code=e.code)

    def get_from_form_data(self, data, files, name):
        """Return a value from a form data dictionary.

        This attempts to return the value for a condition from Django form
        data. It's passed a dictionary of data, uploaded files, and the name
        of the appropriate value field. It will use the form field's widget to
        do this (through :py:meth:`Widget.value_from_datadict
        <django.forms.widgets.Widget.value_from_datadict>`).

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
        return self.field.widget.value_from_datadict(data, files, name)

    def render_html(self):
        """Return rendered HTML for the field.

        The rendered HTML will be generated by the widget for the field,
        and will be dynamically inserted by the JavaScript UI.

        Returns:
            unicode:
            The rendered HTML for the field.
        """
        # The name is a placeholder, and will be updated by the JavaScript.
        # However, we must have it for render.
        return self.field.widget.render(name='XXX', value=None)


class ConditionValueBooleanField(ConditionValueFormField):
    """Condition value wrapper for boolean form fields.

    This is a convenience for condition values that want to use a
    :py:class:`~django.forms.fields.BooleanField`. It accepts the same
    keyword arguments in the constructor that the field itself accepts.

    It also specially serializes the value to a string for use in the
    JavaScript widget.

    Example:
        value_field = ConditionValueBooleanField(initial=True)
    """

    def __init__(self, **field_kwargs):
        """Initialize the value field.

        Args:
            **field_kwargs (dict):
                Keyword arguments to pass to the
                :py:class:`~django.forms.fields.BooleanField` constructor.
        """
        widget = field_kwargs.pop('widget', None)

        if not widget:
            widget = forms.widgets.Select(choices=(
                (True, _('True')),
                (False, _('False')),
            ))

        super(ConditionValueBooleanField, self).__init__(
            field=forms.BooleanField(
                required=False,
                widget=widget,
                **field_kwargs))

    def prepare_value_for_widget(self, value):
        """Return a value suitable for use in the widget.

        This will convert a boolean value to a string, so that it can be
        properly matched against the string choices for the select box.

        Args:
            value (bool):
                The value to prepare for the widget.

        Returns:
            unicode:
            The string value for the widget.
        """
        if value:
            return 'True'
        else:
            return 'False'


class ConditionValueCharField(ConditionValueFormField):
    """Condition value wrapper for single-line text form fields.

    This is a convenience for condition values that want to use a
    :py:class:`~django.forms.fields.CharField`. It accepts the same keyword
    arguments in the constructor that the field itself accepts.

    Example:
        value_field = ConditionValueCharField(max_length=100)
    """

    def __init__(self, **field_kwargs):
        """Initialize the value field.

        Args:
            **field_kwargs (dict):
                Keyword arguments to pass to the
                :py:class:`~django.forms.fields.CharField` constructor.
        """
        super(ConditionValueCharField, self).__init__(
            field=forms.CharField(**field_kwargs))


class ConditionValueIntegerField(ConditionValueFormField):
    """Condition value wrapper for integer form fields.

    This is a convenience for condition values that want to use a
    :py:class:`~django.forms.fields.IntegerField`. It accepts the same
    keyword arguments in the constructor that the field itself accepts.

    Example:
        value_field = ConditionValueIntegerField(min_value=0, max_value=100)
    """

    def __init__(self, **field_kwargs):
        """Initialize the value field.

        Args:
            **field_kwargs (dict):
                Keyword arguments to pass to the
                :py:class:`~django.forms.fields.IntegerField` constructor.
        """
        super(ConditionValueIntegerField, self).__init__(
            field=forms.IntegerField(**field_kwargs))


class ConditionValueModelField(ConditionValueFormField):
    """Condition value wrapper for single model form fields.

    This is a convenience for condition values that want to use a
    :py:class:`~django.forms.fields.ModelChoiceField`. It accepts the same
    keyword arguments in the constructor that the field itself accepts.

    Unlike the standard field, the provided queryset can be a callable that
    returns a queryset.

    Example:
        value_field = ConditionValueModelField(queryset=MyObject.objects.all())
    """

    def __init__(self, queryset, **field_kwargs):
        """Initialize the value field.

        Args:
            queryset (django.db.models.query.QuerySet):
                The queryset used for the field. This may also be a callable
                that returns a queryset.

            **field_kwargs (dict):
                Keyword arguments to pass to the
                :py:class:`~django.forms.fields.ModelChoiceField` constructor.
        """
        def _build_field():
            if callable(queryset):
                qs = queryset()
            else:
                qs = queryset

            empty_label = field_kwargs.pop('empty_label', None)

            return forms.ModelChoiceField(queryset=qs,
                                          empty_label=empty_label,
                                          **field_kwargs)

        super(ConditionValueModelField, self).__init__(field=_build_field)


class ConditionValueMultipleModelField(ConditionValueFormField):
    """Condition value wrapper for multiple model form fields.

    This is a convenience for condition values that want to use a
    :py:class:`~django.forms.fields.ModelMutipleChoiceField`. It accepts the
    same keyword arguments in the constructor that the field itself accepts.

    Unlike the standard field, the provided queryset can be a callable that
    returns a queryset.

    Example:
        value_field = ConditionValueMultipleModelField(
            queryset=MyObject.objects.all())
    """

    def __init__(self, queryset, **field_kwargs):
        """Initialize the value field.

        Args:
            queryset (django.db.models.query.QuerySet):
                The queryset used for the field. This may also be a callable
                that returns a queryset.

            **field_kwargs (dict):
                Keyword arguments to pass to the
                :py:class:`~django.forms.fields.ModelChoiceField` constructor.
        """
        def _build_field():
            if callable(queryset):
                qs = queryset()
            else:
                qs = queryset

            return forms.ModelMultipleChoiceField(queryset=qs, **field_kwargs)

        super(ConditionValueMultipleModelField, self).__init__(
            field=_build_field)


class ConditionValueRegexField(ConditionValueCharField):
    """Condition value for fields that accept regexes.

    This value accepts and validates regex patterns entered into the field.

    Example:
        value_field = ConditionValueRegexField()
    """

    def serialize_value(self, value):
        """Serialize a compiled regex into a string.

        Args:
            value (object):
                The value to serialize.

        Returns:
            object:
            The JSON-compatible serialized value.
        """
        return value.pattern

    def deserialize_value(self, value_data):
        """Deserialize a regex pattern string into a compiled regex.

        Args:
            value_data (unicode):
                The serialized regex pattern to compile.

        Returns:
            object:
            The deserialized value.

        Raises:
            djblets.conditions.errors.InvalidConditionValueError:
                The regex could not be compiled.
        """
        try:
            return re.compile(value_data, re.UNICODE)
        except re.error as e:
            raise InvalidConditionValueError(
                'Your regex pattern had an error: %s' % e)
