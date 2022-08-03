"""Generator for tokens that contain an identifiable prefix and checksum.

Version Added:
    3.0
"""

import re
import secrets
import string
import zlib

from django.utils.translation import gettext_lazy as _

from djblets.secrets.token_generators.base import BaseTokenGenerator


class VendorChecksumTokenGenerator(BaseTokenGenerator):
    """Generator for tokens that contain an identifiable prefix and checksum.

    Tokens of this format contain a prefix for identification (such as
    the vendor or type) and a checksum.

    Version Added:
        3.0
    """

    token_generator_id = 'vendor_checksum'

    #: The character set to use for encoding the token.
    #:
    #: Type:
    #:     str
    CHARSET = string.digits + string.ascii_letters

    #: The length of the checksum portion of the token.
    #:
    #: Type:
    #:     int
    CHECKSUM_LENGTH = 6

    #: A regex for validating the characters of a token.
    #:
    #: Type:
    #:     str
    HASH_RE = r'^_[0-9A-Za-z]+$'

    #: The total length of the token.
    #:
    #: Type:
    #:     int
    TOKEN_LENGTH = 255

    def create_token(self, token_info, **kwargs):
        """Create a token that contains a prefix and checksum.

        Args:
            token_info (dict):
                A dictionary that must contain the following information about
                the token:

                Keys:
                    token_type (str):
                        The token prefix to set.

            **kwargs (dict, unused):
                Additional keyword arguments.

        Returns:
            str:
            The token value.

        Raises:
            KeyError:
                The ``token_info`` dictionary is missing a required key.
        """
        self._check_token_info(token_info)

        charset = self.CHARSET
        checksum_length = self.CHECKSUM_LENGTH

        token_type = token_info['token_type']
        token_type_length = len(token_type)
        token_entropy_length = (self.TOKEN_LENGTH - checksum_length -
                                token_type_length - 1)

        entropy_data = ''.join(
            secrets.choice(charset)
            for _i in range(token_entropy_length)
        )

        checksum_data = zlib.crc32(entropy_data.encode('utf-8')) & 0xFFFFFFFF
        checksum = (
            self._base62_encode(checksum_data)
            .zfill(checksum_length)
        )

        return '%s_%s%s' % (token_type, entropy_data, checksum)

    def validate_token(self, token, token_info, **kwargs):
        """Validate the token to see if it is a valid token from this generator.

        Args:
            token (str):
                The token to validate.

            token_info (dict):
                A dictionary that contains the following information about the
                token:

                Keys:
                    token_type (str):
                        The prefix that the token must have.

            **kwargs (dict, unused):
                Additional keyword arguments.

        Returns:
            bool:
            Whether the token is a valid token from this generator.
        """
        try:
            self._check_token_info(token_info)
        except KeyError:
            return False

        token_type = token_info['token_type']

        return (len(token) == 255 and
                token.startswith(token_type) and
                re.match(self.HASH_RE, token[len(token_type):]) is not None)

    def _base62_encode(self, num):
        """Encode the number using Base62.

        Args:
            num (int):
                The number to encode.

        Returns:
            str:
            The encoded number.
        """
        charset = self.CHARSET

        if num == 0:
            return charset[0]

        result = []

        while num:
            num, remainder = divmod(num, 62)
            result.append(charset[remainder])

        return ''.join(reversed(result))

    def _check_token_info(self, token_info):
        """Checks if all required keys are in the token info dictionary.

        Args:
            token_info (dict):
                A dictionary that information about a token. The required
                keys are:

                Keys:
                    token_type (str):
                        The token vendor/type prefix.

        Raises:
            KeyError:
                The ``token_info`` dictionary is missing a required key.
        """
        try:
            token_info['token_type']
        except KeyError as e:
            raise KeyError(
                _('The token_info dictionary must contain a %s key.')
                % e.args[0])
