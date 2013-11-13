from __future__ import unicode_literals

from django.db.models.manager import Manager


def get_object_or_none(klass, *args, **kwargs):
    if isinstance(klass, Manager):
        manager = klass
        klass = manager.model
    else:
        manager = klass._default_manager

    try:
        return manager.get(*args, **kwargs)
    except klass.DoesNotExist:
        return None
