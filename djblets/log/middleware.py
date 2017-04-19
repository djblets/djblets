"""Middleware used for logging.

The middleware sets up some advanced logging capabilities for profiling
and exception logging.
"""

from __future__ import unicode_literals

import logging
import sys
import traceback

from django.conf import settings
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.db import connection
from django.http import Http404
from django.utils import six
from django.utils.six.moves import cStringIO as StringIO

try:
    # Django >= 1.7
    from django.db.backends import utils as db_backend_utils
    from django.db.backends.base.base import BaseDatabaseWrapper
except ImportError:
    # Django < 1.7
    from django.db.backends import (util as db_backend_utils,
                                    BaseDatabaseWrapper)

from djblets.log import init_logging, init_profile_logger, log_timed


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
        try:
            # Django >= 1.8
            queries = self.db.queries_log
        except AttributeError:
            # Django < 1.8
            queries = self.db.queries

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


class LoggingMiddleware(object):
    """A piece of middleware that sets up page timing and profile logging.

    This is needed if using ``settings.LOGGING_PAGE_TIMES`` or
    ``settings.LOGGING_ALLOW_PROFILING``, in order to handle additional
    logging for page times and detailed profiling for debugging.
    """

    #: Exceptions that should be ignored by this logger.
    #:
    #: Each of these are handled by Django itself on the HTTP layer. We don't
    #: want to do any extra/unwanted logging of these.
    ignored_exceptions = (Http404, PermissionDenied, SuspiciousOperation)

    def process_request(self, request):
        """
        Processes an incoming request. This will set up logging.
        """
        if getattr(settings, 'LOGGING_PAGE_TIMES', False):
            request._page_timedloginfo = \
                log_timed('Page request: HTTP %s %s (by %s)' %
                          (request.method, request.path, request.user))

        if ('profiling' in request.GET and
            getattr(settings, "LOGGING_ALLOW_PROFILING", False)):
            settings.DEBUG = True

    def process_view(self, request, callback, callback_args, callback_kwargs):
        """
        Handler for processing a view. This will run the profiler on the view
        if profiling is allowed in the settings and the user specified the
        profiling parameter on the URL.
        """
        init_logging()

        if ('profiling' in request.GET and
            getattr(settings, "LOGGING_ALLOW_PROFILING", False)):
            import cProfile
            self.profiler = cProfile.Profile()
            args = (request,) + callback_args
            settings.DEBUG = True
            return self.profiler.runcall(callback, *args, **callback_kwargs)

    def process_response(self, request, response):
        """
        Handler for processing a response. Dumps the profiling information
        to the profile log file.
        """
        timedloginfo = getattr(request, '_page_timedloginfo', None)

        if timedloginfo:
            timedloginfo.done()

        if ('profiling' in request.GET and
            getattr(settings, "LOGGING_ALLOW_PROFILING", False)):

            init_profile_logger()

            self.profiler.create_stats()

            # Capture the stats
            out = StringIO()
            old_stdout, sys.stdout = sys.stdout, out
            self.profiler.print_stats(1)
            sys.stdout = old_stdout

            profile_log = logging.getLogger("profile")
            profile_log.log(logging.INFO,
                            "Profiling results for %s (HTTP %s):",
                            request.path, request.method)
            profile_log.log(logging.INFO, out.getvalue().strip())

            profile_log.log(logging.INFO,
                            '%d database queries made\n',
                            len(connection.queries))

            queries = {}
            for query in connection.queries:
                sql = reformat_sql(query['sql'])
                stack = ''.join(query['stack'][:-1])
                time = query['time']
                if sql in queries:
                    queries[sql].append((time, stack))
                else:
                    queries[sql] = [(time, stack)]

            times = {}
            for sql, entries in six.iteritems(queries):
                time = sum((float(entry[0]) for entry in entries))
                tracebacks = '\n\n'.join((entry[1] for entry in entries))
                times[time] = \
                    'SQL Query profile (%d times, %.3fs average)\n%s\n\n%s\n\n' % \
                    (len(entries), time / len(entries), sql, tracebacks)

            sorted_times = sorted(six.iterkeys(times), reverse=1)
            for time in sorted_times:
                profile_log.log(logging.INFO, times[time])

        return response

    def process_exception(self, request, exception):
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
                             request=request)
