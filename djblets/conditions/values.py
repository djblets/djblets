"""Base support and standard value field wrappers for conditions."""

from __future__ import unicode_literals

from django import forms

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
                The Django form field instance for the value.
        """
        super(ConditionValueFormField, self).__init__()

        self.field = field

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
