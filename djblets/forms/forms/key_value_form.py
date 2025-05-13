"""A form for working with key/value stores."""

from __future__ import annotations

from typing import (Any, Dict, Generic, Protocol, TYPE_CHECKING,
                    runtime_checkable)

from django import forms
from typing_extensions import TypeVar

if TYPE_CHECKING:
    from typing import ClassVar, Mapping, Sequence

    from django.core.files.uploadedfile import UploadedFile
    from django.utils.datastructures import MultiValueDict


_T = TypeVar('_T', default=Dict[str, Any])


@runtime_checkable
class _Gettable(Protocol):
    """Protocol for things that support a get() method.

    This is used for type checking with the default implementation of
    :py:meth:`KeyValueForm.get_key_value`.
    """

    def get(
        self,
        key: str,
        default: Any = None,
        /,
    ) -> Any:
        ...


@runtime_checkable
class _Settable(Protocol):
    """Protocol for things that support __setitem__.

    This is used for type checking with the default implementation of
    :py:meth:`KeyValueForm.set_key_value`.
    """

    def __setitem__(
        self,
        name: str,
        value: Any,
        /,
    ) -> None:
        ...


class KeyValueForm(forms.Form, Generic[_T]):
    """A form for working with key/value stores.

    Typical forms are built to work either with database models or with
    entirely custom objects, but are less useful when working with
    dictionaries, caches, generic object attributes, or other objects that work
    as key/value stores.

    This form provides a standard way of loading fields from a key/value
    store and saving back out to one.

    By default, it assumes it's working with something that behaves like a
    dictionary (containing a ``get()`` method and a ``__getitem__`` operator).
    This can be overridden by providing implementations of
    :py:meth:`get_key_value` and :py:meth:`set_key_value`.

    Values for specific keys can be specially serialized/deserialized by
    providing :samp:`serialize_{keyname}_field()` and
    :samp:`deserialize_{keyname}_field()` functions. These take a value and are
    expected to return a serializable JSON value or a deserialized value,
    respectively.

    It's also makes it easy to implement saving behavior for the object
    by overriding :py:meth:`save_instance`.

    There's support for dynamically marking fields as disabled and specifying
    the reason it's disabled, for display in the form. This can be done by
    setting :py:attr:`disabled_fields` and :py:attr:`disabled_reasons`, and
    using the latter in a template.

    Fields can be blacklisted from loading or saving by setting
    :py:attr:`Meta.load_blacklist` and :py:attr:`Meta.save_blacklist`,
    respectively to a list or tuple of field names. Unless specified otherwise,
    the loading blacklist will default to the same fields in the save
    blacklist.

    Args:
        disabled_fields (dict):
            A dictionary of field names to booleans indicating fields that
            should be disabled (if their values are set to ``True``). Those
            fields will then be disabled in the HTML (by setting the
            ``disabled`` attribute on the field).

        disabled_reasons (dict):
            A dictionary of field names to strings describing the reason a
            particular field is disabled. These are not required, and are
            not automatically outputted in any form, but may be useful to
            templates.

        instance (object):
            The instance being loaded and saved. This can be ``None`` (the
            default) when not yet working on an instance (but in that case,
            :py:meth:`create_instance` must be defined).

    Example:
        With custom field serialization:

        .. code-block:: python

            class MyForm(KeyValueForm):
                book = forms.ModelChoiceField(queryset=Book.objects.all())

                def serialize_book_field(self, value):
                    return {
                        'id': book.pk,
                        'title': book.title,
                    }

                def deserialize_book_field(self, value):
                    return Book.objects.get(pk=value['id'])
    """

    #: The list of CSS bundle names to include on the page.
    css_bundle_names: ClassVar[Sequence[str]] = []

    #: The list of JavaScript bundle names to include on the page.
    js_bundle_names: ClassVar[Sequence[str]] = []

    ######################
    # Instance variables #
    ######################

    #: The object instance.
    instance: _T | None

    def __init__(
        self,
        data: (Mapping[str, Any] | None) = None,
        files: (MultiValueDict[str, UploadedFile] | None) = None,
        instance: (_T | None) = None,
        *args,
        **kwargs,
    ) -> None:
        """Initialize the form.

        Args:
            data (dict, optional):
                Data for the form.

            files (dict, optional):
                File uploads for the form.

            instance (object, optional):
                The existing instance being loaded from, if any.

            *args (tuple):
                Positional arguments for the form.

            **kwargs (dict):
                Keyword arguments for the form.
        """
        super().__init__(data=data, files=files, *args, **kwargs)

        self.instance = instance
        self.disabled_fields = {}
        self.disabled_reasons = {}

        self.load()

    def load(self) -> None:
        """Load form fields from the instance.

        If an instance was passed to the form, any values found in that
        instance will be set as the initial data for the form. If an instance
        was not passed, then the fields will be left as their default values.

        This also updates the disabled status of any fields marked as
        disabled in the :py:attr:`disabled_fields` attribute.
        """
        load_blacklist = self.get_load_blacklist()
        disabled_fields = set(self.disabled_fields)

        for field_name, field in self.fields.items():
            if self.instance is not None and field_name not in load_blacklist:
                value = self.get_key_value(field_name, default=field.initial)
                deserialize_func = getattr(self,
                                           f'deserialize_{field_name}_field',
                                           None)

                if deserialize_func is not None:
                    value = deserialize_func(value)

                field.initial = value

            if field_name in disabled_fields:
                field.widget.attrs['disabled'] = 'disabled'

    def save(
        self,
        commit: bool = True,
        extra_save_blacklist: (Sequence[str] | None) = None,
    ) -> _T:
        """Save form fields back to the instance.

        This will save the values of any fields not in the blacklist out to
        the instance.

        If the instance doesn't yet exist, it will be created first through a
        call to :py:meth:`create_instance`.

        Args:
            commit (boolean, optional):
                Whether to save the instance after setting all the fields.
                Defaults to ``True`` (though this will do nothing if
                :py:meth:`save_instance` is not overridden).

            extra_save_blacklist (list, optional):
                Additional fields that should not be saved from the form.

        Raises:
            ValueError:
                The form couldn't be saved due to errors.
        """
        if self.errors:
            raise ValueError('The form could not be saved due to one or more '
                             'errors.')

        if extra_save_blacklist is None:
            extra_save_blacklist = []

        if self.instance is None:
            self.instance = self.create_instance()

        blacklist = set(extra_save_blacklist) | set(self.get_save_blacklist())

        for key, value in self.cleaned_data.items():
            if key not in blacklist:
                serialize_func = getattr(self, f'serialize_{key}_field', None)

                if serialize_func is not None:
                    value = serialize_func(value)

                self.set_key_value(key, value)

        if commit:
            self.save_instance()

        return self.instance

    def get_key_value(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        """Return the value for a key in the instance.

        This defaults to calling a ``get()`` method on the instance,
        passing in the values for ``key`` and ``default`` as positional
        arguments.

        This can be overridden to change how values are loaded from the
        instance.

        Args:
            key (str):
                The key to fetch from the instance. This will be a field
                name in the form.

            default (object, optional):
                The default value, from the field's initial value.

        Returns:
            object:
            The value from the instance.
        """
        assert isinstance(self.instance, _Gettable)
        return self.instance.get(key, default)

    def set_key_value(
        self,
        key: str,
        value: Any,
    ) -> None:
        """Set a value in the instance.

        This defaults to calling the ``[]`` operator (as in ``instance[key]``)
        to set the value.

        This can be overridden to change how values are set in the instance.

        Args:
            key (str):
                The key in the instance where the value should be stored.

            value (object):
                The value to store in the instance.
        """
        assert isinstance(self.instance, _Settable)
        self.instance[key] = value

    def create_instance(self) -> _T:
        """Create a new instance.

        If an instance was not provided to the form, this will be called
        prior to saving. It must return an instance that can have new values
        set.

        If not implemented, and no instance is passed to the form, this
        will raise a :py:exc:`NotImplementedError` when called.

        Returns:
            object:
            The resulting instance to populate.

        Raises:
            NotImplementedError:
                The method was not overridden by a subclass, but was called
                due to an instance not being passed to the form.
        """
        raise NotImplementedError(
            f'{self.__class__.__name__} must implement create_instance()')

    def save_instance(self) -> None:
        """Save the instance.

        By default, this doesn't do anything. Subclasses can override it to
        provide saving functionality for the instance.
        """
        pass

    def get_load_blacklist(self) -> Sequence[str]:
        """Return the field blacklist for loading.

        Any field names returned from here will not be loaded from the
        instance.

        If the subclass has a :py:attr:`Meta.load_blacklist` attribute, it will
        be returned. If not, but it has a :py:attr:`Meta.save_blacklist`
        attribute, that will be returned. Otherwise, an empty list will be
        returned.

        This can be overridden to provide more specialized behavior.

        Returns:
            list:
            The field names to blacklist from loading from the instance.
        """
        if meta := getattr(self, 'Meta', None):
            return getattr(meta, 'load_blacklist', self.get_save_blacklist())

        return []

    def get_save_blacklist(self) -> Sequence[str]:
        """Return the field blacklist for saving.

        Any field names returned from here will not be saved to the
        instance.

        If the subclass has a :py:attr:`Meta.save_blacklist` attribute, it will
        be returned. Otherwise, an empty list will be returned.

        This can be overridden to provide more specialized behavior.

        Returns:
            list:
            The field names to blacklist from saving to the instance.
        """
        if meta := getattr(self, 'Meta', None):
            return getattr(meta, 'save_blacklist', [])

        return []
