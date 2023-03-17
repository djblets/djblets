"""Managers for API-related database models."""

import json
import logging

from django.db import IntegrityError
from django.db.models import Manager, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from djblets.secrets.token_generators import token_generator_registry
from djblets.secrets.token_generators.legacy_sha1 import \
    LegacySHA1TokenGenerator
from djblets.webapi.errors import WebAPITokenGenerationError
from djblets.webapi.signals import webapi_token_created


logger = logging.getLogger(__name__)


class WebAPITokenManager(Manager):
    """Manages WebAPIToken models."""

    def generate_token(self,
                       user,
                       *,
                       max_attempts=20,
                       note=None,
                       policy={},
                       auto_generated=False,
                       expires=None,
                       token_generator_id,
                       token_info,
                       **kwargs):
        """Generate a WebAPIToken for a user.

        This will attempt to construct a unique WebAPIToken for a user.

        Since a collision is possible, it will try up to a certain number
        of times. If it cannot create a unique token, a
        :py:class:`~djblets.webapi.errors.WebAPITokenGenerationError` will be
        raised.

        Version Changed:
            4.0:
            Made the ``token_generator_id`` and ``token_info`` parameters
            required.

        Version Changed:
            3.0:
            * Added the ``token_generator_id`` and ``token_info`` parameters.
              These are used to specify what type of token to generate. These
              parameters are currently optional but will be required in
              Djblets 4.0.

            * Added the optional ``expires`` parameter. This can be used to
              set an expiration date for the token.

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

            auto_generated (bool, optional):
                Whether or not the token is being automatically generated.

                This parameter does not affect token generation. It's value
                will solely be used in the
                :py:data:`~djblets.webapi.signals.webapi_token_created` signal.

            expires (datetime.datetime, optional):
                The date and time that the token will expire. By default the
                token will never expire.

                Version Added:
                    3.0

            token_generator_id (str):
                The ID of the token generator to use for generating the token.
                If not set, this will default to :py:class:
                `djblets.secrets.token_generators.legacy_sha1
                .LegacySHA1TokenGenerator`'s ID.

                Version Added:
                    3.0

            token_info (dict):
                A dictionary that contains information needed for token
                generation. If not set, this will default to a dictionary that
                contains necessary information for the :py:class:
                `djblets.secrets.token_generators.legacy_sha1
                .LegacySHA1TokenGenerator`.

                See :py:mod:`djblets.secrets.token_generators` for further
                details on what is required here for each token generator.

                Version Added:
                    3.0

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

            KeyError:
                The ``token_info`` dictionary is missing a required key.
        """
        assert token_generator_id is not None
        assert token_info is not None

        token_generator = token_generator_registry.get_token_generator(
            token_generator_id)

        if token_generator is None:
            logger.error('Could not find the %s token generator in the '
                         'registry.', token_generator_id)

            raise WebAPITokenGenerationError(
                _('Could not find the token generator to generate the token.'))

        if isinstance(policy, dict):
            policy = json.dumps(policy)

        for attempt in range(max_attempts):
            if 'attempt' in token_info:
                token_info['attempt'] = attempt

            token_string = token_generator.create_token(token_info=token_info)

            try:
                token = self.create(user=user,
                                    token=token_string,
                                    token_generator_id=token_generator_id,
                                    note=note or '',
                                    policy=policy,
                                    expires=expires,
                                    **kwargs)
            except IntegrityError:
                # We hit a collision with the token value. Try again.
                pass
            else:
                webapi_token_created.send(
                    instance=token,
                    auto_generated=auto_generated,
                    sender=type(token),
                )
                return token

        # We hit our limit. The database is too full of tokens.
        logger.error('Unable to generate unique API token for %s after '
                     '%d attempts.',
                     user.username,
                     max_attempts)

        raise WebAPITokenGenerationError(
            _('Could not create a unique API token. Please try again.'))

    def invalidate_tokens(self,
                          users=None,
                          extra_query=None,
                          invalid_reason=''):
        """Invalidate a set of tokens.

        Version Added:
            3.0

        Args:
            users (list of int, optional):
                The list of user IDs whose tokens will be invalidated. By
                default this is set to ``None``, in which case the tokens for
                all users will be invalidated. The set of tokens to invalidate
                can be further filtered down using :py:param`extra_query`.

            extra_query (django.db.models.Q, optional):
                Additional query parameters to filter the set of tokens that
                will be invalidated.

            invalid_reason (str, optional):
                A message indicating why the tokens are invalid. This defaults
                to an empty string.
        """
        q = Q()

        if users:
            q &= Q(user__in=users)

        if extra_query:
            q &= extra_query

        self.filter(q).update(valid=False,
                              invalid_reason=invalid_reason,
                              invalid_date=timezone.now())

    def invalidate_token(self, token, invalid_reason=''):
        """Invalidate the given token.

        Version Added:
            3.0

        Args:
            token (str):
                The token value of the token to invalidate.

            invalid_reason (str, optional):
                A message indicating why the token is invalid. This defaults
                to an empty string.
        """
        self.invalidate_tokens(extra_query=Q(token=token),
                               invalid_reason=invalid_reason)
