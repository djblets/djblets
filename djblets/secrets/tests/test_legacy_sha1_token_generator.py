"""Unit tests for LegacySHA1TokenGenerator.

Version Added:
    3.0
"""

from django.contrib.auth.models import User

from djblets.secrets.token_generators.legacy_sha1 import \
    LegacySHA1TokenGenerator
from djblets.testing.testcases import TestCase


class LegacySHA1TokenGeneratorTests(TestCase):
    """Unit tests for LegacySHA1TokenGenerator.

    Version Added:
        3.0
    """

    def setUp(self):
        super().setUp()

        self.user = User.objects.create(username='test-user')
        self.token_generator = LegacySHA1TokenGenerator()

    def test_create_token(self):
        """Testing LegacySHA1TokenGenerator.create_token"""
        token = self.token_generator.create_token(
            token_info={
                'user': self.user,
                'attempt': 0,
            })

        self.assertIsNotNone(token)

    def test_create_token_with_missing_required_key(self):
        """Testing LegacySHA1TokenGenerator.create_token with a missing
        required key in token info
        """
        error_message = 'The token_info dictionary must contain a user key.'

        with self.assertRaisesMessage(KeyError, error_message):
            self.token_generator.create_token(
                token_info={
                    'attempt': 0,
                })

    def test_validate_token_with_valid_token(self):
        """Testing LegacySHA1TokenGenerator.validate_token with valid token"""
        token = 'ead9190eadc2f8ccc051f813be28ea1f24ba3810'

        self.assertTrue(self.token_generator.validate_token(token))

    def test_validate_token_with_invalid_token_length(self):
        """Testing LegacySHA1TokenGenerator.validate_token with a token that
        has an invalid length
        """
        token = 'abcd1'

        self.assertFalse(self.token_generator.validate_token(token))

    def test_validate_token_with_invalid_token_chars(self):
        """Testing LegacySHA1TokenGenerator.validate_token with a token that
        has an invalid character in it
        """
        token = '!ad9190eadc2f8ccc051f813be28ea1f24ba3810'

        self.assertFalse(self.token_generator.validate_token(token))
