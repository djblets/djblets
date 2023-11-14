"""Utilities for comparing executed queries to expectations.

These are used internally for unit testing, but can also be useful when
instrumenting code.

Version Added:
    3.4
"""

from __future__ import annotations

import operator
import re
from contextlib import contextmanager
from pprint import pformat
from typing import (Any, Callable, Dict, Iterator, List, Optional, Sequence,
                    Set, TYPE_CHECKING, Tuple, Type, TypeVar, Union, cast)

from django.db.models import Q
from django.db.models.query import MAX_GET_RESULTS
from django.db.models.sql.query import Query as SQLQuery
from django.db.models.sql.subqueries import AggregateQuery
from django.utils.encoding import force_str
from typing_extensions import Literal, NotRequired, TypeAlias, TypedDict

from djblets.db.query_catcher import catch_queries
from djblets.deprecation import RemovedInDjblets50Warning

if TYPE_CHECKING:
    from django.db.models import Model
    from django.db.models.expressions import BaseExpression

    from djblets.db.query_catcher import ExecutedQueryInfo

    _T = TypeVar('_T')


_ws_re = re.compile(r'\s+')


class QueryMismatchedAttr(TypedDict):
    """An attribute for a query that failed to meet expectations.

    Version Added:
        3.4
    """

    #: The name of the attribute.
    name: str

    #: The serialized version of the value from the executed query.
    executed_value: NotRequired[str]

    #: The serialized version of the value from the expected query.
    expected_value: NotRequired[str]

    #: The raw value from the executed query.
    raw_executed_value: NotRequired[Any]

    #: The raw value from the expected query.
    raw_expected_value: NotRequired[Any]

    #: The list of failures in a subquery stored in this attribute.
    inner_mismatched_attrs: NotRequired[List[QueryMismatchedAttr]]


class QueryMismatch(TypedDict):
    """Information on a mismatched query.

    Version Added:
        3.4
    """

    #: The query that was executed.
    executed_query: SQLQuery

    #: The list of mismatched attributes in this query.
    mismatched_attrs: List[QueryMismatchedAttr]

    #: The 0-based index of the executed query that this represents.
    index: int

    #: An optional note describing this query.
    note: Optional[str]

    #: The generated SQL for the query.
    query_sql: List[str]

    #: Lines of traceback showing where this query was executed.
    traceback: List[str]


