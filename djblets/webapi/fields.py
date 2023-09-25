"""Representations of field types in the API."""

from __future__ import annotations

import json
from datetime import datetime
from importlib import import_module
from typing import Any, Mapping, Optional, Sequence, TYPE_CHECKING, Type

import dateutil.parser
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _, gettext
from pytz.exceptions import AmbiguousTimeError
from typing_extensions import TypedDict

if TYPE_CHECKING:
    from django.core.files.uploadedfile import UploadedFile
    from django.http import QueryDict
    from django.utils.datastructures import MultiValueDict
    from typing_extensions import TypeAlias

    from djblets.util.typing import StrOrPromise
    from djblets.webapi.resources import WebAPIResource

    _FieldInfo: TypeAlias = Mapping[str, Any]
    _FilesDict: TypeAlias = MultiValueDict[str, UploadedFile]
    _FieldsDict: TypeAlias = QueryDict


class ListFieldTypeItemsInfo(TypedDict):
    """Information on an item in a list for ListFieldType.

    Version Added:
        4.0
    """

    #: The type of item.
    #:
    #: This can be any class type, including primitives or API field types.
    type: Type


class BaseAPIFieldType:
    """Base class for a field type for an API.

    This is responsible for defining the requirements of a field and to
    validate and normalize a value provided by a client of the API, for storage
    or processing.
    """

    #: The localized name of the field type.
    #:
    #: This should be in sentence casing.
    #:
    #: Type:
    #:     str
    name: Optional[StrOrPromise] = None

    ######################
    # Instance variables #
    ######################

    #: Information defined for the field on the API resource.
    #:
    #: Type:
    #:     dict
    field_info: _FieldInfo

    def __init__(
        self,
        field_info: _FieldInfo,
    ) -> None:
        """Initialize the field type.

        Subclasses should override this if they need to look up any values
        from the field information dictionary.

        Args:
            field_info (dict):
                Information defined for a field.
        """
        self.field_info = field_info

    def get_value_from_data(
        self,
        name: str,
        fields_data: _FieldsDict,
        files_data: _FilesDict,
    ) -> Optional[object]:
        """Return a value from the data from a request.

        Args:
            name (str):
                The name of the entry in the API request to retrieve data for.

            fields_data (dict):
                A dictionary of data provided in the request for standard
                fields. This is usually ``request.POST`` or ``request.GET``.

            files_data (dict):
                A dictionary of data provided in the request for uploaded
                files. This is usually ``request.FILES``.

        Returns:
            object:
            The value from one of the dictionaries, or ``None`` if not found.
        """
        return fields_data.get(name)

    def get_field_info_key(
        self,
        key: str,
    ) -> Any:
        """Return the value for a key in the field information dictionary.

        This will return a consistent error if the key is not found.

        Args:
            key (str):
                The name of the key.

        Returns:
            object:
            The value for the key.

        Raises:
            KeyError:
                The key was not found in the field information dictionary.
        """
        try:
            return self.field_info[key]
        except KeyError:
            raise KeyError(
                gettext('Missing "%(key)s" key in %(field_info)r')
                % {
                    'key': key,
                    'field_info': self.field_info,
                })

    def clean_value(
        self,
        value: Optional[Any],
    ) -> Any:
        """Validate and return a normalized result from the given value.

        By default, this just returns the provided value. Subclasses should
        override this to perform normalization.

        Args:
            value (object):
                The value to validate and normalize.

        Returns:
            object:
            The normalized value.

        Raises:
            django.core.exceptions.ValidationError:
                The value is not valid for this field type.
        """
        return value

    def __str__(self) -> str:
        """Return a string representation of the field type.

        This should return a string summary suitable for human consumption.

        Returns:
            str:
            A string representation of this field type.
        """
        return str(self.name)


class NonRequestFieldTypeMixin:
    """Mixin for field types not intended to handle values from requests."""

    def clean_value(
        self,
        value: Any,
    ) -> Any:
        """Validate and return a normalized string result from a value.

        Args:
            value (object):
                The value to normalize.

        Raises:
            NotImplementederror:
                An error describing that this field type cannot be used with
                request data.
        """
        raise NotImplementedError(
            gettext('%s cannot be used for request data')
            % self.__class__.__name__)


class BooleanFieldType(BaseAPIFieldType):
    """A field type for boolean values."""

    name = _('Boolean')

    def clean_value(
        self,
        value: Any,
    ) -> bool:
        """Validate and return a boolean result from a value.

        This treats ``1``, ``"1"``, ``True``, or ``"true"`` (case-insensitive)
        as truthy values, and everything else as a falsy value.

        Args:
            value (object):
                The value to normalize.

        Returns:
            str:
            The normalized boolean value.
        """
        if isinstance(value, str):
            return value.lower() in ('1', 'true')

        return value in (1, True)


