"""Base support and standard value field wrappers for conditions."""

from __future__ import annotations

import re
from typing import (Any, Callable, ClassVar, Dict, Generic, Optional,
                    Sequence, TYPE_CHECKING, Union, cast)

from django import forms
from django.db.models import Model, QuerySet
from django.utils.translation import gettext_lazy as _
from typing_extensions import TypeAlias, TypeVar

from djblets.conditions.errors import InvalidConditionValueError
from djblets.util.typing import JSONDict, JSONValue

if TYPE_CHECKING:
    from django.forms.utils import _DataT, _FilesT
    from django.utils.safestring import SafeString


_T = TypeVar('_T',
             bound=Any,
             default=Any)
_ModelT = TypeVar('_ModelT',
                  bound=Model,
                  default=Model)


#: Type for a Field or a function that returns a Field.
#:
#: Version Added:
#:     5.3
FieldOrCallable: TypeAlias = Union[
    forms.Field,
    Callable[[], forms.Field],
]


#: Type for a QuerySet or a function that returns a QuerySet.
#:
#: Version Added:
#:     5.3
QuerySetOrCallable: TypeAlias = Union[
    QuerySet[_ModelT],
    Callable[[], QuerySet[_ModelT]],
]


#: Type for a dictionary used to cache common computable state for values.
#:
#: Version Added:
#:     5.3
ValueStateCache: TypeAlias = Dict[str, Any]


