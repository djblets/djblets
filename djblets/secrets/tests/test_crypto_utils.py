"""Unit tests for djblets.secrets.crypto."""

from django.test.utils import override_settings

from djblets.secrets.crypto import (aes_decrypt,
                                    aes_decrypt_base64,
                                    aes_encrypt,
                                    aes_encrypt_base64,
                                    get_default_aes_encryption_key)
from djblets.testing.testcases import TestCase


@override_settings(SECRET_KEY='abcdefghijklmnopqrstuvwxyz012345')
class BaseAESTestCase(TestCase):
    """Base testcase for AES-related tests."""

    PLAIN_TEXT_UNICODE = 'this is a test 123 ^&*'
    PLAIN_TEXT_BYTES = b'this is a test 123 ^&*'

    PASSWORD_UNICODE = 'this is a test 123 ^&*'
    PASSWORD_BYTES = b'this is a test 123 ^&*'

    CUSTOM_KEY = b'0123456789abcdef'


class AESDecryptTests(BaseAESTestCase):
    """Unit tests for aes_decrypt."""

    def test_with_bytes(self):
        """Testing aes_decrypt with byte string"""
        # The encrypted value was made with PyCrypto, to help with
        # compatibility testing from older installs.
        encrypted = (
            b'\xfb\xdc\xb5h\x15\xa1\xb2\xdc\xec\xf1\x14\xa9\xc6\xab\xb2J\x10'
            b'\'\xd4\xf6&\xd4k9\x82\xf6\xb5\x8bmu\xc8E\x9c\xac\xc5\x04@B'
        )

        decrypted = aes_decrypt(encrypted)
        self.assertIsInstance(decrypted, bytes)
        self.assertEqual(decrypted, self.PLAIN_TEXT_BYTES)

    def test_with_unicode(self):
        """Testing aes_decrypt with Unicode string"""
        expected_message = ('The data to decrypt must be of type "bytes", '
                            'not "<class \'str\'>"')

        with self.assertRaisesMessage(TypeError, expected_message):
            aes_decrypt('abc')

    def test_with_custom_key(self):
        """Testing aes_decrypt with custom key"""
        # The encrypted value was made with PyCrypto, to help with
        # compatibility testing from older installs.
        encrypted = (
            b'\x9cd$e\xb1\x9e\xe0z\xb8[\x9e!\xf2h\x90\x8d\x82f%G4\xc2\xf0'
            b'\xda\x8dr\x81ER?S6\x12%7\x98\x89\x90'
        )

        decrypted = aes_decrypt(encrypted, key=self.CUSTOM_KEY)
        self.assertIsInstance(decrypted, bytes)
        self.assertEqual(decrypted, self.PLAIN_TEXT_BYTES)

    def test_with_custom_key_unicode(self):
        """Testing aes_decrypt with custom key as Unicode"""
        encrypted = (
            b'\x9cd$e\xb1\x9e\xe0z\xb8[\x9e!\xf2h\x90\x8d\x82f%G4\xc2\xf0'
            b'\xda\x8dr\x81ER?S6\x12%7\x98\x89\x90'
        )
        expected_message = ('The encryption key must be of type "bytes", '
                            'not "<class \'str\'>"')

        with self.assertRaisesMessage(TypeError, expected_message):
            aes_decrypt(encrypted, key='abc')


class AESDecryptBase64(BaseAESTestCase):
    """Unit tests for aes_decrypt_base64."""

    def test_with_bytes(self):
        """Testing aes_decrypt_base64 with byte string"""
        # The encrypted value was made with PyCrypto, to help with
        # compatibility testing from older installs.
        encrypted = b'AjsUGevO3UiVH7iN3zO9vxvqr5X5ozuAbOUByTATsitkhsih1Zc='
        decrypted = aes_decrypt_base64(encrypted)

        self.assertIsInstance(decrypted, str)
        self.assertEqual(decrypted, self.PASSWORD_UNICODE)

    def test_with_unicode(self):
        """Testing aes_decrypt_base64 with Unicode string"""
        # The encrypted value was made with PyCrypto, to help with
        # compatibility testing from older installs.
        encrypted = 'AjsUGevO3UiVH7iN3zO9vxvqr5X5ozuAbOUByTATsitkhsih1Zc='
        decrypted = aes_decrypt_base64(encrypted)

        self.assertIsInstance(decrypted, str)
        self.assertEqual(decrypted, self.PASSWORD_UNICODE)

    def test_with_custom_key(self):
        """Testing aes_decrypt_base64 with custom key"""
        # The encrypted value was made with PyCrypto, to help with
        # compatibility testing from older installs.
        encrypted = b'/pOO3VWHRXd1ZAeHZo8MBGQsNClD4lS7XK9WAydt8zW/ob+e63E='
        decrypted = aes_decrypt_base64(encrypted, key=self.CUSTOM_KEY)

        self.assertIsInstance(decrypted, str)
        self.assertEqual(decrypted, self.PASSWORD_UNICODE)


