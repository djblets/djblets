"""Unit tests for VendorChecksumTokenGenerator.

Version Added:
    3.0
"""

from djblets.secrets.token_generators.vendor_checksum import \
    VendorChecksumTokenGenerator
from djblets.testing.testcases import TestCase


class VendorChecksumTokenGeneratorTests(TestCase):
    """Unit tests for VendorChecksumTokenGenerator.

    Version Added:
        3.0
    """

    def setUp(self):
        super(VendorChecksumTokenGeneratorTests, self).setUp()

        self.token_generator = VendorChecksumTokenGenerator()

    def test_create_token(self):
        """Testing VendorChecksumTokenGenerator.create_token"""
        token = self.token_generator.create_token(
            token_info={
                'token_type': 'test',
            })

        self.assertEqual(len(token), 255)
        self.assertTrue(token.startswith('test'))

    def test_create_token_with_missing_required_key(self):
        """Testing VendorChecksumTokenGenerator.create_token with a missing
        required key in token info
        """
        error_message = ('The token_info dictionary must contain a '
                         'token_type key.')

        with self.assertRaisesMessage(KeyError, error_message):
            self.token_generator.create_token(token_info={})

    def test_validate_token_with_valid_token(self):
        """Testing VendorChecksumTokenGenerator.validate_token with a valid
        token
        """
        token = ('test_kEz3qSWeN25rOVA8RXitY0ywaiAOuey7WRHFeTDaqqR9g827qwuYFy5'
                 'p3NKwLThndO33aVL5pBcU5da9pNnTYtiIsC4f9uLMAP8rQKZa82W91ZArtV4'
                 'WJSDpV07VTszJq6dvzmnbvcTDQvv0crBS2XDntwx5lI4xbtpMR6mquknRneV'
                 'OJxf682I208BGhs8PdGRtv2unF176tCoC3ccI8VFx31Hdb2mgQKPyPCYEtXN'
                 '32N7RUsAX1BjxMy')

        self.assertTrue(self.token_generator.validate_token(
            token,
            token_info={'token_type': 'test'}))

    def test_validate_token_with_valid_token_wrong_base62_encode(self):
        """Testing VendorChecksumTokenGenerator.validate_token with a valid
        token that uses Djblets 3.0's incorrect base62-encoding for checksums
        """
        token = ('test_kEz3qSWeN25rOVA8RXitY0ywaiAOuey7WRHFeTDaqqR9g827qwuYFy5'
                 'p3NKwLThndO33aVL5pBcU5da9pNnTYtiIsC4f9uLMAP8rQKZa82W91ZArtV4'
                 'WJSDpV07VTszJq6dvzmnbvcTDQvv0crBS2XDntwx5lI4xbtpMR6mquknRneV'
                 'OJxf682I208BGhs8PdGRtv2unF176tCoC3ccI8VFx31Hdb2mgQKPyPCYEtXN'
                 '32N7RUsAX1bJXmY')

        self.assertTrue(self.token_generator.validate_token(
            token,
            token_info={'token_type': 'test'}))

    def test_validate_token_with_invalid_token_length(self):
        """Testing VendorChecksumTokenGenerator.validate_token with a token
        that has an invalid length
        """
        token = 'test_1234'

        self.assertFalse(self.token_generator.validate_token(
            token,
            token_info={'token_type': 'test'}))

    def test_validate_token_with_invalid_token_chars(self):
        """Testing VendorChecksumTokenGenerator.validate_token with a token
        that has an invalid character in it
        """
        token = ('test_$Ez3qSWeN25rOVA8RXitY0ywaiAOuey7WRHFeTDaqqR9g827qwuYFy5'
                 'p3NKwLThndO33aVL5pBcU5da9pNnTYtiIsC4f9uLMAP8rQKZa82W91ZArtV4'
                 'WJSDpV07VTszJq6dvzmnbvcTDQvv0crBS2XDntwx5lI4xbtpMR6mquknRneV'
                 'OJxf682I208BGhs8PdGRtv2unF176tCoC3ccI8VFx31Hdb2mgQKPyPCYEtXN'
                 '32N7RUsAX1BjxMy')

        self.assertFalse(self.token_generator.validate_token(
            token,
            token_info={'token_type': 'test'}))

    def test_validate_token_with_invalid_token_type(self):
        """Testing VendorChecksumTokenGenerator.validate_token with a token
        that has an invalid token type
        """
        token = ('fail_kEz3qSWeN25rOVA8RXitY0ywaiAOuey7WRHFeTDaqqR9g827qwuYFy5'
                 'p3NKwLThndO33aVL5pBcU5da9pNnTYtiIsC4f9uLMAP8rQKZa82W91ZArtV4'
                 'WJSDpV07VTszJq6dvzmnbvcTDQvv0crBS2XDntwx5lI4xbtpMR6mquknRneV'
                 'OJxf682I208BGhs8PdGRtv2unF176tCoC3ccI8VFx31Hdb2mgQKPyPCYEtXN'
                 '32N7RUsAX1BjxMy')

        self.assertFalse(self.token_generator.validate_token(
            token,
            token_info={'token_type': 'test'}))

    def test_validate_token_with_invalid_token_checksum(self):
        """Testing VendorChecksumTokenGenerator.validate_token with a token
        that does not match its checksum
        """
        token = ('test_kEz3qSWeN25rOVA8RXitY0ywaiAOuey7WRHFeTDaqqR9g827qwuYFy5'
                 'p3NKwLThndO33aVL5pBcU5da9pNnTYtiIsC4f9uLMAP8rQKZa82W91ZArtV4'
                 'WJSDpV07VTszJq6dvzmnbvcTDQvv0crBS2XDntwx5lI4xbtpMR6mquknRneV'
                 'OJxf682I208BGhs8PdGRtv2unF176tCoC3ccI8VFx31Hdb2mgQKPyPCYEtXN'
                 '32N7RUsAX1BjxMb')

        self.assertFalse(self.token_generator.validate_token(
            token,
            token_info={'token_type': 'test'}))

    def test_validate_token_with_empty_token_info(self):
        """Testing VendorChecksumTokenGenerator.validate_token with a valid
        token but no token_type defined in the token_info
        """
        token = ('test_kEz3qSWeN25rOVA8RXitY0ywaiAOuey7WRHFeTDaqqR9g827qwuYFy5'
                 'p3NKwLThndO33aVL5pBcU5da9pNnTYtiIsC4f9uLMAP8rQKZa82W91ZArtV4'
                 'WJSDpV07VTszJq6dvzmnbvcTDQvv0crBS2XDntwx5lI4xbtpMR6mquknRneV'
                 'OJxf682I208BGhs8PdGRtv2unF176tCoC3ccI8VFx31Hdb2mgQKPyPCYEtXN'
                 '32N7RUsAX1BjxMy')

        self.assertFalse(self.token_generator.validate_token(token,
                                                             token_info={}))
