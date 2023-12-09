"""Utilities for capturing and inspecting database queries.

Version Added:
    3.4
"""

from __future__ import annotations

import traceback
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Iterator, List, Sequence, Type, Union

from django.core.exceptions import EmptyResultSet
from django.db.models import Q, QuerySet, Subquery
from django.db.models.expressions import ExpressionWrapper
from django.db.models.signals import pre_delete
from django.db.models.sql.compiler import (SQLCompiler,
                                           SQLDeleteCompiler,
                                           SQLInsertCompiler,
                                           SQLUpdateCompiler)
from django.db.models.sql.query import Query as SQLQuery
from django.db.models.sql.subqueries import AggregateQuery
from django.utils.tree import Node
from typing_extensions import Literal, TypedDict


class ExecutedQueryType(str, Enum):
    """A type of executed query that can be inspected.

    Version Added:
        3.4
    """

    #: A DELETE query.
    DELETE = 'DELETE'

    #: An INSERT query.
    INSERT = 'INSERT'

    #: A SELECT query.
    SELECT = 'SELECT'

    #: An UPDATE query.
    UPDATE = 'UPDATE'


class ExecutedQueryInfo(TypedDict):
    """Information on an executed query.

    This contains information seen at execution time that can be used for
    inspection of the queries.

    Version Added:
        3.4
    """

    #: The query that was executed.
    query: SQLQuery

    #: The type of result information.
    #:
    #: This is used to distinguish between query and subquery information.
    result_type: Literal['query']

    #: The list of lines of SQL that was executed.
    sql: List[str]

    #: Any subqueries within this query, in the orders found.
    subqueries: List[ExecutedSubQueryInfo]

    #: The lines of traceback showing where the query was executed.
    traceback: List[str]

    #: The type of executed query.
    type: ExecutedQueryType


class ExecutedSubQueryInfo(TypedDict):
    """Information on a subquery within an executed query.

    This contains information seen at execution time that can be used for
    inspection of the queries.

    Version Added:
        3.4
    """

    #: The type of class managing the subquery.
    cls: Type[Union[AggregateQuery, QuerySet, Subquery]]

    #: The instance of the subquery class.
    instance: Union[AggregateQuery, QuerySet, Subquery]

    #: The query that was executed.
    query: SQLQuery

    #: The type of result information.
    #:
    #: This is used to distinguish between query and subquery information.
    result_type: Literal['subquery']

    #: Any subqueries within this query, in the orders found.
    subqueries: List[ExecutedSubQueryInfo]

    #: The type of executed query.
    type: Literal[ExecutedQueryType.SELECT]


@dataclass
class CatchQueriesContext:
    """Context for captured query information.

    This is provided and populated when using :py:func:`catch_queries`.

    Version Added:
        3.4
    """

    #: Information on the queries that were executed.
    executed_queries: Sequence[ExecutedQueryInfo]

    #: A mapping of SQL queries to their Q expressions.
    queries_to_qs: Dict[SQLQuery, Q]


