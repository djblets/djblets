"""Middleware used for logging.

The middleware sets up some advanced logging capabilities for profiling
and exception logging.
"""

from __future__ import annotations

import io
import logging
import sys
import traceback
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.db import connection
from django.db.backends import utils as db_backend_utils
from django.db.backends.base.base import BaseDatabaseWrapper
from django.http import Http404
from django.utils.deprecation import MiddlewareMixin

from djblets.log import init_logging, init_profile_logger, log_timed

if TYPE_CHECKING:
    from typing import Any, Callable

    from django.http import HttpRequest, HttpResponse, HttpResponseBase


logger = logging.getLogger(__name__)


class CursorDebugWrapper(db_backend_utils.CursorDebugWrapper):
    """Debug cursor for databases that stores tracebacks in query logs.

    This is a replacement for the default debug wrapper for database cursors
    which stores a traceback in :py:attr:`connection.queries
    <django.db.connection.queries>`.

    This will dramatically increase the overhead of having
    ``settings.DEBUG=True``, so use with caution.
    """

    def execute(self, *args, **kwargs):
        """Execute a SQL statement.

        This will record an entry in the query log and attach a stack trace.

        Args:
            *args (tuple):
                Positional arguments for the parent method.

            **kwargs (dict):
                Keyword arguments for the parent method.

        Returns:
            object:
            The result of the statement.
        """
        try:
            return super(CursorDebugWrapper, self).execute(*args, **kwargs)
        finally:
            self._store_traceback(traceback.format_stack())

    def executemany(self, *args, **kwargs):
        """Execute multiple SQL statements.

        This will record an entry in the query log and attach a stack trace.

        Note that the Django ORM does not appear to actually make use of this
        method. Third-parties can still use it.

        Args:
            *args (tuple):
                Positional arguments for the parent method.

            **kwargs (dict):
                Keyword arguments for the parent method.

        Returns:
            object:
            The result of the statement.
        """
        try:
            return super(CursorDebugWrapper, self).executemany(*args, **kwargs)
        finally:
            self._store_traceback(traceback.format_stack())

    def _store_traceback(self, stack):
        """Store a traceback in the query log.

        This will look up the correct variable for the query log and add the
        stack trace to the last entry.

        Args:
            stack (unicode):
                The formatted stack trace.
        """
        queries = self.db.queries_log
        queries[-1]['stack'] = stack


# Return this cursor by default in the database backends. Custom backends
# potentially could override this.
BaseDatabaseWrapper.make_debug_cursor = \
    lambda self, cursor: CursorDebugWrapper(cursor, self)


def reformat_sql(sql):
    sql = sql.replace('`,`', '`, `')
    sql = sql.replace('SELECT ', 'SELECT\t')
    sql = sql.replace('` FROM ', '`\nFROM\t')
    sql = sql.replace(' WHERE ', '\nWHERE\t')
    sql = sql.replace(' INNER JOIN ', '\nINNER JOIN\t')
    sql = sql.replace(' LEFT OUTER JOIN ', '\nLEFT OUTER JOIN\t')
    sql = sql.replace(' OUTER JOIN ', '\nOUTER JOIN\t')
    sql = sql.replace(' ON ', '\n    ON ')
    sql = sql.replace(' ORDER BY ', '\nORDER BY\t')
    return sql


