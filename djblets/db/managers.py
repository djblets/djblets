"""Managers for Django database models."""

from __future__ import annotations

from typing import TypeVar

from django.db.models import Manager, Model
from housekeeping import ClassDeprecatedMixin

from djblets.deprecation import RemovedInDjblets80Warning


_T_co = TypeVar('_T_co', bound=Model, covariant=True)


class ConcurrencyManager(ClassDeprecatedMixin,
                         Manager[_T_co],
                         warning_cls=RemovedInDjblets80Warning):
    """A Django manager designed to work around database concurrency issues.

    This was used in very old versions of Django where the
    :py:meth:`get_or_create` method could raise IntegrityErrors due to
    concurrency. Since Django 1.0, the regular Manager has protections against
    this.

    Deprecated:
        6.0:
        Because this is no longer necessary, this class has been deprecated and
        will be removed in Djblets 8.0. Any subclasses should change to just
        inherit from :py:class:`django.db.models.Manager`.
    """