@contextmanager
def catch_queries(
    *,
    _check_subqueries: bool = True,
) -> Iterator[CatchQueriesContext]:
    """Catch queries and provide information for further inspection.

    Any database queries executed during this context will be captured and
    provided in the context. For each query, this will capture:

    1. The type of query.
    2. The :py:class:`SQL Query objects <django.db.models.query.sql.Query>`
    3. The generated SQL statements
    4. Tracebacks showing where the SQL was executed.

    It will also provide a mapping of the Query objects to their Q
    expressions.

    To use this, :pypi:`kgb` must be installed.

    Version Added:
        3.4

    Args:
        _check_subqueries (bool, optional):
            Whether to check subqueries.

            This is internal for compatibility with the old behavior for
            :py:meth:`TestCase.assertQueries()
            <djblets.testing.testcases.assertQueries>` and will be removed in a
            future release without a deprecation period.

    Context:
        CatchQueriesContext:
        The context populated with query information.
    """
    try:
        import kgb
    except ImportError as e:
        raise ImportError(
            'kgb could not be imported. It is required in order to use '
            'djblets.db.query_catcher.catch_queries(). Error: %s'
            % e)

    spy_agency = kgb.SpyAgency()

    executed_queries: List[ExecutedQueryInfo] = []
    queries_to_qs: Dict[SQLQuery, Q] = {}

    # Track Query objects any time a compiler is executing SQL.
    @spy_agency.spy_for(SQLCompiler.execute_sql,
                        owner=SQLCompiler)
    def _sql_compiler_execute_sql(
        _self: SQLCompiler,
        *args,
        **kwargs,
    ) -> Any:
        if isinstance(_self, SQLDeleteCompiler):
            query_type = ExecutedQueryType.DELETE
        elif isinstance(_self, SQLUpdateCompiler):
            query_type = ExecutedQueryType.UPDATE
        else:
            query_type = ExecutedQueryType.SELECT

        query = _self.query
        sql = _serialize_caught_sql(query)

        if sql:
            subqueries: List[ExecutedSubQueryInfo] = []

            if _check_subqueries:
                _scan_subqueries(node=query,
                                 result=subqueries,
                                 queries_to_qs=queries_to_qs,
                                 _check_subqueries=_check_subqueries)

            executed_queries.append({
                'query': query,
                'result_type': 'query',
                'sql': sql,
                'subqueries': subqueries,
                'traceback': traceback.format_stack(),
                'type': query_type,
            })

        return SQLCompiler.execute_sql.call_original(_self, *args, **kwargs)

    @spy_agency.spy_for(SQLInsertCompiler.execute_sql,
                        owner=SQLInsertCompiler)
    def _sql_insert_compiler_execute_sql(
        _self: SQLInsertCompiler,
        *args,
        **kwargs,
    ) -> Any:
        query = _self.query
        sql = _serialize_caught_sql(query)

        if sql:
            executed_queries.append({
                'query': query,
                'result_type': 'query',
                'sql': sql,
                'subqueries': [],
                'traceback': traceback.format_stack(),
                'type': ExecutedQueryType.INSERT,
            })

        return SQLInsertCompiler.execute_sql.call_original(_self, *args,
                                                           **kwargs)

    # Build and track Q() objects any time they're added to a Query.
    @spy_agency.spy_for(SQLQuery.add_q, owner=SQLQuery)
    def _query_add_q(
        _self: SQLQuery,
        q_object: Q,
    ) -> Any:
        try:
            queries_to_qs[_self] &= q_object
        except KeyError:
            queries_to_qs[_self] = q_object

        return SQLQuery.add_q.call_original(_self, q_object)

    # Copy Q() objects any time a Query is cloned.
    @spy_agency.spy_for(SQLQuery.clone, owner=SQLQuery)
    def _query_clone(
        _self: SQLQuery,
        *args,
        **kwargs,
    ) -> Any:
        result = SQLQuery.clone.call_original(_self, *args, **kwargs)

        try:
            queries_to_qs[result] = queries_to_qs[_self]
        except KeyError:
            pass

        return result

    # Set up an explicit pre_delete signal. During deletion, Django
    # attempts to determine if it can fast-delete (which can be done if,
    # amongst other things, signals don't need to be emitted for each
    # object).
    #
    # This can lead to inconsistencies in test runs, if registration of
    # pre_delete or post_delete signals is conditional on that run. We
    # want to ensure a stable query count and information for DELETEs,
    # so we deny fast-deletion by setting up a model-global signal handler
    # during capture of queries.
    def _on_pre_delete(**kwargs):
        pass

    pre_delete.connect(_on_pre_delete)

    # Let the caller execute SQL. Results will be stored in the context.
    try:
        yield CatchQueriesContext(executed_queries=executed_queries,
                                  queries_to_qs=queries_to_qs)
    finally:
        # We no longer need to track anything in the compiler of Query.
        spy_agency.unspy_all()
        pre_delete.disconnect(_on_pre_delete)


