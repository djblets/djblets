from __future__ import unicode_literals

import re

import django
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db.models.query import QuerySet
from django.db.models.manager import Manager
from django.utils import six


class LocalDataQuerySet(object):
    """A QuerySet that operates on generic data provided by the caller.

    This can be used in some circumstances when code requires a QuerySet,
    but where the data doesn't come from the database. The caller can
    instantiate one of these and provide it.

    This doesn't perform full support for all of QuerySet's abilities. It
    does, however, support the following basic functions:

    * all
    * clone
    * count
    * exclude
    * filter
    * get
    * order_by
    * prefetch_related
    * select_related

    As well as the operators expected by consumers of QuerySet, such as
    __len__ and __iter__.

    This is particularly handy with WebAPIResource.
    """

    PROPERTY_REGEX = re.compile(r'(-?)(\w+)')

    def __init__(self, data):
        self._data = data

    def all(self):
        """Returns a cloned copy of this queryset."""
        return self.clone()

    def clone(self):
        """Returns a cloned copy of this queryset."""
        return LocalDataQuerySet(list(self._data))

    def count(self):
        """Returns the number of items in this queryset."""
        return len(self._data)

    def exclude(self, **kwargs):
        """Returns a queryset excluding items from this queryset.

        The result will be a LocalDataQuerySet that contains all items from
        this queryset that do not contain attributes with values matching
        those that were passed to this function as keyword arguments.
        """
        return LocalDataQuerySet(
            list(self._filter_or_exclude(return_matches=False, **kwargs)))

    def filter(self, **kwargs):
        """Returns a queryset filtering items from this queryset.

        The result will be a LocalDataQuerySet that contains all items from
        this queryset that contain attributes with values matching those that
        were passed to this function as keyword arguments.
        """
        return LocalDataQuerySet(
            list(self._filter_or_exclude(return_matches=True, **kwargs)))

    def get(self, **kwargs):
        """Returns a single result from this queryset.

        This will return a single result from the list of items in this
        queryset. If keyword arguments are provided, they will be used
        to filter the queryset down.

        There must be only one item in the queryset matching the given
        criteria, or a MultipleObjectsReturned will be raised. If there are
        no items, then an ObjectDoesNotExist will be raised.
        """
        clone = self.filter(**kwargs)
        count = len(clone)

        if count == 1:
            return clone[0]
        elif count == 0:
            raise ObjectDoesNotExist('%s matching query does not exist.'
                                     % self._data.__class__.__name__)
        else:
            raise MultipleObjectsReturned(
                'get() returned more than one %s -- it returned %s!'
                % (self._data.__class__.__name__, count))

    def order_by(self, *attrs, **kwargs):
        """Returns a queryset ordering items by the specified attributes.

        The result will be a LocalDataQuerySet that contains all items from
        this queryset ordered by the attributes specified. If multiple
        attributes are specified, the items are sorted by the first attribute
        and ties are broken by the other following attributes.

        All items are sorted in ascending order. To specify a descending
        order, an attribute must have a '-' prepended to the name, such as
        `-attribute_A`.
        """
        def compare(element_a, element_b):
            """Compare two elements of the queryset."""
            for attr in attrs:
                match = self.PROPERTY_REGEX.search(attr)
                attr = match.group(2)
                direction = 1

                if match.group(1):
                    direction = -1

                attr_a = getattr(element_a, attr)
                attr_b = getattr(element_b, attr)
                direction *= cmp(attr_a, attr_b)

                if direction:
                    return direction

            return 0

        copy = self.clone()
        copy._data.sort(cmp=compare)
        return copy

    def prefetch_related(self, *args, **kwargs):
        """Stub for compatibility with QuerySet.prefetch_related.

        This will simply return a clone of this queryset.
        """
        return self.clone()

    def select_related(self, *args, **kwargs):
        """Stub for compatibility with QuerySet.select_related.

        This will simply return a clone of this queryset.
        """
        return self.clone()

    def __contains__(self, i):
        return i in self._data

    def __getitem__(self, i):
        return self._data[i]

    def __getslice__(self, i, j):
        return self._data[i:j]

    def __iter__(self):
        for i in self._data:
            yield i

    def __len__(self):
        return len(self._data)

    def _filter_or_exclude(self, return_matches=True, **kwargs):
        for item in self:
            match = True

            for key, value in six.iteritems(kwargs):
                if getattr(item, key) != value:
                    match = False
                    break

            if match == return_matches:
                yield item


class _Django16ChainableSelectRelatedQuerySet(QuerySet):
    """A special QuerySet that allows for chaining select_related calls.

    This is used internally by :py:func:`chainable_select_related_queryset`
    to allow for chaining
    :py:meth:`~django.db.models.query.QuerySet.select_related` calls on
    Django 1.6. This is not used on newer versions of Django.

    This class should not be used directly.
    """

    def select_related(self, *fields):
        """Return a new QuerySet instance that will select related objects.

        If fields are specified, they must be
        :ref:`~django.db.models.ForeignKey` fields.

        If ``select_related(None)`` is called, the list is cleared.

        Unlike the standard version in Django 1.6, subsequent calls to this
        method will not override the previous list.

        Args:
            *fields (tuple, optional):
                Specific fields to select.

        Returns:
            django.db.models.query.QuerySet:
            The resulting queryset.
        """
        obj = (
            super(_Django16ChainableSelectRelatedQuerySet, self)
            .select_related(*fields)
        )

        if (fields and fields != (None,) and
            self.query.select_related and
            isinstance(self.query.select_related, dict)):
            self._merge_dicts(obj.query.select_related,
                              self.query.select_related)

        return obj

    def _merge_dicts(self, dest_dict, source_dict):
        """Recursively merge a source dictionary into a destination dictionary.

        Args:
            dest_dict (dict):
                The dictionary to merge into.

            source_dict (dict):
                The dictionary to merge from.
        """
        for key, value in six.iteritems(source_dict):
            if isinstance(value, dict):
                self._merge_dicts(dest_dict.setdefault(key, {}), value)
            else:
                dest_dict[key] = value


def chainable_select_related_queryset(queryset):
    """Allow for chaining select_related calls on a queryset.

    This is a workaround for Django 1.6's inability to chain calls to
    :py:meth:`QuerySet.select_related()
    <django.db.models.query.QuerySet.select_related>`. When using Django 1.6,
    the returned queryset will be a special type that handles the chaining.
    On Django 1.7 and higher, querysets support this natively, so this function
    will just return the queryset as-is.

    Args:
        queryset (django.db.models.query.QuerySet):
            The queryset to make chainable.

    Returns:
        django.db.models.query.QuerySet:
        A queryset that allows for chaining.
    """
    if django.VERSION[:2] == (1, 6):
        # Django 1.6 needs this helper to allow for chainable select_related()
        # calls.
        queryset = queryset._clone(
            klass=_Django16ChainableSelectRelatedQuerySet)

    return queryset


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
