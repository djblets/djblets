"""Unit tests for TokenGeneratorRegistry.

Version Added:
    3.0
"""

from django.test.utils import override_settings

from djblets.secrets.token_generators import token_generator_registry
from djblets.secrets.token_generators.legacy_sha1 import \
    LegacySHA1TokenGenerator
from djblets.secrets.token_generators.vendor_checksum import \
    VendorChecksumTokenGenerator
from djblets.testing.testcases import TestCase


class TokenGeneratorRegistryTests(TestCase):
    """Unit tests for TokenGeneratorRegistry.

    Version Added:
        3.0
    """

    def test_get_default(self):
        """Testing TokenGeneratorRegistry.get_default with no default
        token generator specified in settings
        """
        token_generator = token_generator_registry.get_default()

        self.assertIsInstance(token_generator, VendorChecksumTokenGenerator)

    @override_settings(
        DJBLETS_DEFAULT_API_TOKEN_GENERATOR='legacy_sha1')
    def test_get_default_when_set(self):
        """Testing TokenGeneratorRegistry.get_default with a default
        token generator specified in settings
        """
        token_generator = token_generator_registry.get_default()

        self.assertIsInstance(token_generator, LegacySHA1TokenGenerator)

    @override_settings(
        DJBLETS_DEFAULT_API_TOKEN_GENERATOR='not_registered')
    def test_get_default_when_set_not_registered(self):
        """Testing TokenGeneratorRegistry.get_default with a default token
        generator specified in settings that does not exist in the registry
        """
        expected_log = ('Could not find the not_registered token generator '
                        'in the registry. Using the vendor_checksum token '
                        'generator instead.')

        with self.assertLogs() as logs:
            token_generator = token_generator_registry.get_default()

            self.assertEqual(logs.records[0].getMessage(),
                             expected_log)
            self.assertIsInstance(token_generator,
                                  VendorChecksumTokenGenerator)

    def test_get_deprecated_token_generators(self):
        """Testing TokenGeneratorRegistry.get_deprecated_token_generators with
        no set of deprecated generators specified in settings
        """
        generators = token_generator_registry.get_deprecated_token_generators()

        self.assertSetEqual(generators,
                            {LegacySHA1TokenGenerator.token_generator_id})

    @override_settings(
        DJBLETS_DEPRECATED_TOKEN_GENERATORS={'vendor_checksum'})
    def test_get_deprecated_token_generators_when_set(self):
        """Testing TokenGeneratorRegistry.get_deprecated_token_generators with
        a set of deprecated generators specified in settings
        """
        generators = token_generator_registry.get_deprecated_token_generators()

        self.assertSetEqual(generators,
                            {VendorChecksumTokenGenerator.token_generator_id})
