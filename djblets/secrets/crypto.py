"""Encryption/decryption utilities.

Version Added:
    3.0
"""

import base64
import os

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from django.conf import settings


AES_BLOCK_SIZE = algorithms.AES.block_size // 8


def _create_cipher(iv, key):
    """Create a cipher for use in symmetric encryption/decryption.

    This will use AES encryption in CFB mode (using an 8-bit shift register)
    and a random IV.

    Version Added:
        3.0

    Args:
        iv (bytes):
            The random IV to use for the cipher.

        key (bytes):
            The encryption key to use.

    Returns:
        cryptography.hazmat.primitives.cipher.Cipher:
        The cipher to use for encryption/decryption.

    Raises:
        ValueError:
            The encryption key was not in the right format.
    """
    if not isinstance(key, bytes):
        raise TypeError('The encryption key must be of type "bytes", not "%s"'
                        % type(key))

    return Cipher(algorithms.AES(key),
                  modes.CFB8(iv),
                  default_backend())


def get_default_aes_encryption_key():
    """Return the default AES encryption key for the install.

    The default key is the first 16 characters (128 bits) of
    :django:setting:`SECRET_KEY`.

    Version Added:
        3.0

    Returns:
        bytes:
        The default encryption key.
    """
    return settings.SECRET_KEY[:16].encode('utf-8')


def aes_encrypt(data, *, key=None):
    """Encrypt data using AES encryption.

    This uses AES encryption in CFB mode (using an 8-bit shift register) and a
    random IV (which will be prepended to the encrypted value). The encrypted
    data will be decryptable using the :py:func:`aes_decrypt` function.

    Version Added:
        3.0

    Args:
        data (bytes):
            The data to encrypt. If a Unicode string is passed in, it will be
            encoded to UTF-8 first.

        key (bytes, optional):
            The optional custom encryption key to use. If not supplied, the
            default encryption key (from
            :py:func:`get_default_aes_encryption_key)` will be used.

    Returns:
        bytes:
        The resulting encrypted value, with the random IV prepended.

    Raises:
        ValueError:
            The encryption key was not in the right format.
    """
    if isinstance(data, str):
        data = data.encode('utf-8')

    iv = os.urandom(AES_BLOCK_SIZE)
    cipher = _create_cipher(iv, key or get_default_aes_encryption_key())
    encryptor = cipher.encryptor()

    return iv + encryptor.update(data) + encryptor.finalize()


def aes_encrypt_base64(data, *, key=None):
    """Encrypt data and encode as Base64.

    The result will be encrypted using AES encryption in CFB mode (using an
    8-bit shift register), and serialized into Base64.

    Version Added:
        3.0

    Args:
        data (bytes or str):
            The data to encrypt. If a Unicode string is passed in, it will
            be encoded to UTF-8 first.

        key (bytes, optional):
            The optional custom encryption key to use. If not supplied, the
            default encryption key (from
            :py:func:`get_default_aes_encryption_key)` will be used.

    Returns:
        str:
        The encrypted password encoded in Base64.

    Raises:
        ValueError:
            The encryption key was not in the right format.
    """
    return base64.b64encode(aes_encrypt(data, key=key)).decode('utf-8')


def aes_decrypt(encrypted_data, *, key=None):
    """Decrypt AES-encrypted data.

    This will decrypt an AES-encrypted value in CFB mode (using an 8-bit
    shift register). It expects the 16-byte cipher IV to be prepended to the
    string.

    This is intended as a counterpart for :py:func:`aes_encrypt`.

    Version Added:
        3.0

    Args:
        encrypted_data (bytes):
            The data to decrypt.

        key (bytes, optional):
            The optional custom encryption key to use. This must match the key
            used for encryption. If not supplied, the default encryption key
            (from :py:func:`get_default_aes_encryption_key)` will be used.

    Returns:
        bytes:
        The decrypted value.

    Raises:
        TypeError:
            One or more arguments had an invalid type.

        ValueError:
            The encryption key was not in the right format.
    """
    if not isinstance(encrypted_data, bytes):
        raise TypeError('The data to decrypt must be of type "bytes", not "%s"'
                        % (type(encrypted_data)))

    cipher = _create_cipher(encrypted_data[:AES_BLOCK_SIZE],
                            key or get_default_aes_encryption_key())
    decryptor = cipher.decryptor()

    return (decryptor.update(encrypted_data[AES_BLOCK_SIZE:]) +
            decryptor.finalize())


def aes_decrypt_base64(encrypted_data, *, key=None):
    """Decrypt an encrypted value encoded in Base64.

    This will decrypt a Base64-encoded encrypted value (from
    :py:func:`aes_encrypt_base64`) into a string.

    Version Added:
        3.0

    Args:
        encrypted_data (bytes or str):
            The Base64-encoded encrypted data to decrypt.

        key (bytes, optional):
            The optional custom encryption key to use. This must match the key
            used for encryption. If not supplied, the default encryption key
            (from :py:func:`get_default_aes_encryption_key)` will be used.

    Returns:
        str:
        The resulting decrypted data.

    Raises:
        ValueError:
            The encryption key was not in the right format.
    """
    return (
        aes_decrypt(base64.b64decode(encrypted_data),
                    key=key)
        .decode('utf-8')
    )