def _scan_subqueries(
    *,
    node: Union[Node, SQLQuery],
    result: List[ExecutedSubQueryInfo],
    queries_to_qs: Dict[SQLQuery, Q],
    _check_subqueries: bool,
) -> None:
    """Scan for subqueries in a level of a query tree.

    This recursively walks a query tree, looking for any subqueries and
    recording them in the list within the nearest top-level query or subquery.

    Version Added:
        3.4

    Args:
        node (django.utils.tree.Node or django.db.models.sql.Query):
            The level of the tree to process.

        result (list of dict):
            The list of queries to append any new subquery information to.

        queries_to_qs (dict):
            A dictionary containing recording mappings of queries to Q objects.
    """
    child_subqueries: List[ExecutedSubQueryInfo]
    children: List[Any] = []

    if isinstance(node, SQLQuery):
        if isinstance(node, AggregateQuery):
            inner_query = node.inner_query  # type: ignore
            assert isinstance(inner_query, SQLQuery)

            child_subqueries = []
            _scan_subqueries(node=inner_query,
                             result=child_subqueries,
                             queries_to_qs=queries_to_qs,
                             _check_subqueries=_check_subqueries)

            result.append({
                'cls': type(node),
                'instance': node,
                'query': inner_query,
                'result_type': 'subquery',
                'subqueries': child_subqueries,
                'type': ExecutedQueryType.SELECT,
            })

            # We won't have any children to process, so we'll effectively
            # bail at this point.
        else:
            # Process the annotations.
            children = list(node.annotations.values())

            # Continue on by processing the Q filters within it.
            try:
                children += queries_to_qs[node].children
            except KeyError:
                # There are no Q objects for this query. Nothing to scan
                # through.
                pass
    else:
        children = node.children

    for child in children:
        if child:
            if isinstance(child, tuple):
                child = child[1]

            if isinstance(child, Node):
                _scan_subqueries(node=child,
                                 result=result,
                                 queries_to_qs=queries_to_qs,
                                 _check_subqueries=_check_subqueries)
            elif _check_subqueries:
                if isinstance(child, ExpressionWrapper):
                    # NOTE: As of November 28, 2023, django-stubs doesn't have
                    #       type hints for `ExpressionWrapper.expression`.
                    child = child.expression  # type: ignore

                if isinstance(child, (QuerySet, Subquery)):
                    child_subqueries = []
                    _scan_subqueries(node=child.query,
                                     result=child_subqueries,
                                     queries_to_qs=queries_to_qs,
                                     _check_subqueries=_check_subqueries)

                    result.append({
                        'cls': type(child),
                        'instance': child,
                        'query': child.query,
                        'result_type': 'subquery',
                        'subqueries': child_subqueries,
                        'type': ExecutedQueryType.SELECT,
                    })


def _serialize_caught_sql(
    query: SQLQuery,
) -> List[str]:
    """Serialize a caught SQL Query to SQL.

    Version Added:
        3.4

    Args:
        query (django.db.models.query.sql.Query):
            The SQL query to serialize.

    Returns:
        list of str:
        The list of SQL statements executed.
    """
    sql: List[str]

    # Grab the SQL. from the query. This may fail, and if it does, it
    # represents a query that we've caught that isn't actually going to be
    # executed (likely a component of another).
    try:
        try:
            sql = [str(query)]
        except ValueError:
            # When doing an INSERT OR IGNORE (SQLite), the SQL can be a list
            # rather than a string. Query.__str__ doesn't know how to handle
            # this, and will crash. We'll deal with it ourselves.
            sql_statements = query.sql_with_params()
            assert isinstance(sql_statements, list)

            sql = [
                _sql % _sql_params
                for _sql, _sql_params in sql_statements
            ]
    except EmptyResultSet:
        # This will be skipped.
        sql = []

    return sql
