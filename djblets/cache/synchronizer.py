from __future__ import unicode_literals

import time
from datetime import datetime

from django.core.cache import cache
from djblets.cache.backend import make_cache_key


class GenerationSynchronizer(object):
    """Manages the synchronization of generation state across processes.

    This is a utility class that makes it easy for consumers to synchronize
    a generation ID between processes and servers. This ID can be used to
    check whether a process has the latest version of some data, updating
    if the version it has is expired.

    Callers should create a :py:class:`GenerationSynchronizer` with a stable
    cache key, which will be used for communication between processes/servers.
    The initial generation number will be fetched, or created if one does not
    already exist.

    When the caller has updated something in the state, it must call
    :py:meth:`mark_updated`. This will bump the synchronization generation
    number, which will invalidate other processes.

    Other callers, upon noticing that their state is expired (through
    :py:meth:`is_expired`) can re-fetch or re-compute the data needed and
    then call :py:meth:`refresh` to refresh the instance's counter from the
    cache.

    Attributes:
        sync_gen (int):
            The synchronization generation number last fetched or set by
            this instance.

        cache_key (unicode):
            The synchronization cache key.
    """

    def __init__(self, cache_key, normalize_cache_key=True):
        """Initialize the synchronizer.

        Args:
            cache_key (unicode):
                The base cache key used for all synchronization. This will be
                normalized by
                :py:func:`~djblets.cache.backends.make_cache_key`.

            normalize_cache_key (bool, optional):
                Whether to normalize the cache key. Normalizing it will
                ensure it can fit within the key length constraints, and
                reduces changes of colliding with keys from other services.
                This is enabled by default.
        """
        if normalize_cache_key:
            cache_key = make_cache_key(cache_key)

        self.cache_key = cache_key
        self.sync_gen = None

        self._fetch_or_create_sync_gen()

    def is_expired(self):
        """Return whether the current state has expired.

        Returns:
            bool:
            ``True`` if the state has expired. ``False`` if this has the
            latest cached generation.
        """
        sync_gen = self._get_latest_sync_gen()

        return (sync_gen is None or
                (type(sync_gen) is int and sync_gen != self.sync_gen))

    def refresh(self):
        """Refresh the generation ID from cache.

        This should be called after having updated to the latest state.
        """
        self._fetch_or_create_sync_gen()

    def clear(self):
        """Clear the cached generation ID.

        This will expire all existing caches and force all processes to
        re-fetch and store the cache state.
        """
        cache.delete(self.cache_key)

    def mark_updated(self):
        """Mark the synchronized state as having been updated.

        All other processes will find their state expired, and will need to
        re-update.
        """
        try:
            self._increment_sync_gen()
        except ValueError:
            self._fetch_or_create_sync_gen()

    def _increment_sync_gen(self):
        """Increment the synchronization generation ID."""
        self.sync_gen = cache.incr(self.cache_key)

    def _fetch_or_create_sync_gen(self):
        """Return or create a new synchronization generation ID.

        If one already exists in the cache, it will be returned. Otherwise,
        the a new generation ID will be stored.
        """
        sync_gen = int(time.mktime(datetime.now().timetuple()))

        if cache.add(self.cache_key, sync_gen):
            self.sync_gen = sync_gen
        else:
            self.sync_gen = self._get_latest_sync_gen()

    def _get_latest_sync_gen(self):
        """Return the latest synchronization generation ID.

        Returns:
            int: The latest generation ID from cache.
        """
        return cache.get(self.cache_key)
