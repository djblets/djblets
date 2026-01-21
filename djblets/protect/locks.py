"""Locking implementations.

Version Added:
    5.3
"""

from __future__ import annotations

import logging
import random
import time
from typing import TYPE_CHECKING
from uuid import uuid4

from django.core.cache import cache

from djblets.cache.backend import make_cache_key

if TYPE_CHECKING:
    from collections.abc import Sequence

    from typing_extensions import Self


logger = logging.getLogger(__name__)


class CacheLock:
    """A distributed lock backed by a cache.

    This is used to acquire a lock associated with a key, either blocking or
    immediately returning if a lock can't immediately be acquired.

    Locks can be used by code that needs to run only once across multiple
    processes or servers. They can be used directly or passed to
    :py:func:`cache_memoize` or :py:func:`cache_memoize_iter` to wrap any
    cache updates in a lock.

    Locks have an expiration time in order to prevent deadlocks. Setting
    this higher can result in longer wait periods if the lock fails to be
    released. Setting it lower can result in locks automatically releasing
    prematurely. It defaults to an expiration of 30 seconds.

    The interface is kept compatible with :py:class:`threading.Lock`, but
    with additional capabilities for updating expiration times and setting
    default blocking and timeout behavior during construction.

    Note:
        This lock is subject to the limitations of the cache system. The
        lock may be purged from cache without notice, and it's possible
        for one client to overwrite another's lock depending on timing
        issues or scaling setup.

        For these reasons, this lock should be considered an imperfect,
        lossy lock. Callers can use it to help prevent multiple operations
        from occurring at once, but they should be tolerant of that
        possibility and designed accordingly.

        CacheLocks are also not thread-safe. Do not reuse the same lock
        across threads.

    Version Added:
        5.3
    """

    ######################
    # Instance variables #
    ######################

    #: Whether a lock is currently acquired by this instance.
    acquired: bool

    #: Whether this lock will block for a period of time to be acquired.
    blocking: bool

    #: The full cache key used for the lock.
    #:
    #: This may be set lazily after the lock is constructed, but must be
    #: set prior to acquiring a lock.
    full_cache_key: str

    #: The max amount of time a lock can be claimed.
    lock_expiration_secs: int

    #: The time to sleep between checking for a lock to be released.
    retry_secs: float

    #: The max time to wait for a lock to be released.
    #:
    #: If -1, the lock will wait indefinitely.
    timeout_secs: float

    #: The cached token value associated with this lock instance.
    token: str

    #: The expected timestamp for lock expiration.
    _lock_expires_time: float

    def __init__(
        self,
        key: str | Sequence[str] = '',
        *,
        blocking: bool = True,
        lock_expiration_secs: int = 30,
        retry_secs: float = 0.25,
        timeout_secs: float = -1,
    ) -> None:
        """Initialize the lock.

        Args:
            key (str or list of str):
                The key to use in the cache.

                This may be a sequence of strings, which will take care of
                serializing each component to help avoid key injection
                attacks.

                This will be passed to :py:func:`make_cache_key` to construct
                a full cache key.

            blocking (bool, optional):
                Whether this lock will block for a period of time to be
                acquired.

            lock_expiration_secs (int, optional):
                The max amount of time a lock can be claimed.

                After this period, the lock will be automatically released.

            retry_secs (float, optional):
                The time to sleep between checking for a lock to be released.

                The caller should set this to be less than the timeout, but
                note that timeouts can be extended or reduced by the lock
                owner.

                An additional jitter between 0-25% of the retry time will be
                added to reduce stampede issues.

            timeout_secs (float, optional):
                The max time to wait for a lock to be released.

                If -1, the lock will block indefinitely.

        Raises:
            ValueError:
                A provided argument had an invalid value.
        """
        if timeout_secs != -1 and timeout_secs <= 0:
            raise ValueError('timeout_secs must be -1 or a positive value.')

        if retry_secs <= 0:
            raise ValueError('retry_secs must be a positive value.')

        self.blocking = blocking
        self.retry_secs = retry_secs
        self.timeout_secs = timeout_secs
        self.lock_expiration_secs = lock_expiration_secs

        self.acquired = False
        self.token = ''
        self._lock_expires_time = 0

        if key:
            self.full_cache_key = make_cache_key(key)
        else:
            self.full_cache_key = ''

    def __del__(self) -> None:
        """Handle destruction of the cache lock.

        If this lock was garbage collected without being released, an
        exception will be logged indicating an implementation problem
        with the caller's use of the lock.
        """
        if self.acquired:
            logger.error('Cache lock "%s" was garbage collected without '
                         'being released! The caller must be careful to '
                         'keep this lock around until it is released.',
                         self.full_cache_key)

    def locked(self) -> bool:
        """Return whether the lock is acquired.

        This wraps :py:attr:`acquired`, and provides API compatibility with
        :py:class:`threading.Lock` and other Python lock objects.

        Returns:
            bool:
            ``True`` if the lock has been acquired. ``False`` if it has not.
        """
        return self.acquired

    def acquire(
        self,
        blocking: (bool | None) = None,
        timeout: (float | None) = None,
    ) -> bool:
        """Acquire a lock.

        If there's already an existing lock in cache, this will either
        return immediately or wait for the lock to be released, depending
        on :py:attr:`blocking`.

        If waiting, this will wait for a total time specified by
        :py:attr:`timeout_secs`, checking every :py:attr:`retry_secs`.

        Waiting uses the monotonic clock, so it's not affected by changes
        to the system clock.

        To ensure API compatibility with :py:class:`threading.Lock` and
        other Python lock objects, this method can also take arguments that
        override the values provided during construction.

        Returns:
            bool:
            ``True`` if the lock could be acquired (even after waiting).
            ``False`` if it could not (only if :py:attr:`blocking` is
            ``False``).

        Raises:
            RuntimeError:
                An attempt was made to acquire a lock that was already
                acquired.

            TimeoutError:
                The lock could not be acquired due to the wait time expiring.

            ValueError:
                A cache key was never set for the lock.
        """
        full_cache_key = self.full_cache_key

        if not full_cache_key:
            raise ValueError('A cache key for the lock must be provided.')

        if self.acquired:
            raise RuntimeError(
                'acquire() is not reentrant for %s instance %s'
                % (type(self).__name__, id(self))
            )

        token = str(uuid4())
        self.token = token

        if blocking is None:
            blocking = self.blocking

        if timeout is None:
            timeout = self.timeout_secs

        retry_secs = self.retry_secs
        lock_expiration_secs = self.lock_expiration_secs

        start = time.monotonic()

        while True:
            if cache.add(full_cache_key, token, lock_expiration_secs):
                lock_expires_time = time.monotonic() + lock_expiration_secs

                logger.debug('Acquired cache lock "%s" with token "%s" for '
                             '%s seconds (monotonic expiration = %s, '
                             'estimated timestamp = %s)',
                             full_cache_key, token, lock_expiration_secs,
                             lock_expires_time,
                             time.time() + lock_expiration_secs)

                self.acquired = True
                self._lock_expires_time = lock_expires_time

                return True

            if not blocking:
                # The caller doesn't want to block waiting for a request,
                # so return immediately.
                return False

            # Check if we've timed out waiting for a lock.
            if (timeout != -1 and
                time.monotonic() - start >= timeout):
                logger.warning('Timed out waiting for cache lock "%s" '
                               '(token "%s") for %s seconds',
                               self.full_cache_key, token, timeout)

                raise TimeoutError(
                    f'Timed out waiting for lock: {full_cache_key}'
                )

            # Wait before retrying, and add random jitter to the retry time
            # to avoid overloading the cache server with concurrent checks
            # during a stampede.
            time.sleep(retry_secs + random.uniform(0, retry_secs * 0.25))

    def update_expiration(
        self,
        lock_expiration_secs: (int | None) = None,
    ) -> None:
        """Update the expiration of the lock.

        This can be used to keep the lock opened a bit longer, in case
        there's work in progress, or to shorten the lock.

        Args:
            lock_expiration_secs (int, optional):
                A specific number of seconds to set for the new expiration.

                If not provided, the original expiration time in seconds
                will be used.

        Raises:
            AssertionError:
                The caller called this without first acquiring a lock.
        """
        if not self.acquired:
            raise AssertionError(
                'Cannot extend a lock that has not been acquired.'
            )

        if lock_expiration_secs is None:
            lock_expiration_secs = self.lock_expiration_secs

        key = self.full_cache_key
        token = self.token

        if cache.touch(key, lock_expiration_secs):
            lock_expires_time = time.monotonic() + lock_expiration_secs

            logger.debug('Extended cache lock "%s" (token "%s") to '
                         '%s seconds (monotonic expiration = %s, '
                         'estimated timestamp = %s)',
                         key, token, lock_expiration_secs,
                         lock_expires_time,
                         time.time() + lock_expiration_secs)

            self._lock_expires_time = lock_expires_time
        else:
            # The key fell out of cache. Attempt to re-add it.
            logger.warning('Cache lock "%s" (token "%s") fell out of cache. '
                           'The lock is no longer valid.',
                           key, token)

    def release(self) -> None:
        """Release a lock.

        If the lock is still valid, it will be removed from the cache,
        allowing something else to acquire the lock.

        If a lock is not acquired, this will raise an exception.

        Raises:
            RuntimeError:
                This was called on a lock that was not acquired.
        """
        if not self.acquired:
            raise RuntimeError('Cannot release a lock that was not acquired.')

        self.acquired = False

        key = self.full_cache_key
        token = self.token
        lock_expiration_secs = self.lock_expiration_secs

        # First check if we're past the expiration window of the lock.
        #
        # If we're past the expiration window (or close enough, given clock
        # inconsistencies on servers), then let the lock expire and don't
        # try to delete it explicitly.
        expired = time.monotonic() > self._lock_expires_time

        if not expired:
            # Attempt to bump the expiration for the key. If it timed out and
            # we lost the key, then the worst that happens is the expiration
            # for the new owner's key is bumped up. It should help avoid
            # deleting that owner's key, in this case.
            expired = not cache.touch(key, lock_expiration_secs)

            if not expired and cache.get(key) == token:
                # The lock is still acquired. Delete it.
                cache.delete(key)

        if expired:
            logger.debug('Released cache lock "%s" (token "%s"), which '
                         'already expired from cache',
                         key, token)
        else:
            logger.debug('Released cache lock "%s" (token "%s")',
                         key, token)

    def __enter__(self) -> Self:
        """Enter the context manager.

        This will acquire the lock, if possible, and pass the result as
        the context. Once the context manager is exited, the lock will be
        released.

        This is equivalent to calling :py:meth:`acquire`.

        Context:
            CacheLock:
            The cache lock instance.

        Raises:
            TimeoutError:
                The lock could not be acquired due to the wait time expiring.

            ValueError:
                A cache key was never set for the lock.
        """
        self.acquire()

        return self

    def __exit__(self, *args, **kwargs) -> None:
        """Exit the context manager.

        This will release the lock, if one was acquired.

        Args:
            *args (tuple, unused):
                Unused positional arguments.

            **kwargs (dict, unused):
                Unused keyword arguments.
        """
        if self.acquired:
            self.release()

    def __repr__(self) -> str:
        """Return a string representation of the cache lock object.

        Returns:
            str:
            The string representation.
        """
        cls_name = type(self).__name__

        return (
            f'<{cls_name}(blocking={self.blocking!r},'
            f' full_cache_key={self.full_cache_key!r},'
            f' token={self.token!r})>'
        )
