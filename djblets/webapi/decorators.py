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
from djblets.webapi.core import WebAPIResponse, WebAPIResponseError
from djblets.webapi.errors import NOT_LOGGED_IN, PERMISSION_DENIED


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
    """
    Checks the API format desired for this handler and sets it in the
    resulting WebAPIResponse.
    """
    def _dec(*args, **kwargs):
        response = view_func(*args, **kwargs)

        if isinstance(response, WebAPIResponse):
            response.api_format = kwargs.get('api_format', 'json')

        return response

    return _dec


@simple_decorator
@webapi
def webapi_login_required(view_func):
    """
    Checks that the user is logged in before invoking the view. If the user
    is not logged in, a NOT_LOGGED_IN error (HTTP 401 Unauthorized) is
    returned.
    """
    def _checklogin(*args, **kwargs):
        from djblets.webapi.auth import basic_access_login

        request = _find_httprequest(args)

        if not request.user.is_authenticated():
            # See if the request contains authentication tokens
            if 'HTTP_AUTHORIZATION' in request.META:
                basic_access_login(request)

        if request.user.is_authenticated():
            response = view_func(*args, **kwargs)
        else:
            response = WebAPIResponseError(request, NOT_LOGGED_IN)

        if isinstance(response, WebAPIResponse):
            response.api_format = kwargs.get('api_format', 'json')

        return response

    return _checklogin


@webapi
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

            if isinstance(response, WebAPIResponse):
                response.api_format = kwargs.get('api_format', 'json')

            return response

        return _checkpermissions

    return _dec
