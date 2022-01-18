"""Managers for Django database models."""

from django.db import models, IntegrityError


class ConcurrencyManager(models.Manager):
    """
    A class designed to work around database concurrency issues.
    """
    def get_or_create(self, **kwargs):
        """
        A wrapper around get_or_create that makes a final attempt to get
        the object if the creation fails.

        This helps with race conditions in the database where, between the
        original get() and the create(), another process created the object,
        causing us to fail. We'll then execute a get().

        This is still prone to race conditions, but they're even more rare.
        A delete() would have to happen before the unexpected create() but
        before the get().
        """
        try:
            return super(ConcurrencyManager, self).get_or_create(**kwargs)
        except IntegrityError:
            kwargs.pop('defaults', None)
            return self.get(**kwargs)
