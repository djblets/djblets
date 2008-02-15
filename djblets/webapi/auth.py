from datetime import datetime

from django.contrib import auth
from django.views.decorators.http import require_POST

from djblets.webapi.core import WebAPIResponse, WebAPIResponseError
from djblets.webapi.decorators import webapi
from djblets.webapi.errors import LOGIN_FAILED


@require_POST
@webapi
def account_login(request, apitype="json"):
    username = request.POST.get('username', None)
    password = request.POST.get('password', None)

    user = auth.authenticate(username=username, password=password)

    if not user or not user.is_active:
        return WebAPIResponseError(request, LOGIN_FAILED)

    auth.login(request, user)
    user.last_login = datetime.now()
    user.save()

    return WebAPIResponse(request)


@webapi
def account_logout(request, apitype="json"):
    auth.logout(request)
    return WebAPIResponse(request)
