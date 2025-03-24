"""Utilities for comparing executed queries to expectations.

These are used internally for unit testing, but can also be useful when
instrumenting code.

Deprecated:
    5.3:
    This has been replaced with
    :py:mod:`django_assert_queries.query_comparator` from
    :pypi:`django-assert-queries`.

Version Added:
    3.4
"""

from __future__ import annotations

from django_assert_queries.query_comparator import (
    CompareQueriesContext,
    ExpectedQueries,
    ExpectedQuery,
    QueryMismatch,
    QueryMismatchedAttr,
    compare_queries,
)
from housekeeping import module_deprecated

from djblets.deprecation import RemovedInDjblets70Warning


module_deprecated(
    RemovedInDjblets70Warning,
    'djblets.db.query_comparator is deprecated in favor of '
    'django_assert_queries.query_comparator, and will be removed in '
    'Djblets 7. See https://pypi.org/project/django-assert-queries/')


__all__ = [
    'CompareQueriesContext',
    'ExpectedQueries',
    'ExpectedQuery',
    'QueryMismatch',
    'QueryMismatchedAttr',
    'compare_queries',
]