class LoggingMiddleware(MiddlewareMixin):
    """A piece of middleware that sets up page timing and profile logging.

    This is needed if using ``settings.LOGGING_PAGE_TIMES`` or
    ``settings.LOGGING_ALLOW_PROFILING``, in order to handle additional
    logging for page times and detailed profiling for debugging.

    Version Changed:
        6.1.1:
        A profiling request no longer turns on ``settings.DEBUG`` for the
        whole process. Impact is limited to the HTTP request.
    """

    #: Exceptions that should be ignored by this logger.
    #:
    #: Each of these are handled by Django itself on the HTTP layer. We don't
    #: want to do any extra/unwanted logging of these.
    ignored_exceptions = (Http404, PermissionDenied, SuspiciousOperation)

    def process_request(
        self,
        request: HttpRequest,
    ) -> None:
        """Process an incoming request.

        If ``settings.LOGGING_PAGE_TIMES`` is enabled, this will begin logging
        the starting time for this HTTP request.

        If ``profiling`` is passed in to the query string and
        ``settings.LOGGING_ALLOW_PROFILING`` is enabled, cursor debug logging
        will be turned on for the request and profiling will be performed for
        any views.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.
        """
        if getattr(settings, 'LOGGING_PAGE_TIMES', False):
            setattr(
                request,
                '_djblets_page_timedloginfo',
                log_timed(
                    f'Page request: HTTP {request.method} {request.path} '
                    f'(by {request.user})'
                ),
            )

        if ('profiling' in request.GET and
            getattr(settings, 'LOGGING_ALLOW_PROFILING', False)):
            # Turn on cursor debug logging for this request only.
            connection.force_debug_cursor = True

    def process_view(
        self,
        request: HttpRequest,
        callback: Callable[..., HttpResponse],
        callback_args: tuple[Any, ...],
        callback_kwargs: dict[str, Any],
    ) -> HttpResponse | None:
        """Process a view.

        If profiling is enabled for this request, a profile will be created
        and used to instrument the view being run.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            callback (callable):
                The view function to call.

            callback_args (tuple):
                Positional arguments to pass to the view.

            callback_kwargs (dict):
                Keyword arguments to pass to the view.

        Returns:
            django.http.HttpResponse:
            The HTTP response to return and process.
        """
        # Initialize logging.
        #
        # Note that this should probably live in process_request(), but this
        # has been here a long time and shouldn't be moved without some
        # testing and a major version bump (or, really, a port to modern
        # middleware).
        init_logging()

        if ('profiling' in request.GET and
            getattr(settings, 'LOGGING_ALLOW_PROFILING', False)):
            # Create a profiler tied to this request and use it to run the
            # view.
            import cProfile
            profiler = cProfile.Profile()
            setattr(request, '_djblets_profiler', profiler)

            return profiler.runcall(
                callback,
                request,
                *callback_args,
                **callback_kwargs,
            )

        # Use the default behavior to run the view.
        return None

    def process_response(
        self,
        request: HttpRequest,
        response: HttpResponseBase,
    ) -> HttpResponseBase:
        """Process a response.

        If page timing is enabled, this will log the page times to the main
        log file.

        If profiling is enabled, this will dump the resulting information to
        the profile log file.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            response (django.http.HttpResponseBase):
                The HTTP response to process.

        Returns:
            django.http.HttpResponseBase:
            The resulting HTTP response.
        """
        # If page timing is enabled, output the result.
        timedloginfo = getattr(request, '_djblets_page_timedloginfo', None)

        if timedloginfo:
            timedloginfo.done()

        # Check if a profiler was set up for this request.
        profiler = getattr(request, '_djblets_profiler', None)

        if profiler is not None:
            # Profiling is enabled, so gather information and send it to the
            # profiling log file.
            init_profile_logger()

            # connection.queries is a property that creates a fresh copy
            # on access, so make sure to fetch it once up-front.
            connection_queries = connection.queries

            profiler.create_stats()

            # Capture the stats
            out = io.StringIO()
            old_stdout, sys.stdout = sys.stdout, out
            profiler.print_stats(1)
            sys.stdout = old_stdout

            profile_log = logging.getLogger("profile")
            profile_log.log(logging.INFO,
                            "Profiling results for %s (HTTP %s):",
                            request.path, request.method)
            profile_log.log(logging.INFO, out.getvalue().strip())

            profile_log.log(logging.INFO,
                            '%d database queries made\n',
                            len(connection_queries))

            queries: dict[str, list[tuple[str, str]]] = {}

            for query in connection_queries:
                sql = reformat_sql(query['sql'])
                stack = ''.join(query['stack'][:-1])
                query_time = query['time']

                if sql in queries:
                    queries[sql].append((query_time, stack))
                else:
                    queries[sql] = [(query_time, stack)]

            times: dict[float, tuple[Any, ...]] = {}

            for sql, entries in queries.items():
                time = sum(
                    float(entry[0])
                    for entry in entries
                )
                tracebacks = '\n\n'.join(
                    entry[1]
                    for entry in entries
                )

                num_entries = len(entries)
                avg_time = time / num_entries

                times[time] = (
                    num_entries,
                    avg_time,
                    sql,
                    tracebacks,
                )

            for time in sorted(times.keys(),
                               reverse=True):
                profile_log.info(
                    'SQL Query profile (%s times, %.3fs average)\n'
                    '%s\n\n'
                    '%s\n\n',
                    *times[time],
                )

        # Check if profiling was requested, and if so, undo the debug cursor.
        #
        # This is a separate check from the above since we may have ended
        # up turning this on without processing a view (due to another
        # middleware returning a result, for example). We wouldn't have a
        # profiler in this case.
        if ('profiling' in request.GET and
            getattr(settings, 'LOGGING_ALLOW_PROFILING', False)):
            # Undo the debug cursor.
            connection.force_debug_cursor = False

        return response

    def process_exception(
        self,
        request: HttpRequest,
        exception: Exception,
    ) -> None:
        """Handle exceptions raised on a page.

        Logs the exception, along with the username and path where the
        exception occurred.

        Exceptions normally handled by Django's HTTP layer will be ignored.
        This helps avoid extraneous logging for 404 and Permission Denied
        errors.

        Args:
            request (django.http.HttpRequest):
                The HTTP request for the page.

            exception (Exception):
                The exception that was raised.
        """
        if not isinstance(exception, self.ignored_exceptions):
            logger.exception('Exception thrown for user %s at %s\n\n%s',
                             request.user, request.build_absolute_uri(),
                             exception,
                             extra={'request': request})
