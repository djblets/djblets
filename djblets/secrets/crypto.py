"""Encryption/decryption utilities.

Version Added:
    3.0
"""

import base64
import os
from typing import AnyStr, Iterable, Iterator, Optional, Union, cast

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from django.conf import settings


AES_BLOCK_SIZE = cast(int, algorithms.AES.block_size) // 8


def _create_cipher(
    iv: bytes,
    *,
    key: Optional[bytes] = None,
) -> Cipher:
    """Create a cipher for use in symmetric encryption/decryption.

    This will use AES encryption in CFB mode (using an 8-bit shift register)
    and a random IV.

    Version Added:
        3.0

    Args:
        iv (bytes):
            The random IV to use for the cipher.

        key (bytes, optional):
            The encryption key to use.

    Returns:
        cryptography.hazmat.primitives.cipher.Cipher:
        The cipher to use for encryption/decryption.

    Raises:
        ValueError:
            The encryption key was not in the right format.
    """
    if key is None:
        key = get_default_aes_encryption_key()

    if not isinstance(key, bytes):
        raise TypeError('The encryption key must be of type "bytes", not "%s"'
                        % type(key))

    return Cipher(algorithms.AES(key),
                  modes.CFB8(iv),
                  default_backend())


def get_default_aes_encryption_key() -> bytes:
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


def aes_encrypt(
    data: Union[bytes, str],
    *,
    key: Optional[bytes] = None,
) -> bytes:
    """Encrypt data using AES encryption.

    This uses AES encryption in CFB mode (using an 8-bit shift register) and a
    random IV (which will be prepended to the encrypted value). The encrypted
    data will be decryptable using the :py:func:`aes_decrypt` function.

    Version Added:
        3.0

    Args:
        data (bytes or str):
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
    cipher = _create_cipher(iv, key=key)
    encryptor = cipher.encryptor()

    return iv + encryptor.update(data) + encryptor.finalize()


def aes_encrypt_base64(
    data: AnyStr,
    *,
    key: Optional[bytes] = None,
) -> str:
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


def aes_encrypt_iter(
    data_iter: Iterable[Union[bytes, str]],
    *,
    key: Optional[bytes] = None,
) -> Iterator[bytes]:
    """Encrypt and yield data iteratively.

    This iterates through an iterable (a generator, list, or similar),
    yielding AES-encrypted batches of data. This can be used when streaming
    a source and yielding encrypted data to a file, HTTP response, across
    multiple cache keys, etc.

    The result can be decrypted either by joining together all the results
    or by passing the results to :py:func:`aes_decrypt_iter`.

    Args:
        data_iter (iterable):
            An iterator that yields byte strings or Unicode strings.

        key (bytes, optional):
            The optional custom encryption key to use. If not supplied, the
            default encryption key (from
            :py:func:`get_default_aes_encryption_key)` will be used.

    Yields:
        bytes:
        An encrypted block of data.

    Raises:
        ValueError:
            The encryption key was not in the right format.
    """
    iv = os.urandom(AES_BLOCK_SIZE)
    cipher = _create_cipher(iv, key=key)
    encryptor = cipher.encryptor()

    # We want the very first value to contain the iv, and the very last to
    # contain the finalizer. So we need to operate one ahead of the item from
    # the stream. We'll iterate through, grab an item, then yield the previous
    # one (prepending the iv if yielding the very first).
    prev_item = None

    for item in data_iter:
        if isinstance(item, str):
            item = item.encode('utf-8')

        encrypted_item = encryptor.update(item)

        if prev_item is not None:
            yield prev_item

            prev_item = encrypted_item
        else:
            prev_item = iv + encrypted_item

    # We can now follow up with the finalizer.
    if prev_item is not None:
        yield prev_item + encryptor.finalize()
    else:
        # We had absolutely nothing to yield. Let's just yield an empty
        # encrypted block.
        yield iv + encryptor.finalize()


def aes_decrypt(
    encrypted_data: bytes,
    *,
    key: Optional[bytes] = None,
) -> bytes:
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
                            key=key)
    decryptor = cipher.decryptor()

    return (decryptor.update(encrypted_data[AES_BLOCK_SIZE:]) +
            decryptor.finalize())


def aes_decrypt_base64(
    encrypted_data: AnyStr,
    *,
    key: Optional[bytes] = None,
) -> str:
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


def aes_decrypt_iter(
    encrypted_iter: Iterable[bytes],
    *,
    key: Optional[bytes] = None,
) -> Iterator[bytes]:
    """Decrypt and yield data iteratively.

    This iterates through an iterable (a generator, list, or similar),
    decrypting items and yielding the decrypted values. This can be used when
    streaming an encrypted source and yielding the decrypted results to a file,
    HTTP response, across multiple cache keys, etc.

    Args:
        encrypted_iter (iterable):
            An iterator that yields AES-encrypted data as byte strings.

        key (bytes, optional):
            The optional custom encryption key to use. If not supplied, the
            default encryption key (from
            :py:func:`get_default_aes_encryption_key)` will be used.

    Yields:
        bytes:
        A decrypted block of data.

    Raises:
        ValueError:
            The encryption key was not in the right format or the encrypted
            data was invalid.
    """
    # Ensure we're working with an actual iterator now, not just something
    # iterable. We need to ensure we're not starting iteration over when we
    # loop through a second time.
    encrypted_iter = iter(encrypted_iter)

    # We need to read enough to get the IV (the Initialization Vector at the
    # start of the encrypted data). We'll keep yielding items until we find
    # it, or until we have nothing left to read.
    #
    # If we don't receive enough for the IV, cryptography will raise a
    # ValueError below (same as when passing an incomplete payload to
    # aes_decrypt()).
    iv_buf = b''

    for item in encrypted_iter:
        iv_buf += item

        if len(iv_buf) >= AES_BLOCK_SIZE:
            break

    # Create the cipher as normal.
    cipher = _create_cipher(iv_buf[:AES_BLOCK_SIZE],
                            key=key)
    decryptor = cipher.decryptor()

    # Start with the data after the IV, and then go through the iterator.
    # Like with aes_encrypt_iter(), we're going to fetch the next item and
    # *then* yield the previous item. The reason is that we want to ensure
    # the finalizer is part of the last item yielded.
    prev_item = iv_buf[AES_BLOCK_SIZE:] or None

    for item in encrypted_iter:
        if prev_item is not None:
            yield decryptor.update(prev_item)

        prev_item = item

    if prev_item is not None:
        yield decryptor.update(prev_item) + decryptor.finalize()
    else:
        yield decryptor.finalize()
