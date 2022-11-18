"""An authentication backend for HTTP Basic Auth."""

from __future__ import annotations

import base64
import logging
from typing import List

from django.http import HttpRequest

from djblets.webapi.auth.backends.base import (WebAPIAuthBackend,
                                               WebAPIGetCredentialsResult)


logger = logging.getLogger(__name__)


class WebAPIBasicAuthBackend(WebAPIAuthBackend):
    """Handles HTTP Basic Authentication for the web API."""

    www_auth_scheme = 'Basic realm="Web API"'

    def get_credentials(
        self,
        request: HttpRequest,
    ) -> WebAPIGetCredentialsResult:
        """Return credentials provided in the request.

        This returns a dictionary of all credentials necessary for this
        auth backend.

        If an :mailheader:`Authorization` header is provided, the result will
        be the parsed username and password.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

        Returns:
            dict:
            A dictionary of credential information containing:

            Keys:
                password (str):
                    The password from the authentication request.

                username (str):
                    The username from the authentication request.

            This will be ``None`` if :mailheader:`Authorization` is not passed
            or could not be parsed as a HTTP Basic Auth header.
        """
        parts: List[str] = request.META['HTTP_AUTHORIZATION'].split(' ')
        realm = parts[0]

        if realm != 'Basic':
            return None

        try:
            encoded_auth: bytes = parts[1].encode('utf-8')
            username: str
            password: str

            username, password = \
                base64.b64decode(encoded_auth).decode('utf-8').split(':', 1)
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
