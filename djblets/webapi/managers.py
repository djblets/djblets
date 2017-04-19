"""Managers for API-related database models."""

from __future__ import unicode_literals

import hashlib
import json
import logging

from django.conf import settings
from django.db import IntegrityError
from django.db.models import Manager
from django.utils import six, timezone
from django.utils.six.moves import range
from django.utils.translation import ugettext_lazy as _

from djblets.webapi.errors import WebAPITokenGenerationError


logger = logging.getLogger(__name__)


class WebAPITokenManager(Manager):
    """Manages WebAPIToken models."""

    def generate_token(self, user, max_attempts=20, note=None, policy={},
                       **kwargs):
        """Generate a WebAPIToken for a user.

        This will attempt to construct a unique WebAPIToken for a user.

        Since a collision is possible, it will try up to a certain number
        of times. If it cannot create a unique token, a
        :py:class:`~djblets.webapi.errors.WebAPITokenGenerationError` will be
        raised.

        Args:
            user (django.contrib.auth.models.User):
                The user who will own the token.

            max_attempts (int, optional):
                The maximum number of attempts to try to find a non-conflicting
                token. Defaults to 20.

            note (unicode, optional):
                A note describing the token.

            policy (dict, optional):
                The policy document describing what this token can access
                in the API. By default, this provides full access.

            **kwargs (dict):
                Additional keyword arguments representing fields in the token.
                These will be set on the token object.

        Returns:
            djblets.webapi.models.BaseWebAPIToken:
            The generated API token.

        Raises:
            djblets.webapi.errors.WebAPITokenGenerationError:
                The token was not able to be generated after ``max_attempts``
                number of collisions were hit.
        """
        prefix = settings.SECRET_KEY + six.text_type(user.pk) + user.password

        if isinstance(policy, dict):
            policy = json.dumps(policy)

        for attempt in range(max_attempts):
            raw_token = (prefix + six.text_type(attempt) +
                         timezone.now().isoformat())
            sha = hashlib.sha1(raw_token.encode('utf-8'))
            token = sha.hexdigest()

            try:
                return self.create(user=user,
                                   token=token,
                                   note=note or '',
                                   policy=policy,
                                   **kwargs)
            except IntegrityError:
                # We hit a collision with the token value. Try again.
                pass

        # We hit our limit. The database is too full of tokens.
        logger.error('Unable to generate unique API token for %s after '
                     '%d attempts.',
                     user.username,
                     max_attempts)

        raise WebAPITokenGenerationError(
            _('Could not create a unique API token. Please try again.'))