class ChoiceFieldType(BaseAPIFieldType):
    """A field type for a fixed choice of strings.

    This takes a ``choices`` key in the field information dictionary, which
    specifies a list of values accepted during validation.
    """

    name = _('Choice')

    ######################
    # Instance variables #
    ######################

    choices: Sequence[str]

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the field type.

        Args:
            *args (tuple):
                Positional arguments for the parent constructor.

            **kwargs (dict):
                Keyword arguments for the parent constructor.

        Raises:
            KeyError:
                The "choices" key was not found in the field information.
        """
        super().__init__(*args, **kwargs)

        self.choices = self.get_field_info_key('choices')

    def clean_value(
        self,
        value: Any,
    ) -> Any:
        """Validate and return a normalized result from the given value.

        This will return the value if it's a valid choice.

        Args:
            value (object):
                The value to validate and normalize.

        Returns:
            object:
            The value, if it's a valid choice.

        Raises:
            django.core.exceptions.ValidationError:
                The value is not one of the valid choices.
        """
        if value in self.choices:
            return value

        raise ValidationError(
            gettext('"%(value)s" is not a valid value. Valid values '
                    'are: %(choices)s'),
            params={
                'value': value,
                'choices': self._get_choices_str(),
            })

    def __str__(self) -> str:
        """Return a string representation of the field type.

        Returns:
            str:
            A string representation of this field type.
        """
        return gettext('One of %s') % self._get_choices_str()

    def _get_choices_str(self) -> str:
        """Return a string representation of a list of choices.

        This is used for the validation error and string representation.

        Returns:
            str:
            A string representing the list of choices.
        """
        return ', '.join(
            '"%s"' % choice
            for choice in self.choices
        )


class DateTimeFieldType(BaseAPIFieldType):
    """A field type for representing date/times in ISO 8601 format."""

    name = _('ISO 8601 Date/Time')

    def clean_value(
        self,
        value: Any,
    ) -> datetime:
        """Validate and return a datetime from an ISO 8601 value.

        Args:
            value (object):
                The value to validate and normalize. This should be a
                :py:class:`datetime.datetime` or an ISO 8601 date/time string.

        Returns:
            datetime.datetime:
            The resulting date/time value.

        Raises:
            django.core.exceptions.ValidationError:
                The resulting value was not a valid ISO 8601 date/time string
                or the time was ambiguous.
        """
        if not isinstance(value, datetime):
            try:
                value = dateutil.parser.parse(value)
            except ValueError:
                raise ValidationError(
                    gettext('This timestamp is not a valid ISO 8601 '
                            'date/time'))

        if timezone.is_naive(value):
            try:
                value = timezone.make_aware(value,
                                            timezone.get_current_timezone())
            except AmbiguousTimeError:
                raise ValidationError(
                    gettext('This timestamp needs a UTC offset to avoid '
                            'being ambiguous due to daylight savings time '
                            'changes'))

        return value


class DictFieldType(BaseAPIFieldType):
    """A field type for dictionary-based values."""

    name = _('Dictionary')

    def clean_value(
        self,
        value: Any,
    ) -> Mapping[Any, Any]:
        """Validate and return a dictionary from a dictionary or JSON value.

        Args:
            value (object):
                The value to validate and normalize. This should be a
                :py:class:`dict` or JSON string representing a dictionary.

        Returns:
            dict:
            The resulting dictionary value.

        Raises:
            django.core.exceptions.ValidationError:
                The resulting value was not a dictionary. Either the value
                provided was of an invalid type or the parsed JSON data did
                not result in a dictionary.
        """
        if isinstance(value, dict):
            return value
        elif isinstance(value, str):
            try:
                result = json.loads(value)
            except ValueError:
                raise ValidationError(
                    gettext('This value is not a valid JSON document'))

            if isinstance(result, dict):
                return result

        raise ValidationError(
            gettext('This value is not a valid dictionary value'))


class FileFieldType(BaseAPIFieldType):
    """A field type for uploaded files."""

    name = _('Uploaded file')

    def get_value_from_data(
        self,
        name: str,
        fields_data: _FieldsDict,
        files_data: _FilesDict,
    ) -> Optional[UploadedFile]:
        """Return a value from the uploaded files from a request.

        Args:
            name (str):
                The name of the entry in the API request to retrieve data for.

            fields_data (dict, unused):
                A dictionary of data provided in the request for standard
                fields. This is usually ``request.POST`` or ``request.GET``.

            files_data (dict):
                A dictionary of data provided in the request for uploaded
                files. This is usually ``request.FILES``.

        Returns:
            django.core.files.uploadedfile.UploadedFile:
            The value from ``files_data``, or ``None`` if not found.
        """
        return files_data.get(name)


class IntFieldType(BaseAPIFieldType):
    """A field type for integer values."""

    name = _('Integer')

    def clean_value(
        self,
        value: Any,
    ) -> int:
        """Validate and return an integer for a given value.

        Args:
            value (object):
                The value to validate and normalize.

        Returns:
            int:
            The resulting integer value.

        Raises:
            django.core.exceptions.ValidationError:
                The value is not a valid integer.
        """
        try:
            return int(value)
        except ValueError:
            raise ValidationError('"%s" is not an integer' % value)


class ListFieldType(BaseAPIFieldType):
    """A field type for list-based values.

    This takes an optional ``items`` key in the field information dictionary,
    which is itself a field information dictionary for the type of item in the
    list. If provided, all values in a JSON list in the request payload will be
    cleaned using that item type. If not provided, the list will be allowed
    as-is.
    """

    name = _('List')

    ######################
    # Instance variables #
    ######################

    #: Information on the type of item in the list.
    #:
    #: Type:
    #:     dict
    item_info: Optional[ListFieldTypeItemsInfo]

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the field type.

        Args:
            *args (tuple):
                Positional arguments for the parent constructor.

            **kwargs (dict):
                Keyword arguments for the parent constructor.
        """
        super().__init__(*args, **kwargs)

        self.item_info = self.field_info.get('items')

    def clean_value(
        self,
        value: Any,
    ) -> Sequence[Any]:
        """Validate and return a list from a list or JSON value.

        Args:
            value (object):
                The value to validate and normalize. This should be a
                :py:class:`list` or JSON string representing a list.

        Returns:
            list:
            The resulting list of optionally-cleaned items.

        Raises:
            django.core.exceptions.ValidationError:
                This will be raised if the resulting value was not a
                dictionary. Either the value provided was of an invalid type or
                the parsed JSON data did not result in a dictionary.

                It may also be raised through the list item type's validation.
        """
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError:
                raise ValidationError(
                    gettext('This value is not a valid JSON document'))

        if not isinstance(value, list):
            raise ValidationError(gettext('This value is not a valid list'))

        if self.item_info:
            item_type = self.item_info['type'](self.item_info)

            value = [
                item_type.clean_value(item_value)
                for item_value in value
            ]

        return value

    def __str__(self) -> str:
        """Return a string representation of the field type.

        Returns:
            str:
            A string representation of this field type.
        """
        if self.item_info:
            item_type = self.item_info['type'](self.item_info)

            return gettext('List of %s') % item_type
        else:
            return gettext('List')


