"""Decorators used for WebAPI views."""

import inspect
import logging

from django.core.exceptions import ValidationError
from django.http import HttpRequest

from djblets.webapi.errors import (NOT_LOGGED_IN, PERMISSION_DENIED,
                                   INVALID_FORM_DATA)
from djblets.webapi.fields import (BooleanFieldType,
                                   ChoiceFieldType,
                                   FileFieldType,
                                   IntFieldType,
                                   StringFieldType)


logger = logging.getLogger(__name__)


SPECIAL_PARAMS = {
    'api_format', 'callback', '_method', 'expand', 'only-fields',
    'only-links',
}


def _find_httprequest(args):
    if isinstance(args[0], HttpRequest):
        request = args[0]
    else:
        # This should be in a class then.
        assert len(args) > 1
        request = args[1]
        assert isinstance(request, HttpRequest)

    return request


def _convert_legacy_field_type(legacy_type, field_info):
    """Update field information for a legacy field type.

    This takes a legacy field type (which in most cases are only compatible
    with Python 2.x) and updates the provided field information dictionary
    with modern information for the type of field.

    It's important to be clear that the provided field information dictionary
    *will* be modified. This avoids having to repeatedly convert the
    information in the cases where this is used.

    Args:
        legacy_type (object or type):
            The legacy field type. This can be one of :py:class:`unicode`,
            :py:class:`bytes`, :py:class:`bool`, :py:class:`int`,
            :py:class:`file`, :py:class:`list`, or :py:calss:`tuple`.

        field_info (dict):
            The field information dictionary to update.

    Returns:
        type:
        The new subclass of :py:class:`BaseAPIFieldType` stored in the
        dictionary.
    """
    new_type = None

    if inspect.isclass(legacy_type):
        if issubclass(legacy_type, (bytes, str)):
            new_type = StringFieldType
        elif issubclass(legacy_type, bool):
            new_type = BooleanFieldType
        elif issubclass(legacy_type, int):
            new_type = IntFieldType
        elif legacy_type.__name__ == 'file':
            # `file` doesn't exist in Python 3, so no module using that as a
            # type will actually get far enough to define it. We're checking
            # using the class name, which will help us mock this as well.
            new_type = FileFieldType
    elif type(legacy_type) in (list, tuple):
        field_info['choices'] = tuple(legacy_type)
        new_type = ChoiceFieldType

    if new_type is None:
        raise TypeError('%r is not a valid field type' % (legacy_type,))

    field_info['type'] = new_type

    return new_type


def copy_webapi_decorator_data(from_func, to_func):
    """Copies and merges data from one decorated function to another.

    This will copy over the standard function information (name, docs,
    and dictionary data), but will also handle intelligently merging
    together data set by webapi decorators, such as the list of
    possible errors.
    """
    had_errors = (hasattr(to_func, 'response_errors') or
                  hasattr(from_func, 'response_errors'))
    had_fields = (hasattr(to_func, 'required_fields') or
                  hasattr(from_func, 'required_fields'))

    from_errors = getattr(from_func, 'response_errors', set())
    to_errors = getattr(to_func, 'response_errors', set())
    from_required_fields = getattr(from_func, 'required_fields', {}).copy()
    from_optional_fields = getattr(from_func, 'optional_fields', {}).copy()
    to_required_fields = getattr(to_func, 'required_fields', {}).copy()
    to_optional_fields = getattr(to_func, 'optional_fields', {}).copy()

    to_func.__name__ = from_func.__name__
    to_func.__doc__ = from_func.__doc__
    to_func.__dict__.update(from_func.__dict__)

    # Only copy if one of the two functions had this already.
    if had_errors:
        to_func.response_errors = to_errors.union(from_errors)

    if had_fields:
        to_func.required_fields = from_required_fields
        to_func.required_fields.update(to_required_fields)
        to_func.optional_fields = from_optional_fields
        to_func.optional_fields.update(to_optional_fields)

    return to_func


def webapi_decorator(decorator):
    """Decorator for simple webapi decorators.

    This is meant to be used for other webapi decorators in order to
    intelligently preserve information, like the possible response
    errors. It handles merging lists of errors and other information
    instead of overwriting one list with another, as simple_decorator
    would do.
    """
    return copy_webapi_decorator_data(
        decorator,
        lambda f: copy_webapi_decorator_data(f, decorator(f)))


@webapi_decorator
def webapi(view_func):
    """Indicates that a view is a Web API handler."""
    return view_func


def webapi_response_errors(*errors):
    """Specifies the type of errors that the response may return.

    This can be used for generating documentation or schemas that cover
    the possible error responses of methods on a resource.
    """
    @webapi_decorator
    def _dec(view_func):
        def _call(*args, **kwargs):
            return view_func(*args, **kwargs)

        _call.response_errors = set(errors)

        return _call

    return _dec


