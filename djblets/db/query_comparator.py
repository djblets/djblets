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

from django.db.models import F, Q, QuerySet
from django.db.models.expressions import (CombinedExpression,
                                          NegatedExpression,
                                          Subquery,
                                          Value)
from django.db.models.query import MAX_GET_RESULTS
from django.db.models.sql.query import Query as SQLQuery
from django.utils.tree import Node
from typing_extensions import Literal, NotRequired, TypeAlias, TypedDict

from djblets.db.query_catcher import catch_queries

if TYPE_CHECKING:
    from django.db.models import Model
    from django.db.models.expressions import BaseExpression

    from djblets.db.query_catcher import (CatchQueriesContext,
                                          ExecutedQueryInfo,
                                          ExecutedSubQueryInfo)

    _T = TypeVar('_T')
    _ExecutedQueryInfoT = TypeVar('_ExecutedQueryInfoT',
                                  ExecutedQueryInfo,
                                  ExecutedSubQueryInfo)


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
    query_sql: Optional[List[str]]

    #: The results for any subquery matches.
    subqueries: Optional[CompareQueriesContext]

    #: Lines of traceback showing where this query was executed.
    traceback: Optional[List[str]]


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

    #: A mapping of joined table names to their join types.
    #:
    #: Version Added:
    #:     3.4
    join_types: NotRequired[Dict[str, str]]

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

    #: Information on subqueries within this query.
    #:
    #: Version Added:
    #:     3.4
    subqueries: NotRequired[Optional[ExpectedQueries]]

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

    #: Whether there are any mismatches found.
    has_mismatches: bool

    #: The number of queries that were executed.
    num_executed_queries: int

    #: The number of queries that were expected.
    num_expected_queries: int

    #: Whether the number of executed and expected queries are different.
    query_count_mismatch: bool

    #: The list of query expectation failures.
    query_mismatches: List[QueryMismatch]

    #: An internal list of unchecked mismatched attributes.
    #:
    #: This is used internally and may be removed in a future version
    #: without a deprecation period.
    _unchecked_mismatched_attrs: Set[str]


class _CheckQueryResult(TypedDict):
    """Results for a _check_query call.

    Version Added:
        3.4
    """

    #: A list of mismatched attributes for this query.
    #:
    #: This will be empty if there are no mismatches.
    mismatched_attrs: List[QueryMismatchedAttr]

    #: The comparison context for any subqueries.
    #:
    #: This will be ``None`` if not checking for subqueries.
    subqueries_compare_ctx: Optional[CompareQueriesContext]

    #: An internal list of unchecked mismatched attributes.
    unchecked_mismatched_attrs: Set[str]


