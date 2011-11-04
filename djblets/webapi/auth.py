#
# auth.py -- Authentication helpers for webapi
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

import logging

from django.contrib import auth
from django.views.decorators.http import require_POST

from djblets.webapi.core import WebAPIResponse, WebAPIResponseError
from djblets.webapi.decorators import webapi
from djblets.webapi.errors import LOGIN_FAILED


def check_login(request):
    """Checks if a login request was made.

    If the client specifies a HTTP_AUTHORIZATION header, this will attempt
    to authenticate using a supported authentication method.
    """
    if 'HTTP_AUTHORIZATION' in request.META:
        basic_access_login(request)


def basic_access_login(request):
    try:
        realm, encoded_auth = request.META['HTTP_AUTHORIZATION'].split(' ')
        username, password = encoded_auth.decode('base64').split(':', 1)
    except ValueError:
        logging.warning("Failed to parse HTTP_AUTHORIZATION header %s" %
                        request.META['HTTP_AUTHORIZATION'],
                        exc_info=1)
        return

    if realm != 'Basic':
        return

    # Don't authenticate if a user is already logged in and the
    # username matches.
    #
    # Note that this does mean that a new password will fail. However,
    # the user is already logged in, and querying the backend for every
    # request is excessive, so it's a tradeoff. The user already has access
    # to the server at this point anyway.

    if request.user.is_anonymous() or request.user.username != username:
        logging.debug("Attempting authentication on API for user %s" % username)
        user = auth.authenticate(username=username, password=password)

        if user and user.is_active:
            auth.login(request, user)
        else:
            logging.debug("API Login failed. No valid user found.")
            auth.logout(request)


@require_POST
@webapi
def account_login(request, *args, **kwargs):
    username = request.POST.get('username', None)
    password = request.POST.get('password', None)

    user = auth.authenticate(username=username, password=password)

    if not user or not user.is_active:
        return WebAPIResponseError(request, LOGIN_FAILED)

    auth.login(request, user)

    return WebAPIResponse(request)


@webapi
def account_logout(request, *args, **kwargs):
    auth.logout(request)
    return WebAPIResponse(request)
