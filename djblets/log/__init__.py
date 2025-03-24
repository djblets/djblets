"""Logging support.

This can be used to offer some advanced logging capabilities.

Note that this predates Django's modern logging support, and is here primarily
for compatibility.


Settings
========

The following settings control logging.


LOGGING_ENABLED
---------------

Default: ``False``

Sets whether or not logging is enabled.


LOGGING_DIRECTORY
-----------------

Default: ``None``

Specifies the directory that log files should be stored in.
This directory must be writable by the process running Django.


LOGGING_NAME
------------

Default: ``None``

The name of the log files, excluding the extension and path. This will
usually be the name of the website or web application. The file extension
will be automatically appended when the file is written.


LOGGING_ALLOW_PROFILING
-----------------------

Default: ``False``

Specifies whether or not code profiling is allowed. If True, visiting
any page with a ``?profiling=1`` parameter in the URL will cause the
request to be profiled and stored in a ``.prof`` file using the defined
``LOGGING_DIRECTORY`` and ``LOGGING_NAME``.


LOGGING_LINE_FORMAT
-------------------

Default: ``"%(asctime)s - %(levelname)s - %(message)s"``

The format for lines in the log file. See Python's :py:mod:`logging`
documentation for possible values in the format string.


LOGGING_PAGE_TIMES
------------------

Default: ``False``

If enabled, page access times will be logged. Specifically, it will log
the initial request, the finished render and response, and the total
time it look.

The username and page URL will be included in the logs.


LOGGING_LEVEL
-------------

Default: ``"DEBUG"``

The minimum level to log. Possible values are ``"DEBUG"``, ``"INFO"``,
``"WARNING"``, ``"ERROR"`` and ``"CRITICAL"``.


LOGGING_BLACKLIST
-----------------

Default: ``['django.db.backends']``

A list of logger names to exclude from the logs. Each logger with the given
name will be filtered out, along with any descendents of those loggers.


LOGGING_TO_STDOUT
-----------------

.. versionadded:: 1.0.17
.. versionadded:: 2.2

Default: ``False``

Whether to log output to stdout. This would be in addition to any other
configured logging, and is intended for environments like Docker.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from datetime import datetime, timezone
from functools import update_wrapper
from typing import Literal, Mapping, Optional, TYPE_CHECKING
from uuid import uuid4

from django.conf import settings
from housekeeping import deprecate_non_keyword_only_args

from djblets.deprecation import RemovedInDjblets70Warning

if TYPE_CHECKING:
    from django.http import HttpRequest


_logging_setup = False
_profile_log = None

DEFAULT_LOG_LEVEL = "DEBUG"
DEFAULT_LINE_FORMAT = \
    "%(asctime)s - %(levelname)s - %(request_info)s - %(name)s - %(message)s"
DEFAULT_REQUEST_FORMAT = '%(user)s - %(path)s'


class TimedLogInfo:
    """Tracks the time between operations for logging purposes.

    This is created and returned by :py:func:`log_timed` to track how long
    an operation takes, warning or critical-erroring if it takes too long.
    """

    ######################
    # Instance variables #
    ######################

    #: The number of seconds at which to log critical errors.
    critical_at: float

    #: The default log level for the timing information.
    default_level: int

    #: Extra information to include with all log items.
    #:
    #: This will be populated with ``request``.
    #:
    #: Version Added:
    #:     5.3
    extra: Mapping[str, object]

    #: The message to show for the log entries.
    message: str

    #: The logger used for all log entries.
    #:
    #: Version Added:
    #:     5.3
    logger: logging.Logger

    #: The optional HTTP request associated with the operation.
    request: Optional[HttpRequest]

    #: The start date/time for the operation.
    start_time: datetime

    #: The trace ID to include in log messages.
    #:
    #: This is used to help follow the chain of events in a series of logs.
    #:
    #: Version Added:
    #:     5.3
    trace_id: str

    #: The number of seconds at which to log warnings.
    warning_at: float

    @deprecate_non_keyword_only_args(RemovedInDjblets70Warning)
    def __init__(
        self,
        *,
        message: str,
        warning_at: float,
        critical_at: float,
        default_level: int,
        log_beginning: bool,
        request: Optional[HttpRequest],
        extra: Mapping[str, object] = {},
        logger: Optional[logging.Logger] = None,
        trace_id: Optional[str] = None,
    ) -> None:
        """Initialize the state for the timer.

        Version Changed:
            5.3:
            * This now expects keyword-only arguments. This will be required
              in Djblets 7.

            * Added ``extra``, ``logger``, and ``trace_id`` arguments.

            * ``warning_at`` and `critical_at`` now support fractions of
              seconds.

        Args:
            message (str):
                The message to show for the log entries.,

            warning_at (float):
                The number of seconds at which to log warnings.

                This may contain fractions of seconds.

                Version Changed:
                    5.3:
                    This now supports fractions of seconds.

            critical_at (float):
                The number of seconds at which to log critical errors.

                This may contain fractions of seconds.

                Version Changed:
                    5.3:
                    This now supports fractions of seconds.

            default_level (int):
                The default log level for the timing information.

            log_beginning (bool):
                Whether to log the beginning time for the operation.

            request (django.http.HttpRequest, optional):
                The HTTPoptional HTTP request associated with the operation.

            extra (dict, optional):
                Extra information to include with all log items.

                This will be populated with ``request`` and ``trace_id``.

                Version Added:
                    5.3

            logger (logging.Logger, optional):
                The logger used for all log entries.

                Version Added:
                    5.3

            trace_id (str, optional):
                The trace ID to include in log messages.

                This is used to help follow the chain of events in a series of
                logs.

                Version Added:
                    5.3
        """
        self.message = message
        self.warning_at = warning_at
        self.critical_at = critical_at
        self.default_level = default_level
        self.start_time = datetime.now(timezone.utc)
        self.request = request

        if logger is None:
            logger = logging.getLogger()

        if not trace_id:
            trace_id = str(uuid4())

        extra = {
            **extra,
            'request': self.request,
            'trace_id': trace_id,
        }

        self.extra = extra
        self.logger = logger
        self.trace_id = trace_id

        if log_beginning:
            logger.log(default_level,
                       f'[%s] Begin: {message}',
                       trace_id,
                       extra=extra)

    def __enter__(self) -> TimedLogInfo:
        """Enter the context for the timer.

        This will open the context and return itself, allowing the timer
        to automatically complete when the context ends.

        Context:
            TimedLogInfo:
            This object.
        """
        return self

    def __exit__(self, *args, **kwargs) -> Literal[False]:
        """Exit the context for the timer.

        This will log the end time of the operation, stopping the timer.

        Args:
            *args (tuple, unused):
                Unused positional arguments.

            **kwargs (dict, unused):
                Unused keyword arguments.
        """
        self.done()

        return False

    def done(self) -> None:
        """Stop the timed logging operation.

        The resulting time of the operation will be written to the log file.
        The log level depends on how long the operation takes.
        """
        delta = datetime.now(timezone.utc) - self.start_time
        level = self.default_level
        logger = self.logger
        message = self.message
        extra = self.extra
        trace_id = self.trace_id
        total_seconds = delta.total_seconds()

        if total_seconds >= self.critical_at:
            level = logging.CRITICAL
        elif total_seconds >= self.warning_at:
            level = logging.WARNING

        logger.log(self.default_level,
                   f'[%s] End: {message}',
                   trace_id,
                   extra=extra)
        logger.log(level,
                   f'[%s] {message} took %d.%06d seconds',
                   trace_id,
                   delta.seconds,
                   delta.microseconds,
                   extra=extra)


class RequestLogFormatter(logging.Formatter):
    def __init__(self, request_fmt, *args, **kwargs):
        super(RequestLogFormatter, self).__init__(*args, **kwargs)
        self.request_fmt = request_fmt

    def format(self, record):
        record.request_info = self.format_request(
            getattr(record, 'request', None))

        return logging.Formatter.format(self, record)

    def format_request(self, request):
        """Return formatted request information for the log message.

        The returned string will be based off the configured
        ``settings.LOGGING_REQUEST_FORMAT`` and keys in the request, if
        found.

        If anything from the request is missing, an empty string will be
        returned.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

        Returns:
            unicode:
            The request-specific string to include in the log message. This
            may be empty.
        """
        s = ''

        if request:
            try:
                s = self.request_fmt % request.__dict__
            except KeyError:
                # The request isn't populated with the keys expected in the
                # format string. Assume that we're logging before some
                # middleware or app configuration has had a chance to set
                # things up, and return an empty string.
                pass

        return s


class BlacklistFilter(logging.Filter):
    """Blacklists the provided loggers (and their children) from logging."""

    def __init__(self, names):
        """Initialize the filter.

        Args:
            names (list of unicode):
                A list of logger names. Each logger (and their children) will
                be excluded from the logs.
        """
        self._filters = [
            logging.Filter(name)
            for name in names
        ]

    def filter(self, record):
        """Return whether this record should be logged.

        The record is only logged if it's not in the list of any of the
        loggers on the blacklist, and if it doesn't have a parent logger
        listed.

        Args:
            record (logging.LogRecord):
                The record to filter.

        Returns:
            bool:
            ``True`` if the record can be logged. ``False`` if it must be
            ignored.
        """
        return all(not log_filter.filter(record)
                   for log_filter in self._filters)


def init_logging():
    """
    Sets up the main loggers, if they haven't already been set up.
    """
    global _logging_setup

    if _logging_setup:
        return

    enabled = getattr(settings, 'LOGGING_ENABLED', False)
    logging_to_stdout = getattr(settings, 'LOGGING_TO_STDOUT', False)
    log_directory = getattr(settings, 'LOGGING_DIRECTORY', None)
    log_name = getattr(settings, 'LOGGING_NAME', None)

    if (not enabled or
        (not logging_to_stdout and
         (not log_directory or not log_name))):
        return

    log_level_name = getattr(settings, 'LOGGING_LEVEL',
                             DEFAULT_LOG_LEVEL)
    log_level = logging.getLevelName(log_level_name)
    request_format_str = getattr(settings, 'LOGGING_REQUEST_FORMAT',
                                 DEFAULT_REQUEST_FORMAT)
    format_str = getattr(settings, 'LOGGING_LINE_FORMAT',
                         DEFAULT_LINE_FORMAT)
    log_blacklist = getattr(settings, 'LOGGING_BLACKLIST', [
        'django.db.backends',
    ])

    if log_directory and log_name:
        log_path = os.path.join(log_directory, '%s.log' % log_name)
    else:
        log_path = None

    formatter = RequestLogFormatter(request_format_str, format_str)
    logging_to_stderr = False

    root = logging.getLogger()

    if log_path:
        try:
            if sys.platform == 'win32':
                handler = logging.FileHandler(log_path)
            else:
                handler = logging.handlers.WatchedFileHandler(log_path)

            logging_to_stderr = False
        except IOError:
            if not logging_to_stdout:
                handler = logging.StreamHandler()
                logging_to_stderr = True
            else:
                handler = None

        if handler:
            handler.setLevel(log_level)
            handler.setFormatter(formatter)

            root.addHandler(handler)

        root.setLevel(log_level)

    if logging_to_stderr:
        logging.warning("Could not open logfile %s. Logging to stderr",
                        log_path)

    if not logging_to_stderr and (settings.DEBUG or logging_to_stdout):
        # In DEBUG mode, log to the console as well.
        console_log = logging.StreamHandler()
        console_log.setLevel(log_level)
        console_log.setFormatter(formatter)
        root.addHandler(console_log)

        logging.debug("Logging to %s with a minimum level of %s",
                      log_path, log_level_name)

    for handler in root.handlers:
        handler.addFilter(BlacklistFilter(log_blacklist))

    _logging_setup = True


def init_profile_logger():
    """
    Sets up the profiling logger, if it hasn't already been set up.
    """
    global _profile_log

    enabled = getattr(settings, 'LOGGING_ENABLED', False)
    log_directory = getattr(settings, 'LOGGING_DIRECTORY', None)
    log_name = getattr(settings, 'LOGGING_NAME', None)

    if (enabled and log_directory and log_name and not _profile_log and
        getattr(settings, "LOGGING_ALLOW_PROFILING", False)):

        filename = os.path.join(log_directory, log_name + ".prof")

        if sys.platform == 'win32':
            handler = logging.FileHandler(filename)
        else:
            handler = logging.handlers.WatchedFileHandler(filename)

        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))

        _profile_log = logging.getLogger("profile")
        _profile_log.addHandler(handler)


def restart_logging():
    """
    Restarts the logging. The next page view will set up the loggers
    based on any new settings.
    """
    global _logging_setup

    logging.debug('Reloading logging settings')

    for logger_id in ('profile', ''):
        logger = logging.getLogger(logger_id)

        while logger.handlers:
            handler = logger.handlers[0]
            handler.flush()
            logger.removeHandler(handler)

    _logging_setup = False

    init_logging()


@deprecate_non_keyword_only_args(RemovedInDjblets70Warning)
def log_timed(
    message: str,
    *,
    warning_at: float = 5,
    critical_at: float = 15,
    log_beginning: bool = True,
    default_level: int = logging.DEBUG,
    request: Optional[HttpRequest] = None,
    extra: Mapping[str, object] = {},
    logger: Optional[logging.Logger] = None,
    trace_id: Optional[str] = None,
) -> TimedLogInfo:
    """Times an operation, logging timing information at different thresholds.

    This will display a log message at the start of an operation and at the
    end, displaying the time taken for the operation. The final log entry's
    level will depend on the amount of time taken, switching to a warning if
    at ``warning_at`` seconds and a critical error at ``critical_at`` seconds.

    This function can be called directly or used as a context manager.

    Version Changed:
        5.3:
        * This can now be used as a context manager.

        * Added ``extra``, ``logger``, and ``trace_id`` arguments.

        * This now expects keyword-only arguments for all but ``message``.
          This will be required in Djblets 7.

        * ``warning_at`` and `critical_at`` now support fractions of seconds.

    Args:
        message (str):
            The message to show for the log entries.,

        warning_at (int):
            The number of seconds at which to log warnings.

            This may contain fractions of seconds.

            Version Changed:
                5.3:
                This now supports fractions of seconds.

        critical_at (int):
            The number of seconds at which to log critical errors.

            This may contain fractions of seconds.

            Version Changed:
                5.3:
                This now supports fractions of seconds.

        default_level (int):
            The default log level for the timing information.

        log_beginning (bool):
            Whether to log the beginning time for the operation.

        request (django.http.HttpRequest, optional):
            The optional HTTP request associated with the operation.

        extra (dict, optional):
            Extra information to include with all log items.

            This will be populated with ``request`` and ``trace_id``.

            Version Added:
                5.3

        logger (logging.Logger, optional):
            The logger used for all log entries.

            Version Added:
                5.3

        trace_id (str, optional):
            The trace ID to include in log messages.

            This is used to help follow the chain of events in a series of
            logs.

            If not provided, one will be generated. This can then be accessed
            on :py:attr:`TimedLogInfo.trace_id`.

            Version Added:
                5.3

    Example:
        .. code-block:: python

           from djblets.log import log_timed

           # As a direct function call:
           t = log_timed('Doing a thing')

           try:
               ...
           finally:
               t.done()

           # As a context manager:
           with log_timed('Doing a thing') as t:
               ...
    """
    return TimedLogInfo(message=message,
                        warning_at=warning_at,
                        critical_at=critical_at,
                        default_level=default_level,
                        log_beginning=log_beginning,
                        request=request,
                        extra=extra,
                        logger=logger,
                        trace_id=trace_id)


# Add support in Logger to take a request= parameter. This will apply to the
# root logger and all instances/subclasses of logging.Logger.
#
# Ideally, we would use logging.setLoggerClass() to set a custom Logger that
# understands request=, but the root logger wouldn't be affected and anything
# that called logging.getLogger('...') before this file was imported wouldn't
# benefit.
def _Logger_log(self, *args, **kwargs):
    extra = kwargs.pop('extra', {})
    request = kwargs.pop('request', None)

    if request:
        RemovedInDjblets70Warning.warn(
            "The request= argument to logging methods has been deprecated and "
            "will be removed in Djblets 7.0. Please change this to pass "
            "extra={'request': request}.")
        extra['request'] = request

    kwargs['extra'] = extra

    _old_log(self, *args, **kwargs)


_old_log = logging.Logger._log

if _old_log is not _Logger_log:
    update_wrapper(_Logger_log, logging.Logger._log)
    logging.Logger._log = _Logger_log