@contextmanager
def compare_queries(
    queries: Sequence[Union[ExpectedQuery,
                            Dict[str, Any]]],
    *,
    _check_join_types: bool = True,
    _check_subqueries: bool = True,
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

        _check_join_types (bool, optional):
            Whether to check join types.

            This is internal for compatibility with the old behavior for
            :py:meth:`TestCase.assertQueries()
            <djblets.testing.testcases.assertQueries>` and will be removed in a
            future release without a deprecation period.

        _check_subqueries (bool, optional):
            Whether to check subqueries.

            This is internal for compatibility with the old behavior for
            :py:meth:`TestCase.assertQueries()
            <djblets.testing.testcases.assertQueries>` and will be removed in a
            future release without a deprecation period.

    Context:
        dict:
        The context for compared queries.

        This will only be populated after the context manager has finished.
        See :py:class:`CompareQueriesContext` for details.
    """
    assert isinstance(queries, list)

    compare_ctx = CompareQueriesContext(
        has_mismatches=False,
        num_executed_queries=0,
        num_expected_queries=0,
        query_count_mismatch=False,
        query_mismatches=[],
        _unchecked_mismatched_attrs=set())

    with catch_queries(_check_subqueries=_check_subqueries) as catch_ctx:
        yield compare_ctx

    compare_ctx.update(_check_queries(
        expected_queries=queries,
        executed_queries=catch_ctx.executed_queries,
        catch_ctx=catch_ctx,
        _check_join_types=_check_join_types,
        _check_subqueries=_check_subqueries))


def _check_queries(
    *,
    expected_queries: List[Union[ExpectedQuery,
                                 Dict[str, Any]]],
    executed_queries: Sequence[_ExecutedQueryInfoT],
    catch_ctx: CatchQueriesContext,
    _check_join_types: bool = True,
    _check_subqueries: bool = True,
) -> CompareQueriesContext:
    """Check database queries for expected output.

    This takes a list of executed queries captured using
    :py:func:`~djblets.db.query_catcher.catch_queries` and compare them against
    a list of expected queries. The results are a list of mismatches found
    between the executed and expeceted queries.

    Version Added:
        3.4

    Args:
        expected_queries (list of dict):
            The list of expected queries.

        executed_queries (list of dict):
            The list of executed queries.

        catch_ctx (djblets.db.query_catcher.CatchQueriesContext):
            The context for caught queries.

        _check_join_types (bool, optional):
            Whether to check join types.

            This is internal for compatibility with the old behavior for
            :py:meth:`TestCase.assertQueries()
            <djblets.testing.testcases.assertQueries>` and will be removed in a
            future release without a deprecation period.

        _check_subqueries (bool, optional):
            Whether to check subqueries.

            This is internal for compatibility with the old behavior for
            :py:meth:`TestCase.assertQueries()
            <djblets.testing.testcases.assertQueries>` and will be removed in a
            future release without a deprecation period.

    Returns:
        dict:
        The context for compared queries.

        See :py:class:`CompareQueriesContext`.
    """
    # Now we can compare numbers.
    num_expected_queries = len(expected_queries)
    num_executed_queries = len(executed_queries)
    query_count_mismatch: bool = False
    unchecked_mismatched_attrs = set()

    # Make sure we received the expected number of queries.
    if num_expected_queries != num_executed_queries:
        query_count_mismatch = True

        if num_expected_queries < num_executed_queries:
            expected_queries += [
                {}
                for _i in range(num_executed_queries - num_expected_queries)
            ]
        elif num_expected_queries > num_executed_queries:
            expected_queries = expected_queries[:num_executed_queries]

    # Go through each matching Query and compare state.
    query_mismatches: List[QueryMismatch] = []
    queries_iter = enumerate(zip(cast(Sequence[ExpectedQuery],
                                      expected_queries),
                                 executed_queries))

    for i, (query_info, executed_query_info) in queries_iter:
        executed_query = executed_query_info['query']
        result = _check_query(
            executed_query=executed_query,
            executed_query_info=executed_query_info,
            expected_query_info=query_info,
            check_join_types=_check_join_types,
            check_subqueries=_check_subqueries,
            catch_ctx=catch_ctx)
        mismatched_attrs = result['mismatched_attrs']
        subqueries_compare_ctx = result.get('subqueries_compare_ctx')
        unchecked_mismatched_attrs.update(result['unchecked_mismatched_attrs'])

        if (mismatched_attrs or
            (_check_subqueries and
             subqueries_compare_ctx is not None and
             subqueries_compare_ctx['has_mismatches'])):
            query_mismatches.append({
                'executed_query': executed_query,
                'index': i,
                'mismatched_attrs': mismatched_attrs,
                'note': query_info.get('__note__'),
                'query_sql': cast(Optional[List[str]],
                                  executed_query_info.get('sql')),
                'subqueries': subqueries_compare_ctx,
                'traceback': cast(Optional[List[str]],
                                  executed_query_info.get('traceback')),
            })

    # Update the context for the caller to examine.
    return {
        'has_mismatches': query_count_mismatch or (len(query_mismatches) > 0),
        'num_executed_queries': num_executed_queries,
        'num_expected_queries': num_expected_queries,
        'query_count_mismatch': query_count_mismatch,
        'query_mismatches': query_mismatches,
        '_unchecked_mismatched_attrs': unchecked_mismatched_attrs,
    }


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
            'executed_value': format_executed_value_func(executed_value),
            'expected_value': format_expected_value_func(expected_value),
            'raw_executed_value': executed_value,
            'raw_expected_value': expected_value,
        })


def _check_query(
    *,
    executed_query: SQLQuery,
    executed_query_info: _ExecutedQueryInfoT,
    expected_query_info: ExpectedQuery,
    check_join_types: bool,
    check_subqueries: bool,
    catch_ctx: CatchQueriesContext,
) -> _CheckQueryResult:
    """Check a query for expectations.

    This will compare attributes on an executed query to an expected query
    and determine if there are any mismatches.

    Version Added:
        3.4

    Args:
        executed_query (django.db.models.sql.query.Query):
            The executed query to compare.

        executed_query_info (djblets.db.query_catcher.ExecutedQueryInfo):
            Information on the executed query to use for comparison.

        expected_query_info (dict):
            Information on the expectations for the query from the caller.

        check_join_types (bool):
            Whether to check for join types.

            This is internal for compatibility with the old behavior for
            :py:meth:`TestCase.assertQueries()
            <djblets.testing.testcases.assertQueries>` and will be removed in a
            future release without a deprecation period.

        check_subqueries (bool):
            Whether to check for subqueries.

            This is internal for compatibility with the old behavior for
            :py:meth:`TestCase.assertQueries()
            <djblets.testing.testcases.assertQueries>` and will be removed in a
            future release without a deprecation period.

        catch_ctx (djblets.db.query_catcher.CatchQueriesContext):
            The context for caught queries.

    Returns:
        dict:
        A dictionary of results.

        See :py:class:`_CheckQueryResult` for details.
    """
    mismatched_attrs: List[QueryMismatchedAttr] = []
    unchecked_mismatched_attrs: Set[str] = set()

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
        executed_value=executed_tables,
        format_expected_value_func=_format_set,
        format_executed_value_func=_format_set)

    # Check 'join_types'.
    executed_join_types = {
        _table_name: _value.join_type
        for _table_name, _value in executed_query.alias_map.items()
        if (_table_name != executed_table_name and
            executed_query.alias_refcount.get(_table_name))
    }

    if check_join_types:
        _check_expectation(
            'join_types',
            mismatched_attrs=mismatched_attrs,
            expected_value=expected_query_info.get('join_types', {}),
            executed_value=executed_join_types)
    elif executed_join_types and 'join_types' not in expected_query_info:
        unchecked_mismatched_attrs.add('join_types')

    # Check 'only_fields'.
    _check_expectation(
        'only_fields',
        mismatched_attrs=mismatched_attrs,
        expected_value=set(expected_query_info.get('only_fields',
                                                   set())),
        executed_value=set(executed_query.deferred_loading[0]),
        format_expected_value_func=_format_set,
        format_executed_value_func=_format_set)

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
            expected_query_info.get('where', Q()),
            normalize_subqueries=False),
        executed_value=_normalize_q(
            catch_ctx.queries_to_qs.get(executed_query, Q()),
            normalize_subqueries=check_subqueries),
        format_expected_value_func=(
            lambda q: _format_node(q, catch_ctx=catch_ctx)),
        format_executed_value_func=(
            lambda q: _format_node(q, catch_ctx=catch_ctx)))

    # Check if this is an aggregate query.
    subqueries_compare_ctx: Optional[CompareQueriesContext] = None

    # Check any subqueries.
    if check_subqueries:
        subqueries_compare_ctx = _check_queries(
            expected_queries=expected_query_info.get('subqueries') or [],
            executed_queries=executed_query_info['subqueries'],
            _check_join_types=check_join_types,
            catch_ctx=catch_ctx)

    return {
        'mismatched_attrs': mismatched_attrs,
        'subqueries_compare_ctx': subqueries_compare_ctx,
        'unchecked_mismatched_attrs': unchecked_mismatched_attrs,
    }


def _build_subquery_placeholder(
    *,
    subquery: Union[Q, QuerySet, Subquery],
    subqueries: List[Any],
) -> Union[Node, Q, tuple]:
    """Normalize a subquery to a placeholder.

    This will convert a subquery or an expression containing subquery value to
    a placeholder Q object in the form of::

        Q(__SubqueryType__subquery__=index)

    This allows for consistent comparison between subqueries, with detailed
    comparisons happening in expected subquery lists.

    Args:
        subquery (django.db.models.Q or
                  django.db.models.QuerySet or
                  django.db.models.expressions.Subquery):
            The subquery to normalize.

        subqueries (list):
            A list for tracking normalized subqueries.

    Returns:
        django.db.models.Q:
        The resulting normalized Q object.
    """
    subqueries.append(subquery)
    subquery_type = type(subquery).__name__
    norm_subquery = (f'__{subquery_type}__subquery__', len(subqueries))

    if getattr(subquery, 'negated', False):
        return ~Q(norm_subquery)
    else:
        return norm_subquery


def _normalize_q(
    q: Q,
    *,
    subqueries: Optional[List[Any]] = None,
    normalize_subqueries: bool = True,
) -> Q:
    """Normalize a Q object for comparison.

    This will filter out any empty Q objects, which are normally filtered
    out during query execution. This helps to compare Q objects without
    worrying whether a code path includes an empty Q object or omits it
    entirely.

    By default, subqueries will be normalized to
    ``Q(__SubqueryName__subquery__=index)`` objects for comparison purposes.

    Version Added:
        3.4

    Args:
        q (django.db.models.Q):
            The Q object to normalize.

        subqueries (list, optional):
            A list of subqueries found, for tracking purposes.

            This is considered internal for recursive calls, and does not
            need to be supplied.

        normalize_subqueries (bool, optional):
            Whether to normalize subqueries.

    Returns:
        django.db.models.Q:
        The resulting Q object.
    """
    if subqueries is None:
        subqueries = []

    children: List[Any] = []

    # Negated expressions are special. We need to extract an expressin out of
    # them.
    is_negated_epxression = False and isinstance(q, NegatedExpression)

    if is_negated_epxression:
        q_children = [q.expression]
    else:
        q_children = getattr(q, 'children', [])

    # Go through all the children and see if we can collapse or transform any
    # of them for comparison.
    for child in q_children:
        if isinstance(child, Q):
            # Remove any empty children.
            if not child:
                continue

            # Normalize the child, recursively.
            child = _normalize_q(child,
                                 subqueries=subqueries,
                                 normalize_subqueries=normalize_subqueries)
            grandchildren = child.children

            if (len(grandchildren) == 1 and
                isinstance(grandchildren[0], tuple)):
                # This is a Q() with only a single value in it. We may be
                # able to collapse or record a subquery.
                grandchild = grandchildren[0]

                if (normalize_subqueries and
                    isinstance(grandchild[1], QuerySet)):
                    child = _build_subquery_placeholder(
                        subquery=child,
                        subqueries=subqueries)
                elif not child.negated:
                    # Since we're not negating, we can collapse the child.
                    child = grandchild
        elif isinstance(child, NegatedExpression):
            child = ~Q(_build_subquery_placeholder(
                subquery=child.expression,
                subqueries=subqueries))
        elif normalize_subqueries and isinstance(child, Subquery):
            # Subqueries are formatted as Q(__SubqueryType__subquery__=index),
            # since we can't actually compare true subqueries. Instead, this
            # will reference a subquery in the subqueries dictionaries in the
            # compare results.
            child = _build_subquery_placeholder(
                subquery=child,
                subqueries=subqueries)

        children.append(child)

    new_q = q

    if is_negated_epxression:
        assert len(children) == 1

        return children[0]

    if len(children) == 1 and isinstance(children[0], Q):
        # There's only one single nested Q, meaning we don't have multiple Qs
        # or any tuples normalized above. We can now determine if we can safely
        # swap in the child and its state.
        child = children[0]
        q_negated = q.negated

        if not q_negated:
            # The current Q object doesn't have a negated property, and it only
            # has one child, so we can optimize it out.
            # collapse down
            new_q = child

        if not child.negated:
            # The child doesn't negate its value, so we can safely use the
            # original Q object's negation state. If the child had negated its
            # value, we'd want to preserve that.
            new_q.negated = q_negated

    if new_q is q:
        new_q.children = children

    return new_q


def _format_query_value(
    value: Any,
) -> str:
    """Format a value in a query.

    This will format a combined expression (such as an F expression) or any
    other value in a query.

    Version Added:
        3.4

    Args:
        value (object):
            The value to format.

    Returns:
        str:
        The formatted value.
    """
    if isinstance(value, CombinedExpression):
        return '%s %s %s' % (_format_query_value(value.lhs),
                             value.connector,
                             _format_query_value(value.rhs))
    elif isinstance(value, F):
        return "%s('%s')" % (type(value).__name__, value.name)
    elif isinstance(value, Value):
        return str(value.value)
    elif isinstance(value, set):
        if value:
            return '{%s}' % ', '.join(
                repr(_item)
                for _item in sorted(value)
            )
        else:
            return 'set()'
    else:
        return repr(value)


def _format_query_part(
    part: Any,
    *,
    indent: str,
    prefix: str = '',
    in_negated: bool = False,
    catch_ctx: CatchQueriesContext,
) -> str:
    """Format part of a query.

    This will format a Node, Query, tuple, or other expression within a query
    tree for display.

    Version Added:
        3.4

    Args:
        query (object):
            The query part object in the tree to format.

        indent (int, optional):
            The indentation level for the formatted output.

        prefix (str, optional):
            The optional prefix for any outputted lines.

        catch_ctx (djblets.db.query_catcher.CatchQueriesContext):
            The context for caught queries.

    Returns:
        str:
        The formatted part.
    """
    if isinstance(part, Node):
        # This is a node (e.g., a Q() object or similar). We can format it
        # as usual.
        return _format_node(part,
                            catch_ctx=catch_ctx,
                            indent=indent,
                            prefix=prefix)
    elif isinstance(part, SQLQuery):
        # This is another query. We need to grab the associated Q() and
        # format that.
        return _format_node(catch_ctx.queries_to_qs[part],
                            catch_ctx=catch_ctx,
                            indent=indent,
                            prefix=prefix)
    elif isinstance(part, tuple):
        # For tuples, just output a `Q()` normally to avoid wrapping inside
        # of another Q().
        key, value = part
        formatted_value = _format_query_value(value)
        part = f'Q({key}={formatted_value})'
    else:
        part = _format_query_value(part)

    # Format either the tuple or whatever else we found as a string
    # representation.
    return f'{indent}{prefix}{part}'


def _format_query_children(
    query: Union[BaseExpression, Node],
    *,
    indent: str,
    op: str = '',
    in_negated: bool = False,
    catch_ctx: CatchQueriesContext,
) -> str:
    """Format children of a node or expression.

    This will iterate through all children, formatting them with an optional
    prefixed operator (for AND or OR queries) at the provided indentation
    level.

    Version Added:
        3.4

    Args:
        node (django.utils.tree.Node or django.db.expressions.BaseExpression):
            The node or expression containing children to format.

        indent (int, optional):
            The indentation level for the formatted output.

        op (str, optional):
            The optional operator to prepend to all lines after the first.

        catch_ctx (djblets.db.query_catcher.CatchQueriesContext):
            The context for caught queries.

    Returns:
        str:
        The formatted Node object.
    """
    children = getattr(query, 'children', [])
    init_parts: List[str]

    if op and len(children) > 1:
        # The first line won't contain an operator, but does need padding for
        # that operator. We'll add this and then process the rest of the
        # children with the operator prefixed to each line.
        prefix = f'{op} '
        init_parts = [
            _format_query_part(children[0],
                               indent=indent,
                               prefix=' ' * len(prefix),
                               catch_ctx=catch_ctx,
                               in_negated=in_negated),
        ]

        children = children[1:]
    else:
        prefix = ''
        init_parts = []

    return '\n'.join(init_parts + [
        _format_query_part(child,
                           indent=indent,
                           prefix=prefix,
                           in_negated=in_negated,
                           catch_ctx=catch_ctx)
        for child in children
    ])


def _format_node(
    node: Node,
    *,
    indent: str = '',
    prefix: str = '',
    catch_ctx: CatchQueriesContext,
) -> str:
    """Format a Node object for easier comparison.

    This will format a normalized Node object and all children in a nested tree
    form, helping to see the structure of the query and compare differences.

    This expects all nodes to be normalized via :py:func:`_normalize_q`.

    Version Added:
        3.4

    Args:
        node (django.utils.tree.Node):
            The node object to format.

        indent (int, optional):
            The indentation level for the formatted output.

        prefix (str, optional):
            The optional prefix for any outputted lines.

        catch_ctx (djblets.db.query_catcher.CatchQueriesContext):
            The context for caught queries.

    Returns:
        str:
        The formatted Node object.
    """
    name = type(node).__name__
    children_str: str = ''

    if node.negated:
        name = f'~{name}'

    if len(node.children) == 1:
        # We may need to collapse this down for display, as Q() objects nest
        # internally (even after normalization). If it's a tuple or a
        # single-child Q(), then we can safely do this.
        child = node.children[0]

        if isinstance(child, tuple):
            # For a tuple, we'll just represent the key/value in the
            # generated Q(...) below.
            key, value = child
            formatted_value = _format_query_value(value)
            children_str = f'{key}={formatted_value}'
        elif isinstance(child, Q) and len(child.children) > 1:
            # For a Q(), we'll collapse down by formatting using the
            # child. This is done since negated Qs have an AND Q inside,
            # and that's the one we want to show.
            node = child

    if node.connector == Q.AND:
        op = '&'
    elif node.connector == Q.OR:
        op = '|'
    else:
        op = ''

    if not children_str:
        prefix_indent = ' ' * len(prefix)
        children_str = _format_query_children(
            node,
            indent=f'{indent}{prefix_indent} ',
            op=op,
            catch_ctx=catch_ctx)

        if children_str:
            children_str = f'\n{children_str}'

    return f'{indent}{prefix}{name}({children_str})'


def _format_set(
    values: Set[Any],
) -> str:
    """Format a set with sorted values.

    :py:mod:`pprint` doesn't sort sets unless they span multiple lines of
    output. This function takes the set, turns it into a sorted list, and
    then re-represents it as sorted set.

    Args:
        values (set):
            The set to format.

    Returns:
        str:
        The formatted set.
    """
    return '{%s}' % (pformat(sorted(values))[1:-1])
