"""Base class for test cases in Django-based applications."""

from __future__ import annotations

import inspect
import operator
import os
import re
import socket
import sys
import threading
import warnings
from collections import OrderedDict
from contextlib import contextmanager
from importlib import import_module
from importlib.machinery import ModuleSpec
from importlib.util import module_from_spec
from pprint import pformat
from typing import (Any, Callable, Dict, Iterator, List, Optional, Sequence,
                    Set, TYPE_CHECKING, Tuple, Type, TypeVar, Union, cast)
from unittest.util import safe_repr

import kgb
from django.apps import apps
from django.conf import settings
from django.core import serializers
from django.core.exceptions import ValidationError
from django.core.handlers.wsgi import WSGIHandler
from django.core.management import call_command
from django.core.servers import basehttp
from django.db import (DatabaseError, DEFAULT_DB_ALIAS, IntegrityError,
                       connections, router)
from django.db.models import Model, Q
from django.db.models.query import MAX_GET_RESULTS
from django.db.models.sql.query import Query as SQLQuery
from django.db.models.sql.subqueries import AggregateQuery
from django.template import Node
from django.test import testcases
from django.utils.encoding import force_text
from typing_extensions import Literal, NotRequired, TypeAlias, TypedDict

try:
    from django_evolution.models import Evolution, Version
except ImportError:
    Evolution = None
    Version = None

from djblets.db.query_catcher import catch_queries
from djblets.deprecation import RemovedInDjblets50Warning
from djblets.siteconfig.models import SiteConfiguration

if TYPE_CHECKING:
    from django.db.models.expressions import BaseExpression

    class _ExecutedQueryFailureInfo(TypedDict):
        key: str
        executed_value: NotRequired[str]
        expected_value: NotRequired[str]
        inner_failures: NotRequired[List[_ExecutedQueryFailureInfo]]

    class _ExecutedQueryAllFailuresInfo(TypedDict):
        executed_query: SQLQuery
        failures: List[_ExecutedQueryFailureInfo]
        index: int
        query_sql: List[str]
        traceback: List[str]

    _T = TypeVar('_T')


class StubNodeList(Node):
    def __init__(self, default_text):
        self.default_text = default_text

    def render(self, context):
        return self.default_text


class StubParser:
    def __init__(self, default_text):
        self.default_text = default_text

    def parse(self, until):
        return StubNodeList(self.default_text)

    def delete_first_token(self):
        pass


class ExpectedQuery(TypedDict):
    """An expected query for a query assertion.

    This is used for :py:meth:`TestCase.assertQueries`.

    Version Added:
        3.4
    """

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
    select_related: NotRequired[Union[Literal[True], Tuple[str, ...]]]

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
#:     this type allows either a :py:meth:`ExpectedQuery` or a plain
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


class ExpectedWarning(TypedDict):
    """An expected warning from an assertion.

    This is used for :py:meth:`TestCase.assertWarnings`.

    Version Added:
        3.2
    """

    #: The expected class for the warning.
    #:
    #: Type:
    #:     type
    cls: Type[Warning]

    #: The expected message for the warning.
    #:
    #: If not provided, messages won't be compared.
    #:
    #: Type:
    #:     str
    message: NotRequired[Optional[str]]


