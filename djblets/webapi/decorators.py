#
# decorators.py -- Decorators used for webapi views
#
# Copyright (c) 2007-2009  Christian Hammond
# Copyright (c) 2007-2009  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#


from django.http import HttpRequest

from djblets.util.decorators import simple_decorator
from djblets.webapi.core import WebAPIResponseError, SPECIAL_PARAMS
from djblets.webapi.errors import NOT_LOGGED_IN, PERMISSION_DENIED, \
                                  INVALID_FORM_DATA


def _find_httprequest(args):
    if isinstance(args[0], HttpRequest):
        request = args[0]
    else:
        # This should be in a class then.
        assert len(args) > 1
        request = args[1]
        assert isinstance(request, HttpRequest)

    return request


@simple_decorator
def webapi(view_func):
    """Indicates that a view is a Web API handler."""
    return view_func


def webapi_response_errors(*errors):
    """Specifies the type of errors that the response may return.

    This can be used for generating documentation or schemas that cover
    the possible error responses of methods on a resource.
    """
    def _dec(view_func):
        def _call(*args, **kwargs):
            return view_func(*args, **kwargs)

        _call.__name__ = view_func.__name__
        _call.__doc__ = view_func.__doc__
        _call.__dict__.update(view_func.__dict__)

        existing_errors = getattr(view_func, 'response_errors', set())
        _call.response_errors = existing_errors.union(set(errors))

        return _call

    return _dec


@webapi_response_errors(NOT_LOGGED_IN)
@simple_decorator
def webapi_login_required(view_func):
    """
    Checks that the user is logged in before invoking the view. If the user
    is not logged in, a NOT_LOGGED_IN error (HTTP 401 Unauthorized) is
    returned.
    """
    def _checklogin(*args, **kwargs):
        request = _find_httprequest(args)

        if request.user.is_authenticated():
            return view_func(*args, **kwargs)
        else:
            return WebAPIResponseError(request, NOT_LOGGED_IN)

    view_func.login_required = True

    return _checklogin


@webapi_response_errors(NOT_LOGGED_IN, PERMISSION_DENIED)
def webapi_permission_required(perm):
    """
    Checks that the user is logged in and has the appropriate permissions
    to access this view. A PERMISSION_DENIED error is returned if the user
    does not have the proper permissions.
    """
    def _dec(view_func):
        def _checkpermissions(*args, **kwargs):
            request = _find_httprequest(args)

            if not request.user.is_authenticated():
                response = WebAPIResponseError(request, NOT_LOGGED_IN)
            elif not request.user.has_perm(perm):
                response = WebAPIResponseError(request, PERMISSION_DENIED)
            else:
                response = view_func(*args, **kwargs)

            return response

        return _checkpermissions

    return _dec


@webapi_response_errors(INVALID_FORM_DATA)
def webapi_request_fields(required={}, optional={}, allow_unknown=False):
    """Validates incoming fields for a request.

    This is a helpful decorator for ensuring that the fields in the request
    match what the caller expects.

    If any field is set in the request that is not in either ``required``
    or ``optional`` and ``allow_unknown`` is True, the response will be an
    INVALID_FORM_DATA error. The exceptions are the special fields
    ``method`` and ``callback``.

    If any field in ``required`` is not passed in the request, these will
    also be listed in the INVALID_FORM_DATA response.

    The ``required`` and ``optional`` parameters are dictionaries
    mapping field name to an info dictionary, which contains the following
    keys:

      * ``type`` - The data type for the field.
      * ```description`` - A description of the field.

    For example:

        @webapi_request_fields(required={
            'name': {
                'type': str,
                'description': 'The name of the object',
            }
        })
    """
    def _dec(view_func):
        def _validate(*args, **kwargs):
            request = _find_httprequest(args)

            if request.method == 'GET':
                request_fields = request.GET
            else:
                request_fields = request.POST

            invalid_fields = {}
            supported_fields = required.copy()
            supported_fields.update(optional)

            if not allow_unknown:
                for field_name in request_fields:
                    if field_name in SPECIAL_PARAMS:
                        # These are special names and can be ignored.
                        continue

                    if field_name not in supported_fields:
                        invalid_fields[field_name] = ['Field is not supported']

            for field_name, info in required.iteritems():
                temp_fields = request_fields

                if info['type'] == file:
                    temp_fields = request.FILES

                if temp_fields.get(field_name, None) is None:
                    invalid_fields[field_name] = ['This field is required']

            new_kwargs = kwargs.copy()

            for field_name, info in supported_fields.iteritems():
                if isinstance(info['type'], file):
                    continue

                value = request_fields.get(field_name, None)

                if value is not None:
                    if type(info['type']) in (list, tuple):
                        # This is a multiple-choice. Make sure the value is
                        # valid.
                        choices = info['type']

                        if value not in choices:
                            invalid_fields[field_name] = [
                                "'%s' is not a valid value. Valid values "
                                "are: %s" % (
                                    value,
                                    ', '.join(["'%s'" % choice
                                               for choice in choices])
                                )
                            ]
                    else:
                        try:
                            if issubclass(info['type'], bool):
                                value = value in (1, "1", True, "True")
                            elif issubclass(info['type'], int):
                                try:
                                    value = int(value)
                                except ValueError:
                                    invalid_fields[field_name] = [
                                        "'%s' is not an integer" % value
                                    ]
                        except TypeError:
                            # The field isn't a class type. This is a
                            # coding error on the developer's side.
                            raise TypeError("%s is not a valid field type" %
                                            info['type'])

                new_kwargs[field_name] = value

            if invalid_fields:
                return INVALID_FORM_DATA, {
                    'fields': invalid_fields,
                }

            return view_func(*args, **new_kwargs)

        _validate.__name__ = view_func.__name__
        _validate.__doc__ = view_func.__doc__
        _validate.__dict__.update(view_func.__dict__)
        _validate.required_fields = required.copy()
        _validate.optional_fields = optional.copy()

        if hasattr(view_func, 'required_fields'):
            _validate.required_fields.update(view_func.required_fields)

        if hasattr(view_func, 'optional_fields'):
            _validate.optional_fields.update(view_func.optional_fields)

        return _validate

    return _dec
