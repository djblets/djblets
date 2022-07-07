"""Compatibility for collections ABCs removed in Python 3.10.

Note that this module is not considered API-stable. Changes may be made that
remove or alter functionality in the future. Please use at your own risk.

Version Added:
    2.2.4
"""

import sys


if sys.version_info >= (3, 10):
    # Python 3.10+ removed a bunch of aliases from the collections module.
    # Unfortunately, Django 1.11 and nose still rely on these.
    try:
        from collections import Callable
    except ImportError:
        import collections
        import collections.abc

        collections.Callable = collections.abc.Callable
        collections.Iterable = collections.abc.Iterable
        collections.Iterator = collections.abc.Iterator
        collections.MutableMapping = collections.abc.MutableMapping
        collections.Mapping = collections.abc.Mapping
        collections.Sequence = collections.abc.Sequence