class AESEncryptTests(BaseAESTestCase):
    """Unit tests for aes_encrypt."""

    def test_with_bytes(self):
        """Testing aes_encrypt with byte string"""
        # The encrypted value will change every time, since the iv changes,
        # so we can't compare a direct value. Instead, we need to ensure that
        # we can decrypt what we encrypt.
        encrypted = aes_encrypt(self.PLAIN_TEXT_BYTES)
        self.assertIsInstance(encrypted, bytes)
        self.assertEqual(aes_decrypt(encrypted), self.PLAIN_TEXT_BYTES)

    def test_with_unicode(self):
        """Testing aes_encrypt with Unicode string"""
        # The encrypted value will change every time, since the iv changes,
        # so we can't compare a direct value. Instead, we need to ensure that
        # we can decrypt what we encrypt.
        encrypted = aes_encrypt(self.PLAIN_TEXT_UNICODE)
        self.assertIsInstance(encrypted, bytes)
        self.assertEqual(aes_decrypt(encrypted), self.PLAIN_TEXT_BYTES)

    def test_with_custom_key(self):
        """Testing aes_encrypt with custom key"""
        # The encrypted value will change every time, since the iv changes,
        # so we can't compare a direct value. Instead, we need to ensure that
        # we can decrypt what we encrypt.
        encrypted = aes_encrypt(self.PLAIN_TEXT_BYTES, key=self.CUSTOM_KEY)
        decrypted = aes_decrypt(encrypted, key=self.CUSTOM_KEY)

        self.assertIsInstance(decrypted, bytes)
        self.assertEqual(decrypted, self.PLAIN_TEXT_BYTES)


class AESEncryptBase64(BaseAESTestCase):
    """Unit tests for aes_encrypt_base64."""

    def test_with_bytes(self):
        """Testing aes_encrypt_base64 with byte string"""
        # The encrypted value will change every time, since the iv changes,
        # so we can't compare a direct value. Instead, we need to ensure that
        # we can decrypt what we encrypt.
        encrypted = aes_decrypt_base64(
            aes_encrypt_base64(self.PASSWORD_BYTES))
        self.assertIsInstance(encrypted, str)
        self.assertEqual(encrypted, self.PASSWORD_UNICODE)

    def test_with_unicode(self):
        """Testing aes_encrypt_base64 with Unicode string"""
        # The encrypted value will change every time, since the iv changes,
        # so we can't compare a direct value. Instead, we need to ensure that
        # we can decrypt what we encrypt.
        encrypted = aes_decrypt_base64(
            aes_encrypt_base64(self.PASSWORD_UNICODE))
        self.assertIsInstance(encrypted, str)
        self.assertEqual(encrypted, self.PASSWORD_UNICODE)

    def test_with_custom_key(self):
        """Testing aes_encrypt_base64 with custom key"""
        # The encrypted value will change every time, since the iv changes,
        # so we can't compare a direct value. Instead, we need to ensure that
        # we can decrypt what we encrypt.
        encrypted = aes_encrypt_base64(self.PASSWORD_UNICODE,
                                       key=self.CUSTOM_KEY)
        self.assertIsInstance(encrypted, str)

        decrypted = aes_decrypt_base64(encrypted, key=self.CUSTOM_KEY)
        self.assertIsInstance(decrypted, str)
        self.assertEqual(decrypted, self.PASSWORD_UNICODE)


class GetDefaultAESEncryptionKeyTests(BaseAESTestCase):
    """Unit tests for get_default_aes_encryption_key."""

    def test_get_default_aes_encryption_key(self):
        """Testing get_default_aes_encryption_key"""
        key = get_default_aes_encryption_key()
        self.assertIsInstance(key, bytes)
        self.assertEqual(key, b'abcdefghijklmnop')