class BaseConditionValueField(Generic[_T]):
    """Base class for a field for editing and representing condition values.

    This is used to provide a field in the UI that can be used for editing a
    condition value. It's responsible for rendering the field, preparing
    data for the field, retrieving the data from the HTML form data, and
    handling JSON-safe serialization/deserialization of values.

    Subclasses can specify custom logic for all these operations, and can
    specify the JavaScript counterparts for the class used to edit the values.

    Version Changed:
        5.3:
        * Added support for Python type hints.
        * This class is now generic. Subclasses should specify a type when
          subclassing. It will default to :py:class:`typing.Any`.
    """

    #: The JavaScript model class for representing field state.
    #:
    #: This is instantiated on the web UI and is used to store any model
    #: data provided by :py:meth:`get_js_model_data`.
    #:
    #: The default is a simple model that just stores the model data as
    #: attributes.
    js_model_class: ClassVar[Optional[str]] = \
        'Djblets.Forms.ConditionValueField'

    #: The JavaScript view class for editing fields.
    #:
    #: This is instantiated on the web UI and is used to provide an editor
    #: for the condition's value.
    #:
    #: It's passed any options that are returned from
    #: :py:meth:`get_js_model_data`.
    js_view_class: ClassVar[Optional[str]] = None

    def serialize_value(
        self,
        value: _T,
    ) -> JSONValue:
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
        return cast(JSONValue, value)

    def deserialize_value(
        self,
        serialized_value: JSONValue,
    ) -> _T:
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
        return cast(_T, serialized_value)

    def get_from_form_data(
        self,
        data: _DataT,
        files: _FilesT,
        name: str,
    ) -> Optional[str]:
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

            name (str):
                The field name for the value to load.

        Returns:
            object:
            The value from the form data.
        """
        return data.get(name, None)

    def prepare_value_for_widget(
        self,
        value: _T,
    ) -> JSONValue:
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

    def get_js_model_data(self) -> JSONDict:
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

    def get_js_view_data(self) -> JSONDict:
        """Return data for the JavaScript view for this field.

        The returned data will be set as options on the Backbone view pointed
        to by :py:attr:`js_view_class`.

        This is empty by default.

        Returns:
            dict:
            The view data. This must be serializable as JSON.
        """
        return {}

    def render_html(self) -> SafeString:
        """Return rendered HTML for the field.

        The rendered HTML will be inserted dynamically by the JavaScript UI.

        This must be implemented by subclasses.

        Returns:
            django.utils.safestring.SafeString:
            The rendered HTML for the field. This does not need to be marked as
            safe (but can be), as it will be passed in as an escaped JavaScript
            string.
        """
        raise NotImplementedError


class ConditionValueFormField(BaseConditionValueField[_T]):
    """Condition value wrapper for HTML form fields.

    This allows the usage of standard HTML form fields (through Django's
    :py:mod:`django.forms` module) for rendering and accepting condition
    values.

    Callers simply need to instantiate the class along with a form field.

    The rendered field must support setting and getting a ``value``
    attribute on the DOM element, like a standard HTML form field.

    Version Changed:
        5.3:
        * Added support for Python type hints.
        * This class is now generic. Subclasses or instances should specify a
          type when subclassing. It will default to :py:class:`typing.Any`.

    Example:
        .. code-block:: python

           value_field = ConditionValueFormField[str](forms.SlugField)
    """

    js_model_class = 'Djblets.Forms.ConditionValueField'
    js_view_class = 'Djblets.Forms.ConditionValueFormFieldView'

    ######################
    # Instance variables #
    ######################

    #: The Django form field instance for the value.
    #:
    #: Type:
    #:     django.forms.fields.Field or callable
    _field: FieldOrCallable

    def __init__(
        self,
        field: FieldOrCallable,
    ) -> None:
        """Initialize the value field.

        Args:
            field (django.forms.fields.Field):
                The Django form field instance for the value. This may also
                be a callable that returns a field.
        """
        super().__init__()

        # NOTE: Ideally we wouldn't have to ignore the type here. The reason
        #       is that (as of June 18, 2023), mypy does not allow different
        #       types for getters and setters.
        #
        #       Since consumers are unlikely to actually set this property,
        #       this is less intrusive than having to worry about results on
        #       access.
        #
        #       See https://github.com/python/mypy/issues/3004
        self.field = field  # type: ignore

    @property
    def field(self) -> forms.Field:
        """The form field to use for the value.

        This will always return a :py:class:`~django.forms.fields.Field`,
        but can be given a callable that returns a field when set.
        """
        if callable(self._field):
            self._field = self._field()

        return self._field

    # Note that the docstring will be inherited from the field property.
    @field.setter
    def field(
        self,
        field: FieldOrCallable,
    ) -> None:
        self._field = field

    def serialize_value(
        self,
        value: _T,
    ) -> JSONValue:
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

    def deserialize_value(
        self,
        serialized_value: JSONValue,
    ) -> _T:
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
            return self.field.clean(serialized_value)
        except forms.ValidationError as e:
            raise InvalidConditionValueError('; '.join(e.messages),
                                             code=e.code)

    def get_from_form_data(
        self,
        data: _DataT,
        files: _FilesT,
        name: str,
    ) -> Optional[str]:
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

            name (str):
                The field name for the value to load.

        Returns:
            object:
            The value from the form data.
        """
        return self.field.widget.value_from_datadict(data, files, name)

    def render_html(self) -> SafeString:
        """Return rendered HTML for the field.

        The rendered HTML will be generated by the widget for the field,
        and will be dynamically inserted by the JavaScript UI.

        Returns:
            django.utils.safestring.SafeString:
            The rendered HTML for the field.
        """
        # The name is a placeholder, and will be updated by the JavaScript.
        # However, we must have it for render.
        return self.field.widget.render(name='XXX', value=None)


