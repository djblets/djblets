"""Registry for token generators.

Version Added:
    3.0
"""

import logging
from typing import Optional, Set

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from djblets.registries.registry import Registry
from djblets.registries.mixins import ExceptionFreeGetterMixin
from djblets.secrets.token_generators.base import BaseTokenGenerator
from djblets.secrets.token_generators.legacy_sha1 import \
    LegacySHA1TokenGenerator
from djblets.secrets.token_generators.vendor_checksum import \
    VendorChecksumTokenGenerator


logger = logging.getLogger(__name__)


class TokenGeneratorRegistry(ExceptionFreeGetterMixin[BaseTokenGenerator],
                             Registry[BaseTokenGenerator]):
    """Registry for managing token generators.

    Version Added:
        3.0
    """

    lookup_attrs = ['token_generator_id']

    def get_token_generator(
        self,
        token_generator_id: str,
    ) -> Optional[BaseTokenGenerator]:
        """Return a token generator with the specified ID.

        Args:
            token_generator_id (str):
                The ID of the token generator.

        Returns:
            djblets.secrets.token_generators.BaseTokenGenerator:
            The token generator instance, or ``None`` if not found.
        """
        return self.get_or_none('token_generator_id', token_generator_id)

    def get_default(self) -> BaseTokenGenerator:
        """Return the default token generator.

        The default token generator ID can be set in
        ``settings.DJBLETS_DEFAULT_API_TOKEN_GENERATOR``. If not
        set the default token generator will be :py:class:`~djblets.secrets.
        token_generators.vendor_checksum.VendorChecksumTokenGenerator`.

        Returns:
            djblets.secrets.token_generators.BaseTokenGenerator:
            The default token generator.
        """
        token_generator_id = (
            getattr(settings, 'DJBLETS_DEFAULT_API_TOKEN_GENERATOR', None) or
            VendorChecksumTokenGenerator.token_generator_id
        )

        assert isinstance(token_generator_id, str)

        token_generator = self.get_token_generator(token_generator_id)

        if token_generator is None:
            logger.error('Could not find the %s token generator in the '
                         'registry. Using the vendor_checksum token '
                         'generator instead.', token_generator_id)

            token_generator_id = \
                VendorChecksumTokenGenerator.token_generator_id
            assert token_generator_id

            token_generator = self.get_token_generator(token_generator_id)
            assert token_generator is not None

        return token_generator

    def get_defaults(self):
        """Return the default token generators.

        Returns:
            list of djblets.secrets.token_generators.BaseTokenGenerator:
            The list of default token generators.
        """
        return [
            LegacySHA1TokenGenerator(),
            VendorChecksumTokenGenerator(),
        ]

    def get_deprecated_token_generators(self) -> Set[str]:
        """Return deprecated token generator IDs.

        The set of deprecated token generator IDs can be set in
        ``settings.DJBLETS_DEPRECATED_TOKEN_GENERATORS``. By default
        the set will contain the :py:class:`~djblets.secrets.
        token_generators.legacy_sha1.LegacySHA1TokenGenerator`'s ID.

        Version Added:
            3.1

        Returns:
            set of str:
            A set of deprecated token generator IDs.
        """
        deprecated_token_generators = (
            getattr(settings, 'DJBLETS_DEPRECATED_TOKEN_GENERATORS', None) or
            {LegacySHA1TokenGenerator.token_generator_id}
        )

        if type(deprecated_token_generators) is not set:
            raise ImproperlyConfigured(
                'settings.DJBLETS_DEPRECATED_TOKEN_GENERATORS must be a set'
                'of token generator ID strings.'
            )

        return deprecated_token_generators
