"""Utilities for capturing and inspecting database queries.

Deprecated:
    5.3:
    This has been replaced with :py:mod:`django_assert_queries.query_catcher`
    from :pypi:`django-assert-queries`.

Version Added:
    3.4
"""

from __future__ import annotations

from django_assert_queries.query_catcher import (
    CatchQueriesContext,
    ExecutedQueryInfo,
    ExecutedQueryType,
    ExecutedSubQueryInfo,
    catch_queries,
)
from housekeeping import module_deprecated

from djblets.deprecation import RemovedInDjblets70Warning


module_deprecated(
    RemovedInDjblets70Warning,
    'djblets.db.query_catcher is deprecated in favor of '
    'django_assert_queries.query_catcher, and will be removed in '
    'Djblets 7. See https://pypi.org/project/django-assert-queries/')


__all__ = [
    'CatchQueriesContext',
    'ExecutedQueryInfo',
    'ExecutedQueryType',
    'ExecutedSubQueryInfo',
    'catch_queries',
]
