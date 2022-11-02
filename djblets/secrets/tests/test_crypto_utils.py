"""Unit tests for djblets.secrets.crypto."""

import inspect

from django.test.utils import override_settings

from djblets.secrets.crypto import (aes_decrypt,
                                    aes_decrypt_base64,
                                    aes_decrypt_iter,
                                    aes_encrypt,
                                    aes_encrypt_base64,
                                    aes_encrypt_iter,
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
            aes_decrypt('abc')  # type: ignore

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
            aes_decrypt(encrypted, key='abc')  # type: ignore


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


class AESDecryptIterTests(BaseAESTestCase):
    """Unit tests for aes_decrypt_iter."""

    def test_with_bytes(self):
        """Testing aes_decrypt_iter with byte string"""
        # The encrypted value will change every time, since the iv changes,
        # so we can't compare a direct value. Instead, we need to ensure that
        # we can decrypt what we encrypt.
        def _gen_data():
            yield (b'\xfd\x1c\xccF\xe8\xa8\xe3\x94`\xfa\xcf\xc7\x11\xeabD'
                   b'\xdft\xfa;Y\x06\xb2\xb3\xae\x10#"kR\x13')
            yield b'\xc7\x17/\x02w\xe0\xe4\xa32L/\x9d\r\xd1v\xa2\xec\xb41\x82'
            yield (b'\xa8\x04\xa9M\t\xac\x92\x9d|\xc0\xb3\xa4\x1f+\xab\x0c\t'
                   b'\xc4\x80\x8c')
            yield b'*'

        decrypted = aes_decrypt_iter(_gen_data())

        self.assertTrue(inspect.isgenerator(decrypted))
        self.assertEqual(b''.join(decrypted),
                         b'this is a test\n'
                         b'and this is another\n'
                         b'hey look three tests!')

    def test_with_list(self):
        """Testing aes_decrypt_iter with list"""
        # The encrypted value will change every time, since the iv changes,
        # so we can't compare a direct value. Instead, we need to ensure that
        # we can decrypt what we encrypt.
        decrypted = aes_decrypt_iter([
            (b'\xfd\x1c\xccF\xe8\xa8\xe3\x94`\xfa\xcf\xc7\x11\xeabD'
             b'\xdft\xfa;Y\x06\xb2\xb3\xae\x10#"kR\x13'),

            b'\xc7\x17/\x02w\xe0\xe4\xa32L/\x9d\r\xd1v\xa2\xec\xb41\x82',

            (b'\xa8\x04\xa9M\t\xac\x92\x9d|\xc0\xb3\xa4\x1f+\xab\x0c\t'
             b'\xc4\x80\x8c'),

            b'*',
        ])

        self.assertTrue(inspect.isgenerator(decrypted))
        self.assertEqual(b''.join(decrypted),
                         b'this is a test\n'
                         b'and this is another\n'
                         b'hey look three tests!')

    def test_with_empty_iter(self):
        """Testing aes_encrypt_iter with empty iterator"""
        # The encrypted value will change every time, since the iv changes,
        # so we can't compare a direct value. Instead, we need to ensure that
        # we can decrypt what we encrypt.
        decrypted = aes_decrypt_iter([])

        self.assertTrue(inspect.isgenerator(decrypted))

        with self.assertRaisesMessage(ValueError,
                                      'Invalid IV size (0) for CFB8.'):
            list(decrypted)

    def test_with_empty_str(self):
        """Testing aes_encrypt_iter with only empty string from iterator"""
        # The encrypted value will change every time, since the iv changes,
        # so we can't compare a direct value. Instead, we need to ensure that
        # we can decrypt what we encrypt.
        decrypted = aes_decrypt_iter([b''])

        self.assertTrue(inspect.isgenerator(decrypted))

        with self.assertRaisesMessage(ValueError,
                                      'Invalid IV size (0) for CFB8.'):
            list(decrypted)

    def test_with_iv_data_split(self):
        """Testing aes_encrypt_iter with IV and encrypted data split across
        items
        """
        def _gen_data():
            data = (
                b'\xfd\x1c\xccF\xe8\xa8\xe3\x94`\xfa\xcf\xc7\x11\xeabD\xdft'
                b'\xfa;Y\x06\xb2\xb3\xae\x10#"kR\x13\xc7\x17/\x02w\xe0\xe4'
                b'\xa32L/\x9d\r\xd1v\xa2\xec\xb41\x82\xa8\x04\xa9M\t\xac\x92'
                b'\x9d|\xc0\xb3\xa4\x1f+\xab\x0c\t\xc4\x80\x8c*'
            )

            # Iterating over a byte string yields integers, unless we slice.
            # Hence needing to do this.
            yield from (
                data[i:i + 1]
                for i in range(len(data))
            )

        # The encrypted value will change every time, since the iv changes,
        # so we can't compare a direct value. Instead, we need to ensure that
        # we can decrypt what we encrypt.
        decrypted = aes_decrypt_iter(_gen_data())

        self.assertTrue(inspect.isgenerator(decrypted))
        self.assertEqual(b''.join(decrypted),
                         b'this is a test\n'
                         b'and this is another\n'
                         b'hey look three tests!')

    def test_with_just_iv_finalizer(self):
        """Testing aes_encrypt_iter with only IV + finalizer in encypted data
        """
        def _gen_data():
            yield b'\xa9;\xb1)b\xaeSF.S\xb4\x8f\x8d\xecT\xfb'

        # The encrypted value will change every time, since the iv changes,
        # so we can't compare a direct value. Instead, we need to ensure that
        # we can decrypt what we encrypt.
        decrypted = aes_decrypt_iter(_gen_data())

        self.assertTrue(inspect.isgenerator(decrypted))
        self.assertEqual(b''.join(decrypted),
                         b'')

    def test_with_custom_key(self):
        """Testing aes_decrypt_iter with custom key"""
        # The encrypted value will change every time, since the iv changes,
        # so we can't compare a direct value. Instead, we need to ensure that
        # we can decrypt what we encrypt.
        def _gen_data():
            yield (b'\xbbq\xb8w\xf8s!\x10E4+\x89^0\x00\x04A\xcc\x82"\xa7\xc6'
                   b'\xe0\xfe\x93M\x0b\xdc\xdf\xe1\xfb')
            yield (b'?\x06\xef\x94\xda\x88\xb7\xd0\xbfM\xc8@\x80\xff\xde\x8a'
                   b'\xc4\xab\xb9h')
            yield (b'B\x97\x82am\x9b\x8d\xf0\x8c\x10\xfa\xb1\xf7\xc7\x9c\x97'
                   b'9ZbA')
            yield b'\x01'

        decrypted = aes_decrypt_iter(_gen_data(),
                                     key=self.CUSTOM_KEY)

        self.assertTrue(inspect.isgenerator(decrypted))
        self.assertEqual(b''.join(decrypted),
                         b'this is a test\n'
                         b'and this is another\n'
                         b'hey look three tests!')


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


class AESEncryptIterTests(BaseAESTestCase):
    """Unit tests for aes_encrypt_iter."""

    def test_with_bytes(self):
        """Testing aes_encrypt_iter with byte string"""
        # The encrypted value will change every time, since the iv changes,
        # so we can't compare a direct value. Instead, we need to ensure that
        # we can decrypt what we encrypt.
        def _gen_data():
            yield b'this is a test\n'
            yield b'and this is another\n'
            yield b'hey look three tests'
            yield b'!'

        encrypted = aes_encrypt_iter(_gen_data())

        self.assertTrue(inspect.isgenerator(encrypted))
        self.assertEqual(aes_decrypt(b''.join(encrypted)),
                         b'this is a test\n'
                         b'and this is another\n'
                         b'hey look three tests!')

    def test_with_unicode(self):
        """Testing aes_encrypt_iter with Unicode string"""
        # The encrypted value will change every time, since the iv changes,
        # so we can't compare a direct value. Instead, we need to ensure that
        # we can decrypt what we encrypt.
        def _gen_data():
            yield 'this is a test\n'
            yield 'and this is another\n'
            yield 'hey look three tests'
            yield '!'

        encrypted = aes_encrypt_iter(_gen_data())

        self.assertTrue(inspect.isgenerator(encrypted))
        self.assertEqual(aes_decrypt(b''.join(encrypted)),
                         b'this is a test\n'
                         b'and this is another\n'
                         b'hey look three tests!')

    def test_with_list(self):
        """Testing aes_encrypt_iter with list"""
        # The encrypted value will change every time, since the iv changes,
        # so we can't compare a direct value. Instead, we need to ensure that
        # we can decrypt what we encrypt.
        encrypted = aes_encrypt_iter([
            b'this is a test\n',
            b'and this is another\n',
            b'hey look three tests',
            b'!',
        ])

        self.assertTrue(inspect.isgenerator(encrypted))
        self.assertEqual(aes_decrypt(b''.join(encrypted)),
                         b'this is a test\n'
                         b'and this is another\n'
                         b'hey look three tests!')

    def test_with_empty_iter(self):
        """Testing aes_encrypt_iter with empty iterator"""
        encrypted = aes_encrypt_iter([])

        self.assertTrue(inspect.isgenerator(encrypted))
        self.assertEqual(aes_decrypt(b''.join(encrypted)),
                         b'')

    def test_with_custom_key(self):
        """Testing aes_encrypt_iter with custom key"""
        # The encrypted value will change every time, since the iv changes,
        # so we can't compare a direct value. Instead, we need to ensure that
        # we can decrypt what we encrypt.
        def _gen_data():
            yield b'this is a test\n'
            yield b'and this is another\n'
            yield b'hey look three tests'
            yield b'!'

        encrypted = aes_encrypt_iter(_gen_data(), key=self.CUSTOM_KEY)
        decrypted = aes_decrypt(b''.join(encrypted), key=self.CUSTOM_KEY)

        self.assertIsInstance(decrypted, bytes)
        self.assertEqual(decrypted,
                         b'this is a test\n'
                         b'and this is another\n'
                         b'hey look three tests!')


class GetDefaultAESEncryptionKeyTests(BaseAESTestCase):
    """Unit tests for get_default_aes_encryption_key."""

    def test_get_default_aes_encryption_key(self):
        """Testing get_default_aes_encryption_key"""
        key = get_default_aes_encryption_key()
        self.assertIsInstance(key, bytes)
        self.assertEqual(key, b'abcdefghijklmnop')
