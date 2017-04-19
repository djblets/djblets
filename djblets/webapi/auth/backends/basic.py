"""An authentication backend for HTTP Basic Auth."""

from __future__ import unicode_literals

import logging

from djblets.webapi.auth.backends.base import WebAPIAuthBackend


logger = logging.getLogger(__name__)


class WebAPIBasicAuthBackend(WebAPIAuthBackend):
    """Handles HTTP Basic Authentication for the web API."""

    www_auth_scheme = 'Basic realm="Web API"'

    def get_credentials(self, request):
        parts = request.META['HTTP_AUTHORIZATION'].split(' ')
        realm = parts[0]

        if realm != 'Basic':
            return None

        try:
            encoded_auth = parts[1]
            username, password = encoded_auth.decode('base64').split(':', 1)
        except Exception:
            logger.warning('Failed to parse HTTP_AUTHORIZATION header %s',
                           request.META['HTTP_AUTHORIZATION'],
                           exc_info=True,
                           extra={'request': request})
            return None

        return {
            'username': username,
            'password': password,
        }