class ExpectedQuery(TypedDict):
    """An expected query for a query assertion.

    This is used for :py:meth:`TestCase.assertQueries`.

    While this type is new, the documented keys (unless otherwise noted) were
    introduced in Djblets 2.3.1.

    Version Added:
        3.4
    """

    #: A custom note for the query, to help with query inspection.
    #:
    #: Version Added:
    #:     3.4
    __note__: NotRequired[str]

    #: A dictionary containing applied annotations.
    #:
    #: Keys are destination attribute names, and values are the annotation
    #: instances.
    #:
    #: The default is empty.
    annotations: NotRequired[Dict[str, BaseExpression]]

    #: Whether :py:meth:`django.db.models.query.QuerySet.distinct` was used.
    #:
    #: The default is ``False``.
    distinct: NotRequired[bool]

    #: A list of distinct fields.
    #:
    #: These are field names passed to
    #: :py:meth:`django.db.models.query.QuerySet.distinct`.
    #:
    #: The default is empty.
    distinct_fields: NotRequired[Tuple[str, ...]]

    #: Extra state passed in the queryset.
    #:
    #: This is state passed in calls to
    #: :py:meth:`django.db.models.query.QuerySet.extra` when using
    #: ``select`` and ``select_params``.
    #:
    #: Each key maps to a key in ``select``, and each value is a
    #: tuple containing the value in ``select`` and the corresponding
    #: value (if any) in ``select_params``.
    #:
    #: Values are normalized to collapse and strip whitespace, to
    #: help with comparison.
    #:
    #: The default is empty.
    extra: NotRequired[Dict[str, Any]]

    #: Extra order-by values.
    #:
    #: This is state passed in calls to
    #: :py:meth:`django.db.models.query.QuerySet.extra` when using
    #: ``order_by``.
    #:
    #: The default is empty.
    extra_order_by: NotRequired[Sequence[str]]

    #: Extra tables for the query.
    #:
    #: This is state passed in calls to
    #: :py:meth:`django.db.models.query.QuerySet.extra` when using ``tables``.
    #:
    #: The default is empty.
    extra_tables: NotRequired[Sequence[str]]

    #: The grouping of results.
    #:
    #: This determines whether no fields will be grouped (``None``), all
    #: fields will be grouped (``True``), or specific expressions/field
    #: names are grouped (a tuple).
    #:
    #: This is influenced by using
    #: :py:meth:`django.db.models.query.QuerySet.annotate`.
    #:
    #: The default is ``None``.
    group_by: NotRequired[Optional[Union[bool, Tuple[str, ...]]]]

    #: The inner query information to compare, for aggregate queries.
    #:
    #: Version Added:
    #:     3.4
    inner_query: NotRequired[Optional[ExpectedQuery]]

    #: The value for a ``LIMIT`` in the ``SELECT``.
    #:
    #: This will generally only need to be supplied if testing a query using
    #: :py:meth:`QuerySet.exists() <django.db.models.query.QuerySet.exists>`
    #: or when slicing results.
    #:
    #: Django itself sometimes uses a default of ``None`` and sometimes a
    #: default currently of ``21`` (this exact value, and when it's used, is
    #: considered an implementation detail in Django). Both of these will
    #: match a caller-provided ``limit`` value of ``None``.
    #:
    #: The default is ``None``.
    limit: NotRequired[Optional[int]]

    #: The model backing the queryset.
    #:
    #: This represents the results that would be returned or altered by the
    #: query.
    model: NotRequired[Type[Model]]

    #: The number of tables joined.
    #:
    #: The default is 0.
    num_joins: NotRequired[int]

    #: The value for an ``OFFSET`` in the ``SELECT``.
    #:
    #: The default is 0.
    offset: NotRequired[int]

    #: The specific fields being fetched, or ``None`` if fetching all fields.
    #:
    #: The default is ``None``.
    only_fields: NotRequired[Set[str]]

    #: The ordering criteria.
    #:
    #: The default is empty.
    order_by: NotRequired[Tuple[str, ...]]

    #: Whether this is a select-for-update operation.
    #:
    #: The default is ``False``.
    select_for_update: NotRequired[bool]

    #: The table names involved in a select-related operation.
    #:
    #: These are the names passed to
    #: :py:meth:`django.db.models.query.QuerySet.select_related`. If called
    #: without any parameters, this would be ``True``.
    select_related: NotRequired[Union[Literal[True], Set[str]]]

    #: Whether this is considered a subquery of another query.
    #:
    #: The default is ``False``.
    subquery: NotRequired[bool]

    #: The tables involved in the query.
    #:
    #: The default is the model's table name.
    tables: NotRequired[Set[str]]

    #: The query type.
    #:
    #: This would be one of ``DELETE``, ``INSERT``, ``SELECT``, or ``UPDATE``.
    #:
    #: The default is ``SELECT``.
    type: NotRequired[str]

    #: A list of specified fields to return as values.
    #:
    #: These are values passed in
    #: :py:meth:`~django.db.models.query.QuerySet.values` or
    #: :py:meth:`~django.db.models.query.QuerySet.values_list`.
    values_select: NotRequired[Tuple[str, ...]]

    #: The query expression objects used to represent the filter on the query.
    #:
    #: These are normalized to filter out empty or unnecessarily-nested
    #: queries, to ease comparison.
    where: NotRequired[Q]


#: A type representing list of expected queries.
#:
#: Note:
#:     This type allows either a :py:meth:`ExpectedQuery` or a plain
#:     dictionary of string-based keys. This is because with pyright (as of
#:     1.1.332), the type of the right-hand-side of a ``+=`` operation cannot
#:     be inferred. That makes it difficult to dynamically build expected
#:     queries.
#:
#:     Until/unless the situation improves, we aim for an
#:     :py:meth:`ExpectedQuery` but allow a plain dictionary.
#:
#: Version Added:
#:     3.4
ExpectedQueries: TypeAlias = List[Union[ExpectedQuery,
                                        Dict[str, Any]]]


class CompareQueriesContext(TypedDict):
    """Context for compared query results.

    This is provided and populated when using :py:func:`compare_queries`.

    Version Added:
        3.4
    """

    #: The number of queries that were executed.
    num_executed_queries: int

    #: The number of queries that were expected.
    num_expected_queries: int

    #: Whether the number of executed and expected queries are different.
    query_count_mismatch: bool

    #: The list of query expectation failures.
    query_mismatches: List[QueryMismatch]


