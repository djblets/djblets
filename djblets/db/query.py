import functools
import re
from copy import deepcopy

from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db.models.manager import Manager
from django.db.models.query_utils import Q


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

                # Set the default result based on whether this is in ascending
                # or descending order.
                if match.group(1):
                    direction = -1
                else:
                    direction = 1

                attr_a = getattr(element_a, attr)
                attr_b = getattr(element_b, attr)

                if attr_a < attr_b:
                    return -direction
                elif attr_a > attr_b:
                    return direction

            return 0

        copy = self.clone()
        copy._data.sort(key=functools.cmp_to_key(compare))
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

            for key, value in kwargs.items():
                if getattr(item, key) != value:
                    match = False
                    break

            if match == return_matches:
                yield item


def get_object_or_none(cls, *args, **kwargs):
    """Return a model instance or None if one can not be found.

    Args:
        cls (type or django.db.models.manager.Manager):
            Either the model, a subclass of :py:class:`django.db.models.Model`,
            or its manager.

        *args (tuple):
            Arguments to pass to
            :py:meth:`~django.db.models.manager.Manger.get`.

        **kwargs (dict):
            Keyword arguments to pass to
            :py:meth:`~django.db.models.manager.Manger.get`.

    Returns:
        django.db.models.Model:
        The model instance, if it could be found, or :py:data:`None` otherwise.
    """
    if isinstance(cls, Manager):
        manager = cls
        cls = manager.model
    else:
        manager = cls._default_manager

    try:
        return manager.get(*args, **kwargs)
    except cls.DoesNotExist:
        return None


def prefix_q(prefix, q, clone=True):
    """Prefix a query expression.

    A :py:class:`query expression <django.db.models.query_utils.Q>` is used in
    :py:meth:`Manager.get <django.db.models.manager.Manager.get>` and
    :py:meth:`Manager.filter <django.db.models.manager.Manager.filter>`
    methods. These expressions are made of a tree of key-value pairs.

    Prefixing these expressions allows a query expression for one model to be
    used in a related model. The resulting prefixed expression will have every
    key in every key-value pair prefixed with the given prefix.

    By default, the query expression will be cloned. That is, the given query
    expression will not be modified and a prefixed copy will be returned.

    Args:
        prefix (unicode):
            The prefix to add to each member in the expression. This should be
            the name of a field and will be automatically suffixed by ``__``.

        q (django.db.models.query_utils.Q):
            The expression to prefix.

        clone (bool):
            Determine if the query should be cloned. If this is ``False``,
            ``q`` will be modified in place. This defaults to ``True``.

    Returns:
        django.db.models.query_utils.Q:
        The prefixed query expression.

    Example usage:
        .. code-block:: python

           from django.db import models
           from django.db.query_utils import Q
           from djblets.db.query import prefix_q

           # Given the following models:
           class A(models.Model):
               foo = models.IntegerField()
               bar = models.IntegerField()

           class B(models.Model):
               fk = models.ForeignKey(A, on_delete=models.CASCADE)
               baz = models.IntegerField()

           # And the following query expressions:
           a_q = Q(foo=1) & Q(bar=2)
           b_q = Q(fk__foo=1) & Q(fk__bar=2)

           # The following queries are equivalent:
           B.objects.filter(b_q)
           B.objects.filter(prefix_q('fk', a_q))
    """
    if clone:
        q = _clone_q(q)

    for i, child in enumerate(q.children):
        # django.utils.tree (which Q inherits from) stores its children as a
        # list. Each member is either an instance of Q (in the case of a nested
        # expression) or a tuple of the form (key_name, key_val).
        if isinstance(child, Q):
            prefix_q(prefix, child, False)
        else:
            assert type(q.children[i]) is tuple

            key, value = q.children[i]

            # This is going to be pure ASCII data (it's basically keyword
            # argument names). We'll use the native string type on Python.
            q.children[i] = (str('%s__%s' % (prefix, key)),
                             value)

    return q


def _clone_q(q):
    """Clone a query expression.

    This will clone a :py:class:`~django.db.models.Q` object and all children,
    allowing for modifications to be made on its tree.

    Args:
        q (django.db.models.Q):
            The query expression.

    Returns:
        django.db.models.Q:
        A clone of the query expression.
    """
    return deepcopy(q)