class ConditionValueBooleanField(ConditionValueFormField[bool]):
    """Condition value wrapper for boolean form fields.

    This is a convenience for condition values that want to use a
    :py:class:`~django.forms.fields.BooleanField`. It accepts the same
    keyword arguments in the constructor that the field itself accepts.

    It also specially serializes the value to a string for use in the
    JavaScript widget.

    Version Changed:
        5.3:
        Added support for Python type hints.

    Example:
        .. code-block:: python

           value_field = ConditionValueBooleanField(initial=True)
    """

    def __init__(self, **field_kwargs) -> None:
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

        super().__init__(field=forms.BooleanField(required=False,
                                                  widget=widget,
                                                  **field_kwargs))

    def prepare_value_for_widget(
        self,
        value: bool,
    ) -> Any:
        """Return a value suitable for use in the widget.

        This will convert a boolean value to a string, so that it can be
        properly matched against the string choices for the select box.

        Args:
            value (bool):
                The value to prepare for the widget.

        Returns:
            str:
            The string value for the widget.
        """
        if value:
            return 'True'
        else:
            return 'False'


class ConditionValueCharField(ConditionValueFormField[str]):
    """Condition value wrapper for single-line text form fields.

    This is a convenience for condition values that want to use a
    :py:class:`~django.forms.fields.CharField`. It accepts the same keyword
    arguments in the constructor that the field itself accepts.

    Version Changed:
        5.3:
        Added support for Python type hints.

    Example:
        .. code-block:: python

           value_field = ConditionValueCharField(max_length=100)
    """

    def __init__(self, **field_kwargs) -> None:
        """Initialize the value field.

        Args:
            **field_kwargs (dict):
                Keyword arguments to pass to the
                :py:class:`~django.forms.fields.CharField` constructor.
        """
        super().__init__(field=forms.CharField(**field_kwargs))


class ConditionValueIntegerField(ConditionValueFormField[int]):
    """Condition value wrapper for integer form fields.

    This is a convenience for condition values that want to use a
    :py:class:`~django.forms.fields.IntegerField`. It accepts the same
    keyword arguments in the constructor that the field itself accepts.

    Version Changed:
        5.3:
        Added support for Python type hints.

    Example:
        .. code-block:: python

           value_field = ConditionValueIntegerField(min_value=0,
                                                    max_value=100)
    """

    def __init__(self, **field_kwargs) -> None:
        """Initialize the value field.

        Args:
            **field_kwargs (dict):
                Keyword arguments to pass to the
                :py:class:`~django.forms.fields.IntegerField` constructor.
        """
        super().__init__(field=forms.IntegerField(**field_kwargs))


class ConditionValueMultipleChoiceField(ConditionValueFormField[_T]):
    """Condition value wrapper for multiple choice fields.

    This is a convenience for condition values that want to use a
    :py:class:`~django.forms.fields.MultipleChoiceField`. It accepts the same
    keyword arguments in the constructor that the field itself accepts.

    Version Changed:
        5.3:
        * Added support for Python type hints.
        * This class is now generic. Subclasses or instances should specify a
          type when subclassing. It will default to :py:class:`typing.Any`.

    Version Added:
        3.0

    Example:
        .. code-block:: python

           value_field = ConditionValueMultipleChoiceField[str](
               choices=[
                   ('value1', 'Value 1'),
                   ('value2', 'Value 2'),
               ])
    """

    def __init__(self, **field_kwargs) -> None:
        """Initialize the value field.

        Args:
            **field_kwargs (dict):
                Keyword arguments to pass to the
                :py:class:`~django.forms.fields.MultipleChoiceField`
                constructor.
        """
        super().__init__(field=forms.MultipleChoiceField(**field_kwargs))