@contextmanager
def compare_queries(
    queries: Sequence[Union[ExpectedQuery,
                            Dict[str, Any]]],
    *,
    num_statements: Optional[int] = None,
    with_tracebacks: bool = False,
    traceback_size: int = 15,
    _check_subqueries: Optional[bool] = True,
) -> Iterator[CompareQueriesContext]:
    """Assert the number and complexity of queries.

    This provides advanced checking of queries, allowing the caller to
    match filtering, JOINs, ordering, selected fields, and more.

    This takes a list of dictionaries with query information. Each
    contains the keys in :py:class:`ExpectedQuery`.

    Version Added:
        3.4

    Args:
        queries (list of ExpectedQuery):
            The list of query dictionaries to compare executed queries
            against.

        num_statements (int, optional):
            The numbre of SQL statements executed.

            This defaults to the length of ``queries``, but callers may
            need to provide an explicit number, as some operations may add
            additional database-specific statements (such as
            transaction-related SQL) that won't be covered in ``queries``.

        with_tracebacks (bool, optional):
            If enabled, tracebacks for queries will be included in
            results.

        tracebacks_size (int, optional):
            The size of any tracebacks, in number of lines.

            The default is 15.

        _check_subqueries (bool, optional):
            Whether to check subqueries.

            This is considered internal and should not be used outside of
            Djblets.

    Returns:
        ...
    """
    assert isinstance(queries, list)

    if num_statements is None:
        num_statements = len(queries)

    comparator_ctx = CompareQueriesContext(
        num_executed_queries=0,
        num_expected_queries=0,
        query_count_mismatch=False,
        query_mismatches=[])

    with catch_queries() as ctx:
        yield comparator_ctx

    executed_queries = ctx.executed_queries
    queries_to_qs = ctx.queries_to_qs

    # Now we can compare numbers.
    num_queries = len(queries)
    num_executed_queries = len(executed_queries)

    # Make sure we received the expected number of queries.
    if num_queries != num_executed_queries:
        if num_queries < num_executed_queries:
            queries += [
                ExpectedQuery()
                for _i in range(num_executed_queries - num_queries)
            ]
        elif num_queries > num_executed_queries:
            queries = queries[:num_executed_queries]

    # Go through each matching Query and compare state.
    query_mismatches: List[QueryMismatch] = []
    queries_iter = enumerate(zip(cast(Sequence[ExpectedQuery], queries),
                                 executed_queries))

    for i, (query_info, executed_query_info) in queries_iter:
        query_sql = executed_query_info['sql']

        # If this query didn't generate any SQL, then we want to skip it.
        if not query_sql:
            continue

        executed_query = executed_query_info['query']
        mismatched_attrs = _check_query(
            executed_query=executed_query,
            executed_query_info=executed_query_info,
            expected_query_info=query_info,
            check_subqueries=_check_subqueries,
            queries_to_qs=queries_to_qs)

        if mismatched_attrs:
            query_mismatches.append({
                'executed_query': executed_query,
                'mismatched_attrs': mismatched_attrs,
                'index': i,
                'note': query_info.get('__note__'),
                'query_sql': query_sql,
                'traceback': executed_query_info['traceback'],
            })

    # Update the context for the caller to examine.
    comparator_ctx.update({
        'num_executed_queries': num_executed_queries,
        'num_expected_queries': num_queries,
        'query_count_mismatch': num_queries != num_executed_queries,
        'query_mismatches': query_mismatches,
    })


def _check_expectation(
    name: str,
    *,
    mismatched_attrs: List[QueryMismatchedAttr],
    expected_value: _T,
    executed_value: _T,
    match_func: Callable[[_T, _T], bool] = operator.__eq__,
    format_expected_value_func: Callable[[_T], str] = pformat,
    format_executed_value_func: Callable[[_T], str] = pformat,
) -> None:
    """Check the expectation for a query attribute.

    This will compare the query attribute values between the expected and
    executed queries, storing a mismatch in ``mismatched_attrs`` containing
    raw and human-readable versions of the values.

    Version Added:
        3.4

    Args:
        name (str):
            The name of the attribute to check.

        mismatched_attrs (list of dict):
            The list of mismatched attributes to apapend to if there's a
            mismatch.

        expected_value (object):
            The expected value for the attribute.

        executed_value (object):
            The executed value for the attribute.

        match_func (callable, optional):
            The function to call to compare the values.

            This defaults to an equality check.

        format_expected_value_func (callable, optional):
            The function to format the expected value for the human-readable
            representation.

            This defaults to :py:func:`pprint.pformat`.

        format_executed_value_func (callable, optional):
            The function to format the executed value for the human-readable
            representation.

            This defaults to :py:func:`pprint.pformat`.
    """
    if not match_func(expected_value, executed_value):
        mismatched_attrs.append({
            'name': name,
            'executed_value': format_executed_value_func(
                executed_value),
            'expected_value': format_expected_value_func(
                expected_value),
            'raw_executed_value': executed_value,
            'raw_expected_value': expected_value,
        })


