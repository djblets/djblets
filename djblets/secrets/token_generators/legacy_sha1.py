"""Token generator for legacy SHA1 tokens.

Version Added:
    3.0
"""

import hashlib
import re
from typing import Any, Dict

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from djblets.secrets.token_generators.base import BaseTokenGenerator


class LegacySHA1TokenGenerator(BaseTokenGenerator):
    """Token generator for legacy SHA1 tokens.

    The support for SHA1 tokens will soon be deprecated in favour of
    :py:class:`~djblets.secrets.token_generators.vendor_checksum.
    VendorChecksumTokenGenerator` tokens.

    Version Added:
        3.0
    """

    token_generator_id = 'legacy_sha1'

    def create_token(
        self,
        token_info: Dict[str, Any] = {},
        **kwargs,
    ) -> str:
        """Create a SHA1 token.

        Args:
            token_info (dict):
                A dictionary that must contain the following information
                about the token:

                Keys:
                    attempt (int):
                        The number of attempts that have been made to create
                        a token. This is used in the raw token string.

                    user (django.contrib.auth.models.User):
                        The user that the token belongs to.

            **kwargs (dict, unused):
                Additional keyword arguments.

        Returns:
            str:
            The token value.

        Raises:
            KeyError:
                The ``token_info`` dictionary is missing a required key.
        """
        try:
            user = token_info['user']
            attempt = token_info['attempt']
        except KeyError as e:
            raise KeyError(
                _('The token_info dictionary must contain a %s key.')
                % e.args[0])

        prefix = '%s%s%s' % (settings.SECRET_KEY, str(user.pk), user.password)

        raw_token = '%s%s%s' % (prefix, str(attempt),
                                timezone.now().isoformat())
        sha = hashlib.sha1(raw_token.encode('utf-8'))
        token = sha.hexdigest()

        return token

    def validate_token(
        self,
        token: str,
        token_info: Dict[str, Any] = {},
        **kwargs,
    ) -> bool:
        """Validate the token to see if it is a valid token from this generator.

        Args:
            token (str):
                The token to validate.

            token_info (dict, unused):
                A dictionary that contains information about the
                token.

            **kwargs (dict, unused):
                Additional keyword arguments.

        Returns:
            bool:
            Whether the token is a valid token from this generator.
        """
        return re.fullmatch(r'[0-9A-Fa-f]{40}', token) is not None
