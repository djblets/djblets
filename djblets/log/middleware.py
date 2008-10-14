import logging
import sys
import time
import traceback

from django.conf import settings
from django.db import connection
from django.db.backends import util

from djblets.log import init_logging, init_profile_logger


class CursorDebugWrapper(util.CursorDebugWrapper):
    """
    Replacement for CursorDebugWrapper which stores a traceback in
    `connection.queries`. This will dramatically increase the overhead of having
    DEBUG=True, so use with caution.
    """
    def execute(self, sql, params=()):
        start = time.time()
        try:
            return self.cursor.execute(sql, params)
        finally:
            stop = time.time()
            sql = self.db.ops.last_executed_query(self.cursor, sql, params)
            self.db.queries.append({
                'sql': sql,
                'time': stop - start,
                'stack': traceback.format_stack(),
            })
util.CursorDebugWrapper = CursorDebugWrapper


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
    """
    A piece of middleware that sets up logging.

    This a few settings to configure.

    LOGGING_ENABLED
    ---------------

    Default: False

    Sets whether or not logging is enabled.


    LOGGING_DIRECTORY
    -----------------

    Default: None

    Specifies the directory that log files should be stored in.
    This directory must be writable by the process running Django.


    LOGGING_NAME
    ------------

    Default: None

    The name of the log files, excluding the extension and path. This will
    usually be the name of the website or web application. The file extension
    will be automatically appended when the file is written.


    LOGGING_ALLOW_PROFILING
    -----------------------

    Default: False

    Specifies whether or not code profiling is allowed. If True, visiting
    any page with a ``?profiling=1`` parameter in the URL will cause the
    request to be profiled and stored in a ``.prof`` file using the defined
    ``LOGGING_DIRECTORY`` and ``LOGGING_NAME``.


    LOGGING_LINE_FORMAT
    -------------------

    Default: "%(asctime)s - %(levelname)s - %(message)s"

    The format for lines in the log file. See Python's logging documentation
    for possible values in the format string.


    LOGGING_LEVEL
    -------------

    Default: "DEBUG"

    The minimum level to log. Possible values are ``DEBUG``, ``INFO``,
    ``WARNING``, ``ERROR`` and ``CRITICAL``.
    """

    def process_request(self, request):
        """
        Processes an incoming request. This will set up logging.
        """
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
        if ('profiling' in request.GET and
            getattr(settings, "LOGGING_ALLOW_PROFILING", False)):

            init_profile_logger()

            from cStringIO import StringIO
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
            for sql, entries in queries.iteritems():
                time = sum((float(entry[0]) for entry in entries))
                tracebacks = '\n\n'.join((entry[1] for entry in entries))
                times[time] = \
                    'SQL Query profile (%d times, %.3fs average)\n%s\n\n%s\n\n' % \
                    (len(entries), time / len(entries), sql, tracebacks)

            sorted_times = sorted(times.keys(), reverse=1)
            for time in sorted_times:
                profile_log.log(logging.INFO, times[time])

        return response