class TestCase(testcases.TestCase):
    """Base class for test cases.

    Individual tests on this TestCase can use the :py:func:`add_fixtures`
    decorator to add or replace the fixtures used for the test.
    """
    ws_re = re.compile(r'\s+')

    def __call__(self, *args, **kwargs):
        method = getattr(self, self._testMethodName)
        old_fixtures = getattr(self, 'fixtures', None)

        if hasattr(method, '_fixtures'):
            if (getattr(method, '_replace_fixtures') or
                old_fixtures is None):
                self.fixtures = method._fixtures
            else:
                self.fixtures = old_fixtures + method._fixtures

        super(TestCase, self).__call__(*args, **kwargs)

        self.fixtures = old_fixtures

    def shortDescription(self):
        """Returns the description of the current test.

        This changes the default behavior to replace all newlines with spaces,
        allowing a test description to span lines. It should still be kept
        short, though.
        """
        doc = self._testMethodDoc

        if doc is not None:
            doc = doc.split('\n\n', 1)[0]
            doc = self.ws_re.sub(' ', doc).strip()

        return doc

    @contextmanager
    def siteconfig_settings(self, settings):
        """Temporarily sets siteconfig settings for a test.

        Subclasses should override this if they want to run a method like
        :py:func:`~djblets.siteconfig.django_settings.apply_django_settings`
        before and after each test.

        Args:
            settings (dict):
                The new siteconfig settings to set.

        Context:
            The current site configuration will contain the new settings for
            this test.
        """
        siteconfig = SiteConfiguration.objects.get_current()

        old_settings = {}

        for key, value in settings.items():
            old_settings[key] = siteconfig.get(key)
            siteconfig.set(key, value)

        siteconfig.save()

        try:
            yield
        finally:
            for key, value in old_settings.items():
                siteconfig.set(key, value)

            siteconfig.save()

    def assertAttrsEqual(self, obj, attrs, msg=None):
        """Assert that attributes on an object match expected values.

        This will compare each attribute defined in ``attrs`` against the
        corresponding attribute on ``obj``. If the attribute value does not
        match, or the attribute is missing, this will assert.

        Args:
            obj (object):
                The object to compare attribute values to.

            attrs (dict):
                A dictionary of expected attribute names and values.

            msg (unicode, optional):
                A custom message to include if there's a failure.

        Raises:
            AssertionError:
                An attribute was not found or the value did not match.
        """
        for key, value in attrs.items():
            try:
                attr_value = getattr(obj, key)

                if attr_value != value:
                    raise self.failureException(self._formatMessage(
                        msg,
                        '%s: %s != %s'
                        % (key, safe_repr(attr_value),
                           safe_repr(value))))
            except AttributeError:
                raise self.failureException(self._formatMessage(
                    msg,
                    'Attribute "%s" was not found on %s'
                    % (key, safe_repr(obj))))

    def assertRaisesValidationError(self, expected_messages, *args, **kwargs):
        """Assert that a ValidationError is raised with the given message(s).

        This is a wrapper around :py:meth:`assertRaisesMessage` with a
        :py:class:`ValidationError` that handles converting the expected
        messages into a list (if it isn't already) and then converting that
        into a string representation, which is what
        :py:meth:`assertRaisesMessage` will be checking against.

        Args:
            expected_messages (list or unicode):
                The expected messages as either a list of strings or a
                single string.

            args:
                Additional arguments to pass to :py:meth:`assertRaisesMessage`.

            kwargs:
                Additional keyword arguments to pass to
                :py:meth:`assertRaisesMessage`.
        """
        if isinstance(expected_messages, str):
            expected_messages = [expected_messages]

        return self.assertRaisesMessage(ValidationError,
                                        repr(expected_messages),
                                        *args,
                                        **kwargs)

    def assertRaisesMessage(self, expected_exception, expected_message,
                            *args, **kwargs):
        """Assert that an exception is raised with a given message.

        This is a replacement for Django's assertRaisesMessage that behaves
        well with a design change in Python 2.7.9/10, without crashing.
        """
        # The difference between this version and Django's is that we're
        # not taking the callable_obj as an argument with a default value and
        # passing it down to assertRaisesRegex. Python 2.7.9/10's
        # implementation defaults callable_obj to a special value, which
        # Django overrides.
        return self.assertRaisesRegex(expected_exception,
                                      re.escape(expected_message),
                                      *args, **kwargs)

    # NOTE: This overrides TestCase.assertWarns (introducecd in Python 3.2),
    #       adding 'message' and removing a callable argument and custom
    #       error message. It's not compatible with that function. We should
    #       consider this for future deprecation.
    @contextmanager
    def assertWarns(
        self,
        cls: Type[Warning] = DeprecationWarning,
        message: Optional[str] = None,
    ) -> Iterator[None]:
        """Assert that a warning is generated with a given message.

        This method only supports code which generates a single warning.
        Tests which make use of code generating multiple warnings will
        need to manually catch their warnings.

        Args:
            cls (type, optional):
                The expected warning type.

                If not provided, this defaults to a
                :py:exc:`DeprecationWarning`.

            message (unicode, optional):
                The expected error message, if any.

        Context:
            The test to run.
        """
        warning_list: List[ExpectedWarning] = [
            {
                'cls': cls,
                'message': message,
            },
        ]

        with self.assertWarnings(warning_list):
            yield

    @contextmanager
    def assertWarnings(
        self,
        warning_list: List[ExpectedWarning],
    ) -> Iterator[None]:
        """Assert that multiple warnings were generated.

        This method accepts a sequence of warnings that must be matched in
        order. Each item must be an instance of a warning with a message.
        The type and messages of the warnings must match.

        Version Added:
            3.2

        Args:
            warning_list (list of dict, optional):
                The list of expected warnings, in order.

                Each item is a dictionary in the format described in
                :py:class:`ExpectedWarning`.

        Context:
            The test to run.
        """
        with warnings.catch_warnings(record=True) as w:
            # Some warnings such as DeprecationWarning are filtered by
            # default, stop filtering them.
            warnings.simplefilter('always')

            # We do need to ignore this one, though, or a lot of things will
            # fail. This is specific to Python 3.10 and the versions of six
            # in Django.
            warnings.filterwarnings(
                'ignore',
                r'_SixMetaPathImporter.find_spec\(\) not found')

            self.assertEqual(len(w), 0)

            try:
                yield
            finally:
                self.assertEqual(len(w), len(warning_list))

                for i, (emitted, expected) in enumerate(zip(w, warning_list),
                                                        start=1):
                    expected_cls = expected['cls']
                    expected_message = expected.get('message')

                    self.assertTrue(
                        issubclass(emitted.category, expected_cls),
                        'Warning #%d: Class %r != %r'
                        % (i, emitted.category, expected_cls))

                    if expected_message is not None:
                        self.assertEqual(
                            str(emitted.message),
                            expected_message,
                            'Warning #%d: Message %r != %r'
                            % (i, str(emitted.message), str(expected_message)))

    @contextmanager
    def assertNoWarnings(self):
        """Assert that a warning is not generated.

        Context:
            The test to run.
        """
        with self.assertWarnings([]):
            yield

    @contextmanager
    def assertQueries(
        self,
        queries: Sequence[Union[ExpectedQuery,
                                Dict[str, Any]]],
        num_statements: Optional[int] = None,
        *,
        with_tracebacks: bool = False,
        traceback_size: int = 15,
        check_subqueries: Optional[bool] = None,
    ) -> Iterator[None]:
        """Assert the number and complexity of queries.

        This provides advanced checking of queries, allowing the caller to
        match filtering, JOINs, ordering, selected fields, and more.

        This takes a list of dictionaries with query information. Each
        contains the keys in :py:class:`ExpectedQuery`.

        Version Changed:
            3.4:
            * Added ``with_tracebacks``, ``tracebacks_size``, and
              ``check_subqueries`` arguments.
            * Added support for type hints for expected queries.
            * The ``where`` queries are now normalized for easier comparison.
            * The assertion output now shows the executed queries on the
              left-hand side and the expected queries on the right-hand side,
              like most other assertion functions.
            * The number of expected and executed queries no longer need to
              be exact in order to see results.

        Version Added:
            3.0

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

                Version Added:
                    3.4

            tracebacks_size (int, optional):
                The size of any tracebacks, in number of lines.

                The default is 15.

                Version Added:
                    3.4

            check_subqueries (bool, optional):
                Whether to check subqueries.

                If enabled, ``inner_query`` on queries with subqueries will
                be checked. This is currently disabled by default, in order
                to avoid breaking tests, but will be enabled by default in
                Djblets 5.

                Version Added:
                    3.4

        Raises:
            AssertionError:
                The parameters passed, or the queries compared, failed
                expectations.
        """
        assert isinstance(queries, list)

        if num_statements is None:
            num_statements = len(queries)

        with catch_queries() as ctx:
            yield

        executed_queries = ctx.executed_queries
        queries_to_qs = ctx.queries_to_qs

        # Now we can compare numbers.
        error_lines: List[str] = []
        num_queries = len(queries)
        num_executed_queries = len(executed_queries)

        # Make sure we received the expected number of queries.
        if num_queries != num_executed_queries:
            error_lines += [
                'Expected %s queries, but got %s\n'
                % (num_queries, num_executed_queries),

                '',
            ]

            if num_queries < num_executed_queries:
                queries += [
                    ExpectedQuery()
                    for _i in range(num_executed_queries - num_queries)
                ]
            elif num_queries > num_executed_queries:
                queries = queries[:num_executed_queries]

        def _check_expectation(
            key: str,
            *,
            failures: List[_ExecutedQueryFailureInfo],
            expected_value: _T,
            executed_value: _T,
            match_func: Callable[[_T, _T], bool] = operator.__eq__,
            format_expected_value_func: Callable[[_T], str] = pformat,
            format_executed_value_func: Callable[[_T], str] = pformat,
        ) -> None:
            if not match_func(expected_value, executed_value):
                failures.append({
                    'key': key,
                    'executed_value': format_executed_value_func(
                        executed_value),
                    'expected_value': format_expected_value_func(
                        expected_value),
                })

        def _check_query(
            executed_query: SQLQuery,
            expected_query_info: ExpectedQuery,
        ) -> List[_ExecutedQueryFailureInfo]:
            failures: List[_ExecutedQueryFailureInfo] = []

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
                failures=failures,
                expected_value=expected_model,
                executed_value=executed_model,
                match_func=operator.is_)

            # Check the query type.
            _check_expectation(
                'type',
                failures=failures,
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
                    failures=failures,
                    expected_value=expected_query_info.get(key, default),
                    executed_value=getattr(executed_query, key))

            # Check 'extra'.
            _check_expectation(
                'extra',
                failures=failures,
                expected_value={
                    _key: (ws_re.sub(' ', _value[0]).strip(), _value[1])
                    for _key, _value in expected_query_info.get('extra',
                                                                {}).items()
                },
                executed_value={
                    _key: (ws_re.sub(' ', _value[0]).strip(), _value[1])
                    for _key, _value in executed_query.extra.items()
                })

            # Check 'offset'.
            _check_expectation(
                'offset',
                failures=failures,
                expected_value=expected_query_info.get('offset', 0),
                executed_value=executed_query.low_mark)

            # Check 'limit'.
            _check_expectation(
                'limit',
                failures=failures,
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
                failures=failures,
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
                failures=failures,
                expected_value=set(expected_query_info.get('tables',
                                                           tables_default)),
                executed_value=executed_tables)

            # Check 'only_fields'.
            _check_expectation(
                'only_fields',
                failures=failures,
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
                failures=failures,
                expected_value=expected_select_related,
                executed_value=executed_select_related)

            # Check 'where'. Normalize the Q object used to filter.
            _check_expectation(
                'where',
                failures=failures,
                expected_value=_normalize_q(expected_query_info.get('where',
                                                                    Q())),
                executed_value=_normalize_q(queries_to_qs.get(executed_query,
                                                              Q())),
                format_expected_value_func=_format_q,
                format_executed_value_func=_format_q)

            # Check if this is an aggregate query.
            expected_inner_query_info = expected_query_info.get('inner_query')

            if isinstance(executed_query, AggregateQuery):
                if check_subqueries:
                    # NOTE: As of October 23, 2023, django-stubs doesn't
                    #       document this attribute.
                    inner_query = executed_query.inner_query  # type: ignore

                    inner_failures = _check_query(
                        executed_query=inner_query,
                        expected_query_info=expected_inner_query_info or {})

                    if inner_failures:
                        failures.append({
                            'key': 'inner_query',
                            'inner_failures': inner_failures,
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
                    failures=failures,
                    expected_value=expected_inner_query_info,
                    executed_value=None)

            return failures

        def _serialize_failures(
            failures: List[_ExecutedQueryFailureInfo],
            *,
            indent_str: str = '  ',
        ) -> List[str]:
            error_lines: List[str] = []

            for failure in sorted(failures,
                                  key=lambda failure: failure['key']):
                key = failure['key']
                inner_failures = failure.get('inner_failures')

                if inner_failures is not None:
                    error_lines.append(f'{indent_str}{key}:')
                    error_lines += _serialize_failures(
                        inner_failures,
                        indent_str=f'{indent_str}  ')
                else:
                    executed_value = failure.get('executed_value')
                    expected_value = failure.get('expected_value')

                    assert executed_value is not None
                    assert expected_value is not None

                    # If we're formatting multi-line output, make sure to
                    # indent it properly.
                    if '\n' in executed_value or '\n' in expected_value:
                        executed_value = f'\n%s\n{indent_str}' % '\n'.join(
                            f'{indent_str}  {line}'
                            for line in executed_value.splitlines()
                        )
                        expected_value = '\n%s' % '\n'.join(
                            f'{indent_str}  {line}'
                            for line in expected_value.splitlines()
                        )

                    error_lines.append(
                        f'{indent_str}{key}: '
                        f'{executed_value} != {expected_value}')

            return error_lines

        # Go through each matching Query and compare state.
        ws_re = self.ws_re
        all_failures: List[_ExecutedQueryAllFailuresInfo] = []
        queries_iter = enumerate(zip(cast(Sequence[ExpectedQuery], queries),
                                     executed_queries))

        for i, (query_info, executed_query_info) in queries_iter:
            query_sql = executed_query_info['sql']

            # If this query didn't generate any SQL, then we want to skip it.
            if not query_sql:
                continue

            executed_query = executed_query_info['query']
            failures = _check_query(executed_query=executed_query,
                                    expected_query_info=query_info)

            if failures:
                all_failures.append({
                    'executed_query': executed_query,
                    'failures': failures,
                    'index': i,
                    'query_sql': query_sql,
                    'traceback': executed_query_info['traceback'],
                })

        # Check if we found any failures, and include them in an assertion.
        if all_failures:
            num_failures = len(all_failures)

            if num_failures == 1:
                error_lines.append('1 query failed to meet expectations.')
            else:
                error_lines.append(
                    '%s queries failed to meet expectations.'
                    % num_failures,
                )

            for failure_info in all_failures:
                failures = failure_info['failures']

                if failures:
                    i = failure_info['index']

                    error_lines += [
                        '',
                        'Query %s:' % (i + 1),
                    ] + _serialize_failures(failures) + [
                        '  SQL: %s' % _sql
                        for _sql in failure_info['query_sql']
                    ]

                    if with_tracebacks:
                        traceback_lines = \
                            failure_info['traceback'][-traceback_size:]
                        error_lines.append('Trace: %s'
                                           % ''.join(traceback_lines))

            self.fail('\n'.join(error_lines))


class TestModelsLoaderMixin(object):
    """Allows unit test modules to provide models to test against.

    This allows a unit test file to provide models that will be synced to the
    database and flushed after tests. These can be tested against in any unit
    tests.

    Typically, Django requires any test directories to be pre-added to
    INSTALLED_APPS in order for models to be created in the test database.

    This mixin works around this by dynamically adding the module to
    INSTALLED_APPS and forcing the database to be synced. It also will
    generate a fake 'models' module to satisfy Django's requirement, if one
    doesn't already exist.

    By default, this will assume that the test class's module is the one that
    should be added to INSTALLED_APPS. This can be changed by overriding
    :py:attr:`tests_app`.
    """
    tests_app = None

    @classmethod
    def setUpClass(cls):
        cls._tests_loader_models_mod = None

        if not cls.tests_app:
            cls.tests_app = cls.__module__

        models_mod_name = '%s.models' % cls.tests_app

        try:
            models_mod = import_module(models_mod_name)
        except ImportError:
            # Set up a 'models' module, containing any models local to the
            # module that this TestCase is in.

            # It's not enough to simply create a module type. We need to
            # create a basic spec, and then we need to have the module
            # system create a module from it. There's a handy public
            # function to do this on Python 3.5, but Python 3.4 lacks a
            # public function. Fortunately, it's easy to call a private
            # one.
            spec = ModuleSpec(name=models_mod_name,
                              loader=None)

            models_mod = module_from_spec(spec)
            assert models_mod

            # Transfer all the models over into this new module.
            module_name = cls.__module__
            test_module = sys.modules[module_name]

            for key, value in test_module.__dict__.items():
                if (inspect.isclass(value) and
                    issubclass(value, Model) and
                    value.__module__ == module_name):
                    models_mod.__dict__[key] = value

        cls._tests_loader_models_mod = models_mod

        if models_mod:
            sys.modules[models_mod.__name__] = models_mod

        cls._models_loader_old_settings = settings.INSTALLED_APPS
        settings.INSTALLED_APPS = list(settings.INSTALLED_APPS) + [
            cls.tests_app,
        ]

        # If Django Evolution is being used, we'll want to clear out any
        # recorded schema information so that it can be generated from
        # scratch when we set up the database.
        if (Evolution is not None and
            Version is not None and
            getattr(settings, 'DJANGO_EVOLUTION_ENABLED', True)):
            Version.objects.all().delete()
            Evolution.objects.all().delete()

        # Push the new set of installed apps, and begin registering
        # each of the models associated with the tests.
        apps.set_installed_apps(settings.INSTALLED_APPS)
        app_config = apps.get_containing_app_config(cls.tests_app)

        if models_mod:
            app_label = app_config.label

            for key, value in models_mod.__dict__.items():
                if inspect.isclass(value) and issubclass(value, Model):
                    # The model was likely registered under another app,
                    # so we need to remove the old one and add the new
                    # one.
                    try:
                        del apps.all_models[value._meta.app_label][
                            value._meta.model_name]
                    except KeyError:
                        pass

                    value._meta.app_label = app_label
                    apps.register_model(app_label, value)

        call_command('migrate', run_syncdb=True, verbosity=0,
                     interactive=False)

        super(TestModelsLoaderMixin, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestModelsLoaderMixin, cls).tearDownClass()

        call_command('flush', verbosity=0, interactive=False)

        settings.INSTALLED_APPS = cls._models_loader_old_settings

        # If we added a fake 'models' module to sys.modules, remove it.
        models_mod = cls._tests_loader_models_mod

        if models_mod:
            try:
                del sys.modules[models_mod.__name__]
            except KeyError:
                pass

        apps.unset_installed_apps()
        apps.all_models[cls.tests_app].clear()

        # Set this free so the garbage collector can eat it.
        cls._tests_loader_models_mod = None


class FixturesCompilerMixin(object):
    """Compiles and efficiently loads fixtures into a test suite.

    Unlike Django's standard fixture support, this doesn't re-discover
    and re-deserialize the referenced fixtures every time they're needed.
    Instead, it precompiles the fixtures the first time they're found and
    reuses their objects for future tests.

    However, also unlike Django's, this does not accept compressed or
    non-JSON fixtures.
    """

    _precompiled_fixtures = {}
    _fixture_dirs = []

    def _fixture_setup(self):
        """Set up fixtures for unit tests."""
        # Temporarily hide the fixtures, so that the parent class won't
        # do anything with them.
        self._hide_fixtures = True
        super(FixturesCompilerMixin, self)._fixture_setup()
        self._hide_fixtures = False

        if getattr(self, 'multi_db', False):
            databases = connections
        else:
            databases = [DEFAULT_DB_ALIAS]

        if hasattr(self, 'fixtures'):
            for db in databases:
                self.load_fixtures(self.fixtures, db=db)

    def load_fixtures(self, fixtures, db=DEFAULT_DB_ALIAS):
        """Load fixtures for the current test.

        This is called for every fixture in the test case's ``fixtures``
        list. It can also be called by an individual test to add additional
        fixtures on top of that.

        Args:
            fixtures (list of unicode):
                The list of fixtures to load.

            db (unicode):
                The database name to load fixture data on.
        """
        if not fixtures:
            return

        if db not in self._precompiled_fixtures:
            self._precompiled_fixtures[db] = {}

        for fixture in fixtures:
            if fixture not in self._precompiled_fixtures[db]:
                self._precompile_fixture(fixture, db)

        self._load_fixtures(fixtures, db)

    def _precompile_fixture(self, fixture, db):
        """Precompile a fixture.

        The fixture is loaded and deserialized, and the resulting objects
        are stored for future use.

        Args:
            fixture (unicode):
                The name of the fixture.

            db (unicode):
                The database name to load fixture data on.
        """
        assert db in self._precompiled_fixtures
        assert fixture not in self._precompiled_fixtures[db]

        fixture_path = None

        for fixture_dir in self._get_fixture_dirs():
            fixture_path = os.path.join(fixture_dir, fixture + '.json')

            if os.path.exists(fixture_path):
                break

        try:
            if not fixture_path:
                raise IOError('Fixture path not found')

            with open(fixture_path, 'r') as fp:
                self._precompiled_fixtures[db][fixture] = [
                    obj
                    for obj in serializers.deserialize('json', fp, using=db)
                    if ((hasattr(router, 'allow_syncdb') and
                         router.allow_syncdb(db, obj.object.__class__)) or
                        (hasattr(router, 'allow_migrate_model') and
                         router.allow_migrate_model(db, obj.object)))
                ]
        except IOError as e:
            sys.stderr.write('Unable to load fixture %s: %s\n' % (fixture, e))

    def _get_fixture_dirs(self):
        """Return the list of fixture directories.

        This is computed only once and cached.

        Returns:
            The list of fixture directories.
        """
        if not self._fixture_dirs:
            app_module_paths = []

            for app in self._get_app_model_modules():
                if hasattr(app, '__path__'):
                    # It's a 'models/' subpackage.
                    for path in app.__path__:
                        app_module_paths.append(path)
                else:
                    # It's a models.py module
                    app_module_paths.append(app.__file__)

            all_fixture_dirs = [
                os.path.join(os.path.dirname(path), 'fixtures')
                for path in app_module_paths
            ]

            self._fixture_dirs = [
                fixture_dir
                for fixture_dir in all_fixture_dirs
                if os.path.exists(fixture_dir)
            ]

        return self._fixture_dirs

    def _load_fixtures(self, fixtures, db):
        """Load precompiled fixtures.

        Each precompiled fixture is loaded and then used to populate the
        database.

        Args:
            fixtures (list of unicode):
                The list of fixtures to load.

            db (unicode):
                The database name to load fixture data on.
        """
        table_names = set()
        connection = connections[db]

        with connection.constraint_checks_disabled():
            for fixture in fixtures:
                assert db in self._precompiled_fixtures
                assert fixture in self._precompiled_fixtures[db]
                deserialized_objs = self._precompiled_fixtures[db][fixture]

                to_save = OrderedDict()
                to_save_m2m = []

                # Start off by going through the list of deserialized object
                # information from the fixtures and group them into categories
                # that we'll further filter down later.
                for deserialized_obj in deserialized_objs:
                    obj = deserialized_obj.object

                    table_names.add(obj._meta.db_table)
                    to_save.setdefault(type(obj), []).append(obj)

                    if deserialized_obj.m2m_data:
                        to_save_m2m.append((obj, deserialized_obj.m2m_data))

                # Now we'll break this down into objects we can batch-create
                # and ones we have to update.
                #
                # The database may already have entries for some of these
                # models, particularly if they're being shared across multiple
                # tests for the same suite. In that case, when doing a save()
                # on an object, Django will perform a update-or-create
                # operation, involving an UPDATE statement followed by an
                # INSERT If the UPDATE returned 0 rows.
                #
                # That's wasteful. Instead, we're going to just delete
                # everything matching the deserialized objects' IDs and then
                # bulk-create new entries.
                try:
                    for model_cls, objs in to_save.items():
                        obj_ids = [
                            _obj.pk
                            for _obj in objs
                            if _obj.pk
                        ]

                        if obj_ids:
                            model_cls.objects.filter(pk__in=obj_ids).delete()

                        model_cls.objects.using(db).bulk_create(objs)
                except (DatabaseError, IntegrityError) as e:
                    meta = model_cls._meta
                    sys.stderr.write(
                        'Could not load %s.%s from fixture "%s": %s\n'
                        % (meta.app_label,
                           meta.object_name,
                           fixture,
                           e))
                    raise

                # Now save any Many-to-Many field relations.
                #
                # Note that we're not assigning the values to the
                # ManyToManyField attribute. Instead, we're getting the add()
                # method and calling that. We can trust that the relations are
                # empty (since we've newly-created the object), so we don't
                # need to clear the old list first.
                for obj, m2m_data in to_save_m2m:
                    try:
                        for m2m_attr, m2m_objs in m2m_data.items():
                            getattr(obj, m2m_attr).add(*m2m_objs)
                    except (DatabaseError, IntegrityError) as e:
                        meta = obj._meta
                        sys.stderr.write(
                            'Could not load Many-to-Many entries for %s.%s '
                            '(pk=%s) in fixture "%s": %s\n'
                            % (meta.app_label,
                               meta.object_name,
                               obj.pk,
                               fixture,
                               e))
                        raise

        # We disabled constraints above, so check now.
        connection.check_constraints(table_names=sorted(table_names))

    def _get_app_model_modules(self):
        """Return the entire list of registered Django app models modules.

        This is an internal utility function that's used to provide
        compatibility with all supported versions of Django.

        Returns:
            list:
            The list of Django applications.
        """
        return [
            app.models_module
            for app in apps.get_app_configs()
            if app.models_module
        ]

    def __getattribute__(self, name):
        if name == 'fixtures' and self.__dict__.get('_hide_fixtures'):
            raise AttributeError

        return super(FixturesCompilerMixin, self).__getattribute__(name)


class TagTest(TestCase):
    """Base testing setup for custom template tags"""

    def setUp(self):
        self.parser = StubParser(self.getContentText())

    def getContentText(self):
        return "content"


# The following is all based on the code at
# http://trac.getwindmill.com/browser/trunk/windmill/authoring/djangotest.py,
# which is based on the changes submitted for Django in ticket 2879
# (http://code.djangoproject.com/ticket/2879)
#
# A lot of this can go away when/if this patch is committed to Django.

# Code from django_live_server_r8458.diff
#     @ http://code.djangoproject.com/ticket/2879#comment:41
# Editing to monkey patch django rather than be in trunk

class StoppableWSGIServer(basehttp.WSGIServer):
    """
    WSGIServer with short timeout, so that server thread can stop this server.
    """
    def server_bind(self):
        """Sets timeout to 1 second."""
        basehttp.WSGIServer.server_bind(self)
        self.socket.settimeout(1)

    def get_request(self):
        """Checks for timeout when getting request."""
        try:
            sock, address = self.socket.accept()
            sock.settimeout(None)
            return (sock, address)
        except socket.timeout:
            raise


class WSGIRequestHandler(basehttp.WSGIRequestHandler):
    """A custom WSGIRequestHandler that logs all output to stdout.

    Normally, WSGIRequestHandler will color-code messages and log them
    to stderr. It also filters out admin and favicon.ico requests. We don't
    need any of this, and certainly don't want it in stderr, as we'd like
    to only show it on failure.
    """
    def log_message(self, format, *args):
        print(format % args)


class TestServerThread(threading.Thread):
    """Thread for running a http server while tests are running."""

    def __init__(self, address, port):
        self.address = address
        self.port = port
        self._stopevent = threading.Event()
        self.started = threading.Event()
        self.error = None
        super(TestServerThread, self).__init__()

    def run(self):
        """
        Sets up test server and database and loops over handling http requests.
        """
        try:
            handler = basehttp.AdminMediaHandler(WSGIHandler())
            server_address = (self.address, self.port)
            httpd = StoppableWSGIServer(server_address,
                                        WSGIRequestHandler)
            httpd.set_app(handler)
            self.started.set()
        except basehttp.WSGIServerException as e:
            self.error = e
            self.started.set()
            return

        # Must do database stuff in this new thread if database in memory.
        from django.conf import settings

        if hasattr(settings, 'DATABASES'):
            db_engine = settings.DATABASES['default']['ENGINE']
            test_db_name = settings.DATABASES['default']['TEST_NAME']
        else:
            db_engine = settings.DATABASE_ENGINE
            test_db_name = settings.TEST_DATABASE_NAME

        if (db_engine.endswith('sqlite3') and
            (not test_db_name or test_db_name == ':memory:')):
            # Import the fixture data into the test database.
            if hasattr(self, 'fixtures'):
                # We have to use this slightly awkward syntax due to the fact
                # that we're using *args and **kwargs together.
                testcases.call_command('loaddata', verbosity=0, *self.fixtures)

        # Loop until we get a stop event.
        while not self._stopevent.isSet():
            httpd.handle_request()

    def join(self, timeout=None):
        """Stop the thread and wait for it to finish."""
        self._stopevent.set()
        threading.Thread.join(self, timeout)


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
            children_fmt.append('%s %s' % (indent_str, force_text(child)))

    children_str = '\n'.join(children_fmt)

    return template % (q.connector, children_str)