def _check_query(
    *,
    executed_query: SQLQuery,
    executed_query_info: ExecutedQueryInfo,
    expected_query_info: ExpectedQuery,
    check_subqueries: Optional[bool],
    queries_to_qs: Dict[SQLQuery, Q],
) -> List[QueryMismatchedAttr]:
    """Check a query for expectations.

    This will compare attributes on an executed query to an expected query
    and determine if there are any mismatches.

    Args:
        executed_query (django.db.models.sql.query.Query):
            The executed query to compare.

        executed_query_info (djblets.db.query_catcher.ExecutedQueryInfo):
            Information on the executed query to use for comparison.

        expected_query_info (dict):
            Information on the expectations for the query from the caller.

        check_subqueries (bool):
            Whether to check for subqueries.

            This is here for backwards-compatibility and will be removed in
            a future version.

        queries_to_qs (dict):
            A dictionary mapping queries to Q objects.

    Returns:
        list of dict:
        A list of mismatched attributes for this query.

        This will be empty if there are no mismatches.
    """
    mismatched_attrs: List[QueryMismatchedAttr] = []

    executed_model = executed_query.model
    assert executed_model is not None

    expected_model = expected_query_info.get('model')

    executed_table_name = executed_model._meta.db_table
    executed_reffed_tables: Set[str] = {
        _table_name
        for _table_name in executed_query.alias_map.keys()
        if executed_query.alias_refcount.get(_table_name, 0) > 0
    }

    # Check 'model'.
    _check_expectation(
        'model',
        mismatched_attrs=mismatched_attrs,
        expected_value=expected_model,
        executed_value=executed_model,
        match_func=operator.is_)

    # Check the query type.
    _check_expectation(
        'type',
        mismatched_attrs=mismatched_attrs,
        expected_value=expected_query_info.get('type', 'SELECT'),
        executed_value=executed_query_info['type'].value)

    # Check the fields that are easy to compare.
    for key, default in (('annotations', {}),
                         ('distinct', False),
                         ('distinct_fields', ()),
                         ('extra_order_by', ()),
                         ('extra_tables', ()),
                         ('group_by', None),
                         ('order_by', ()),
                         ('select_for_update', False),
                         ('subquery', False),
                         ('values_select', ())):
        _check_expectation(
            key,
            mismatched_attrs=mismatched_attrs,
            expected_value=expected_query_info.get(key, default),
            executed_value=getattr(executed_query, key))

    # Check 'extra'.
    _check_expectation(
        'extra',
        mismatched_attrs=mismatched_attrs,
        expected_value={
            _key: (_ws_re.sub(' ', _value[0]).strip(), _value[1])
            for _key, _value in expected_query_info.get('extra',
                                                        {}).items()
        },
        executed_value={
            _key: (_ws_re.sub(' ', _value[0]).strip(), _value[1])
            for _key, _value in executed_query.extra.items()
        })

    # Check 'offset'.
    _check_expectation(
        'offset',
        mismatched_attrs=mismatched_attrs,
        expected_value=expected_query_info.get('offset', 0),
        executed_value=executed_query.low_mark)

    # Check 'limit'.
    _check_expectation(
        'limit',
        mismatched_attrs=mismatched_attrs,
        expected_value=expected_query_info.get('limit'),
        executed_value=executed_query.high_mark,
        match_func=lambda expected_value, executed_value: (
            expected_value == executed_value or
            (expected_value is None and
             executed_value == MAX_GET_RESULTS)))

    # Check 'num_joins'.
    if executed_query.alias_map:
        # Consider all tables that have been JOINed, ignoring the
        # main table.
        executed_num_joins = len(executed_reffed_tables -
                                 {executed_table_name})
    else:
        executed_num_joins = 0

    _check_expectation(
        'num_joins',
        mismatched_attrs=mismatched_attrs,
        expected_value=expected_query_info.get('num_joins', 0),
        executed_value=executed_num_joins)

    # Check 'tables'.
    tables_default: Set[str]

    if expected_model is None:
        tables_default = set()
    else:
        tables_default = {expected_model._meta.db_table}

    if executed_query.alias_refcount:
        executed_tables = \
            executed_reffed_tables | {executed_table_name}
    else:
        executed_tables = {executed_table_name}

    _check_expectation(
        'tables',
        mismatched_attrs=mismatched_attrs,
        expected_value=set(expected_query_info.get('tables',
                                                   tables_default)),
        executed_value=executed_tables)

    # Check 'only_fields'.
    _check_expectation(
        'only_fields',
        mismatched_attrs=mismatched_attrs,
        expected_value=set(expected_query_info.get('only_fields',
                                                   set())),
        executed_value=set(executed_query.deferred_loading[0]))

    # Check 'select_related'.
    executed_select_related_raw = executed_query.select_related
    executed_select_related: Union[Literal[True], Set[str]]

    if executed_select_related_raw is True:
        executed_select_related = True
    elif isinstance(executed_select_related_raw, dict):
        executed_select_related = \
            set(executed_select_related_raw.keys())
    else:
        executed_select_related = set()

    expected_select_related_raw = \
        expected_query_info.get('select_related')
    expected_select_related: Union[Literal[True], Set[str]]

    if expected_select_related_raw is True:
        expected_select_related = True
    elif expected_select_related_raw:
        expected_select_related = set(expected_select_related_raw)
    else:
        expected_select_related = set()

    _check_expectation(
        'select_related',
        mismatched_attrs=mismatched_attrs,
        expected_value=expected_select_related,
        executed_value=executed_select_related)

    # Check 'where'. Normalize the Q object used to filter.
    _check_expectation(
        'where',
        mismatched_attrs=mismatched_attrs,
        expected_value=_normalize_q(
            expected_query_info.get('where', Q())),
        executed_value=_normalize_q(
            queries_to_qs.get(executed_query, Q())),
        format_expected_value_func=_format_q,
        format_executed_value_func=_format_q)

    # Check if this is an aggregate query.
    expected_inner_query_info = expected_query_info.get('inner_query')

    if isinstance(executed_query, AggregateQuery):
        if check_subqueries:
            # NOTE: As of October 23, 2023, django-stubs doesn't
            #       document this attribute.
            inner_query = executed_query.inner_query  # type: ignore

            inner_mismatched_attrs = _check_query(
                executed_query=inner_query,
                executed_query_info=executed_query_info,
                expected_query_info=expected_inner_query_info or {},
                check_subqueries=check_subqueries,
                queries_to_qs=queries_to_qs)

            if inner_mismatched_attrs:
                mismatched_attrs.append({
                    'name': 'inner_query',
                    'inner_mismatched_attrs': inner_mismatched_attrs,
                })
        elif check_subqueries is None:
            RemovedInDjblets50Warning.warn(
                'assertQueries() does not check subqueries by '
                'default, but a subquery was found and ignored in '
                'this test! Djblets 5 will check subqueries by '
                'default. Please update your assertQueries() call '
                'to pass check_subqueries=True and then update your '
                'query expectations to include the subquery.')
    else:
        _check_expectation(
            'inner_query',
            mismatched_attrs=mismatched_attrs,
            expected_value=expected_inner_query_info,
            executed_value=None)

    return mismatched_attrs