class ResourceFieldType(NonRequestFieldTypeMixin, BaseAPIFieldType):
    """A field type for referencing a resource.

    This is intended purely for the :py:class:`Resource.fields
    <djblets.webapi.resources.base.WebAPIResource.fields>` list, for the
    purpose of documentation. It's generally not considered safe to let a
    client specify information like resources in a request. If needed,
    subclasses can override :py:meth:`clean_value` to safely handle client
    requests.

    This expects a "resource" key in the field information.  It can point to
    a resource class or instance, or a string path pointing to one.
    """

    name = _('Resource')

    ######################
    # Instance variables #
    ######################

    #: The resource referenced by this field.
    #:
    #: Type:
    #:     type
    resource: Type[WebAPIResource]

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the field type.

        Args:
            *args (tuple):
                Positional arguments for the parent constructor.

            **kwargs (dict):
                Keyword arguments for the parent constructor.

        Raises:
            ImportError:
                The resource class could not be imported.

            KeyError:
                The "resource" key was not found in the field information.
        """
        super().__init__(*args, **kwargs)

        resource = self.get_field_info_key('resource')

        if isinstance(resource, str):
            module, attr = resource.rsplit('.', 1)

            try:
                resource = getattr(import_module(module), attr)
            except (AttributeError, ImportError) as e:
                raise ImportError('Unable to load resource "%s": %s'
                                  % (resource, e))

        self.resource = resource

    def __str__(self) -> str:
        """Return a string representation of the field type.

        Returns:
            str:
            A string representation of this field type.
        """
        # Note that this catches the type for our __name__ property on the
        # class, but in reality, accessing this on a class will get the
        # actual class name. Ignore this here.
        return self.resource.__name__  # type: ignore


class ResourceListFieldType(ResourceFieldType):
    """A field type for referencing a list of a type of resource.

    This is intended purely for the :py:class:`Resource.fields
    <djblets.webapi.resources.base.WebAPIResource.fields>` list, for the
    purpose of documentation. It's generally not considered safe to let a
    client specify information like resources in a request. If needed,
    subclasses can override :py:meth:`clean_value` to safely handle client
    requests.

    This expects a ``"resource"`` key in the field information.
    """

    name = _('Resource List')

    def __str__(self) -> str:
        """Return a string representation of the field type.

        Returns:
            str:
            A string representation of this field type.
        """
        return gettext('List of %s') % self.resource.__name__


class StringFieldType(BaseAPIFieldType):
    """A field type for string values."""

    name = _('String')

    def clean_value(
        self,
        value: Any,
    ) -> str:
        """Validate and return a normalized string result from a value.

        Args:
            value (object):
                The value to normalize.

        Returns:
            str:
            A string version of the value.
        """
        if isinstance(value, bytes):
            return value.decode('utf-8')
        else:
            return str(value)