@webapi_decorator
def webapi_login_required(view_func):
    """
    Checks that the user is logged in before invoking the view. If the user
    is not logged in, a NOT_LOGGED_IN error (HTTP 401 Unauthorized) is
    returned.
    """
    @webapi_response_errors(NOT_LOGGED_IN)
    def _checklogin(*args, **kwargs):
        request = _find_httprequest(args)

        if request.user.is_authenticated:
            return view_func(*args, **kwargs)
        else:
            return NOT_LOGGED_IN

    _checklogin.login_required = True

    return _checklogin


def webapi_permission_required(perm):
    """
    Checks that the user is logged in and has the appropriate permissions
    to access this view. A PERMISSION_DENIED error is returned if the user
    does not have the proper permissions.
    """
    @webapi_decorator
    def _dec(view_func):
        @webapi_response_errors(NOT_LOGGED_IN, PERMISSION_DENIED)
        def _checkpermissions(*args, **kwargs):
            request = _find_httprequest(args)

            if not request.user.is_authenticated:
                response = NOT_LOGGED_IN
            elif not request.user.has_perm(perm):
                logger.warning('%s %s: user %s is missing required '
                               'permission "%s".',
                               request.method, request.path,
                               request.user.username, perm,
                               extra={'request': request})
                response = PERMISSION_DENIED
            else:
                response = view_func(*args, **kwargs)

            return response

        return _checkpermissions

    return _dec


def webapi_request_fields(required={}, optional={}, allow_unknown=False):
    """Validates incoming fields for a request.

    This is a helpful decorator for ensuring that the fields in the request
    match what the caller expects.

    The parsed fields will be passed in as keyword arguments to the decorated
    function. There will also be an additional keyword argument,
    ``parsed_request_fields``, that is a dictionary of all the parsed request
    fields.

    If any field is set in the request that is not in either ``required``
    or ``optional`` and ``allow_unknown`` is False, the response will be an
    INVALID_FORM_DATA error. The exceptions are the special fields
    ``method`` and ``callback``.

    If any field in ``required`` is not passed in the request, these will
    also be listed in the INVALID_FORM_DATA response.

    The ``required`` and ``optional`` parameters are dictionaries
    mapping field name to an info dictionary, which contains the following
    keys:

    * ``type`` - The data type for the field.
    * ``description`` - A description of the field.

    For example:

    .. code-block:: python

        from djblets.webapi.decorators import webapi_request_fields
        from djblets.webapi.fields import StringFieldType


        @webapi_request_fields(required={
            'name': {
                'type': StringFieldType,
                'description': 'The name of the object',
            }
        })
    """
    @webapi_decorator
    def _dec(view_func):
        @webapi_response_errors(INVALID_FORM_DATA)
        def _validate(*args, **kwargs):
            request = _find_httprequest(args)

            if request.method == 'GET':
                request_fields = request.GET
            else:
                request_fields = request.POST

            extra_fields = {}
            invalid_fields = {}

            for field_name, field_value in request_fields.items():
                if field_name in SPECIAL_PARAMS:
                    # These are special names and can be ignored.
                    continue

                if (field_name not in _validate.required_fields and
                    field_name not in _validate.optional_fields):
                    if allow_unknown:
                        extra_fields[field_name] = field_value
                    elif field_name not in kwargs:
                        # If the field is present in kwargs, it was already
                        # processed (and therefore validated) by a containing
                        # decorator.
                        invalid_fields[field_name] = ['Field is not supported']

            parsed_request_fields = {}

            for fields_dict, is_required in ((required, True),
                                             (optional, False)):
                for field_name, field_info in fields_dict.items():
                    field_type_cls = field_info['type']

                    if not hasattr(field_type_cls, 'clean_value'):
                        field_type_cls = _convert_legacy_field_type(
                            field_type_cls, field_info)

                    field_type = field_type_cls(field_info)
                    field_value = field_type.get_value_from_data(
                        name=field_name,
                        fields_data=request_fields,
                        files_data=request.FILES)

                    if field_value is not None:
                        try:
                            parsed_request_fields[field_name] = \
                                field_type.clean_value(field_value)
                        except ValidationError as e:
                            invalid_fields[field_name] = e.messages
                    elif is_required:
                        invalid_fields[field_name] = ['This field is required']

            if invalid_fields:
                return INVALID_FORM_DATA, {
                    'fields': invalid_fields,
                }

            new_kwargs = kwargs.copy()
            new_kwargs['extra_fields'] = extra_fields
            new_kwargs['parsed_request_fields'] = parsed_request_fields
            new_kwargs.update(parsed_request_fields)

            return view_func(*args, **new_kwargs)

        _validate.required_fields = required.copy()
        _validate.optional_fields = optional.copy()

        if hasattr(view_func, 'required_fields'):
            _validate.required_fields.update(view_func.required_fields)

        if hasattr(view_func, 'optional_fields'):
            _validate.optional_fields.update(view_func.optional_fields)

        return _validate

    return _dec
