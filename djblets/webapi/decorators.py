from djblets.util.decorators import simple_decorator
from djblets.webapi.core import WebAPIResponse, WebAPIResponseError
from djblets.webapi.errors import NOT_LOGGED_IN, PERMISSION_DENIED


@simple_decorator
def webapi(view_func):
    """
    Checks the API format desired for this handler and sets it in the
    resulting WebAPIResponse.
    """
    def _dec(request, api_format="json", *args, **kwargs):
        response = view_func(request, *args, **kwargs)

        if isinstance(response, WebAPIResponse):
            response.api_format = api_format

        return response

    return _dec


@simple_decorator
@webapi
def webapi_login_required(view_func):
    """
    Checks that the user is logged in before invoking the view. If the user
    is not logged in, a NOT_LOGGED_IN error is returned.
    """
    def _checklogin(request, api_format="json", *args, **kwargs):
        if request.user.is_authenticated():
            return view_func(request, *args, **kwargs)
        else:
            return WebAPIResponseError(request, NOT_LOGGED_IN)

    return _checklogin


@webapi
def webapi_permission_required(perm):
    """
    Checks that the user is logged in and has the appropriate permissions
    to access this view. A PERMISSION_DENIED error is returned if the user
    does not have the proper permissions.
    """
    def _dec(view_func):
        def _checkpermissions(request, api_format="json", *args, **kwargs):
            if not request.user.is_authenticated():
                return WebAPIResponseError(request, NOT_LOGGED_IN)
            elif not request.user.has_perm(perm):
                return WebAPIResponseError(request, PERMISSION_DENIED)

            return view_func(request, *args, **kwargs)

        return _checkpermissions

    return _dec
