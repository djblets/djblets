"""Deprecated module for authentication-related functions and classes.

.. deprecated:: 0.9

See the following for the new function/class locations:

* :py:func:`djblets.webapi.auth.backends.check_login`
* :py:func:`djblets.webapi.auth.backends.get_auth_backends`
* :py:func:`djblets.webapi.auth.backends.reset_auth_backends`
* :py:class:`djblets.webapi.auth.backends.base.WebAPIAuthBackend`
* :py:class:`djblets.webapi.auth.backends.basic.WebAPIBasicAuthBackend`
* :py:func:`djblets.webapi.auth.views.account_login`
* :py:func:`djblets.webapi.auth.views.account_logout`
"""

from __future__ import unicode_literals

from djblets.webapi.auth.backends import (check_login, get_auth_backends,
                                          reset_auth_backends)
from djblets.webapi.auth.backends.base import WebAPIAuthBackend
from djblets.webapi.auth.backends.basic import WebAPIBasicAuthBackend
from djblets.webapi.auth.views import account_login, account_logout


__all__ = [
    'WebAPIAuthBackend',
    'WebAPIBasicAuthBackend',
    'account_login',
    'account_logout',
    'check_login',
    'get_auth_backends',
    'reset_auth_backends',
]

__deprecated__ = __all__
