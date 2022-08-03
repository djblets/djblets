"""Registry for token generators.

Version Added:
    3.0
"""

from django.conf import settings

from djblets.registries.registry import Registry
from djblets.registries.mixins import ExceptionFreeGetterMixin
from djblets.secrets.token_generators.legacy_sha1 import \
    LegacySHA1TokenGenerator
from djblets.secrets.token_generators.vendor_checksum import \
    VendorChecksumTokenGenerator


class TokenGeneratorRegistry(ExceptionFreeGetterMixin, Registry):
    """Registry for managing token generators.

    Version Added:
        3.0
    """

    lookup_attrs = ['token_generator_id']

    def get_token_generator(self, token_generator_id):
        """Return a token generator with the specified ID.

        Args:
            token_generator_id (str):
                The ID of the token generator.

        Returns:
            djblets.secrets.token_generators.BaseTokenGenerator:
            The token generator instance, or ``None`` if not found.
        """
        return self.get('token_generator_id', token_generator_id)

    def get_default(self):
        """Return the default token generator.

        The default token generator class can be set in
        ``settings.DJBLETS_DEFAULT_API_TOKEN_GENERATOR``. If not
        set it will default to :py:class:`~djblets.secrets.
        token_generators.vendor_checksum.VendorChecksumTokenGenerator`.

        Returns:
            djblets.secrets.token_generators.BaseTokenGenerator:
            The default token generator.
        """
        return getattr(settings,
                       'DJBLETS_DEFAULT_API_TOKEN_GENERATOR',
                       VendorChecksumTokenGenerator)()

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