def _normalize_q(
    q: Q,
) -> Q:
    """Normalize a Q object for comparison.

    This will filter out any empty Q objects, which are normally filtered
    out during query execution. This helps to compare Q objects without
    worrying whether a code path includes an empty Q object or omits it
    entirely.

    Version Added:
        3.4

    Args:
        q (django.db.models.Q):
            The Q object to normalize.

    Returns:
        django.db.models.Q:
        The resulting Q object.
    """
    children: List[Any] = []

    for child_q in q.children:
        if isinstance(child_q, Q):
            if not child_q:
                continue

            child_q = _normalize_q(child_q)
            grandchildren = child_q.children

            if len(grandchildren) == 1:
                child_q = grandchildren[0]

        children.append(child_q)

    if len(children) == 1 and isinstance(children[0], Q):
        new_q = children[0]
    else:
        new_q = Q(*children)
        new_q.connector = q.connector
        new_q.negated = q.negated

    return new_q


def _format_q(
    q: Q,
    *,
    indent: int = 0,
) -> str:
    """Format a Q object for easier comparison.

    This will display a Q object and all children in a nested tree form,
    helping to see the structure of the query and compare differences.

    Version Added:
        3.4

    Args:
        q (django.db.models.Q):
            The Q object to format.

        indent (int, optional):
            The indentation level for the formatted output.

    Returns:
        str:
        The formatted Q object.
    """
    indent_str = ' ' * indent

    if q.negated:
        template = f'{indent_str}(NOT\n{indent_str} (%s:\n%s))'
        indent += 1
        indent_str += ' '
    else:
        template = f'{indent_str}(%s:\n%s)'

    children_fmt: List[str] = []

    for child in q.children:
        if isinstance(child, Q):
            children_fmt.append(_format_q(child, indent=indent + 1))
        else:
            children_fmt.append('%s %s' % (indent_str, force_str(child)))

    children_str = '\n'.join(children_fmt)

    return template % (q.connector, children_str)