class ConditionValueModelField(ConditionValueFormField[_ModelT]):
    """Condition value wrapper for single model form fields.

    This is a convenience for condition values that want to use a
    :py:class:`~django.forms.fields.ModelChoiceField`. It accepts the same
    keyword arguments in the constructor that the field itself accepts.

    Unlike the standard field, the provided queryset can be a callable that
    returns a queryset.

    Version Changed:
        5.3:
        * Added support for Python type hints.
        * This class is now generic. Subclasses or instances should specify a
          type when subclassing. It will default to :py:class:`typing.Any`.

    Example:
        .. code-block:: python

           value_field = ConditionValueModelField[MyObject](
               queryset=MyObject.objects.all())
    """

    def __init__(
        self,
        queryset: QuerySetOrCallable[_ModelT],
        **field_kwargs,
    ) -> None:
        """Initialize the value field.

        Args:
            queryset (django.db.models.query.QuerySet):
                The queryset used for the field. This may also be a callable
                that returns a queryset.

            **field_kwargs (dict):
                Keyword arguments to pass to the
                :py:class:`~django.forms.fields.ModelChoiceField` constructor.
        """
        def _build_field() -> forms.ModelChoiceField:
            if callable(queryset):
                qs = queryset()
            else:
                qs = queryset

            empty_label = field_kwargs.pop('empty_label', None)

            return forms.ModelChoiceField(queryset=qs,
                                          empty_label=empty_label,
                                          **field_kwargs)

        super().__init__(field=_build_field)


class ConditionValueMultipleModelField(
    ConditionValueFormField[Sequence[_ModelT]]
):
    """Condition value wrapper for multiple model form fields.

    This is a convenience for condition values that want to use a
    :py:class:`~django.forms.fields.ModelMutipleChoiceField`. It accepts the
    same keyword arguments in the constructor that the field itself accepts.

    Unlike the standard field, the provided queryset can be a callable that
    returns a queryset.

    Version Changed:
        5.3:
        * Added support for Python type hints.
        * This class is now generic. Subclasses or instances should specify a
          type when subclassing. It will default to :py:class:`typing.Any`.

    Example:
        .. code-block:: python

           value_field = ConditionValueMultipleModelField[MyObject](
               queryset=MyObject.objects.all())
    """

    def __init__(
        self,
        queryset: QuerySetOrCallable[_ModelT],
        **field_kwargs,
    ) -> None:
        """Initialize the value field.

        Args:
            queryset (django.db.models.query.QuerySet):
                The queryset used for the field. This may also be a callable
                that returns a queryset.

            **field_kwargs (dict):
                Keyword arguments to pass to the
                :py:class:`~django.forms.fields.ModelChoiceField` constructor.
        """
        def _build_field() -> forms.ModelMultipleChoiceField:
            if callable(queryset):
                qs = queryset()
            else:
                qs = queryset

            return forms.ModelMultipleChoiceField(queryset=qs, **field_kwargs)

        super().__init__(field=_build_field)


class ConditionValueRegexField(ConditionValueFormField[re.Pattern]):
    """Condition value for fields that accept regexes.

    This value accepts and validates regex patterns entered into the field.

    Version Changed:
        5.3:
        Added support for Python type hints.

    Example:
        .. code-block:: python

           value_field = ConditionValueRegexField()
    """

    def __init__(self, **field_kwargs) -> None:
        """Initialize the value field.

        Args:
            **field_kwargs (dict):
                Keyword arguments to pass to the
                :py:class:`~django.forms.fields.CharField` constructor.
        """
        super().__init__(field=forms.CharField(**field_kwargs))

    def serialize_value(
        self,
        value: re.Pattern,
    ) -> JSONValue:
        """Serialize a compiled regex into a string.

        Args:
            value (object):
                The value to serialize.

        Returns:
            object:
            The JSON-compatible serialized value.
        """
        return value.pattern

    def deserialize_value(
        self,
        serialized_value: JSONValue,
    ) -> re.Pattern:
        """Deserialize a regex pattern string into a compiled regex.

        Args:
            serialized_value (str):
                The serialized regex pattern to compile.

        Returns:
            re.Pattern:
            The deserialized value.

        Raises:
            djblets.conditions.errors.InvalidConditionValueError:
                The regex could not be compiled.
        """
        assert isinstance(serialized_value, str)

        try:
            return re.compile(serialized_value, re.UNICODE)
        except re.error as e:
            raise InvalidConditionValueError(
                'Your regex pattern had an error: %s' % e)
