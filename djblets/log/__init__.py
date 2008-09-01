from datetime import datetime
import logging
import os

from django.conf import settings


_logging_setup = False
_console_log = None
_profile_log = None

DEFAULT_LOG_LEVEL = "DEBUG"
DEFAULT_LINE_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"


class TimedLogInfo(object):
    """
    A utility class created by ``log_timed`` that handles the timed logging
    functionality and provides a way to end the timed logging operation.
    """
    def __init__(self, message, warning_at, critical_at, default_level,
                 log_beginning):
        self.message = message
        self.warning_at = warning_at
        self.critical_at = critical_at
        self.default_level = default_level
        self.start_time = datetime.now()

        if log_beginning:
            logging.log(self.default_level, "Begin: %s" % self.message)

    def done(self):
        """
        Stops the timed logging operation. The resulting time of the
        operation will be written to the log file. The log level depends
        on how long the operation takes.
        """
        delta = datetime.now() - self.start_time
        level = self.default_level

        if delta.seconds >= self.critical_at:
            level = logging.CRITICAL
        elif delta.seconds >= self.warning_at:
            level = logging.WARNING

        logging.log(self.default_level, "End: %s" % self.message)
        logging.log(level, "%s took %s.%s seconds" % (self.message,
                                                      delta.seconds,
                                                      delta.microseconds))


def init_logging():
    """
    Sets up the main loggers, if they haven't already been set up.
    """
    global _logging_setup

    if _logging_setup:
        return

    enabled = getattr(settings, 'LOGGING_ENABLED', False)
    log_directory = getattr(settings, 'LOGGING_DIRECTORY', None)
    log_name = getattr(settings, 'LOGGING_NAME', None)

    if not enabled or not log_directory or not log_name:
        return

    log_level_name = getattr(settings, 'LOGGING_LEVEL',
                             DEFAULT_LOG_LEVEL)
    log_level = logging.getLevelName(log_level_name)
    format_str = getattr(settings, 'LOGGING_LINE_FORMAT',
                         DEFAULT_LINE_FORMAT)

    log_path = os.path.join(log_directory, log_name + ".log")

    logging.basicConfig(
        level=log_level,
        format=format_str,
        filename=log_path,
        filemode='a'
    )

    if settings.DEBUG:
        # In DEBUG mode, log to the console as well.
        console_log = logging.StreamHandler()
        console_log.setLevel(log_level)
        console_log.setFormatter(logging.Formatter(format_str))
        logging.getLogger('').addHandler(console_log)

    logging.info("Logging to %s with a minimum level of %s",
                 log_path, log_level_name)

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
        handler = logging.FileHandler(
            os.path.join(log_directory, log_name + ".prof"))
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
    global _console_log
    global _profile_log

    logging.log(logging.INFO, "Reloading logging settings")

    if _profile_log:
        logging.getLogger("profile").removeHandler(_profile_log)

    if _console_log:
        _console_log.flush()
        logging.getLogger("").removeHandler(_console_log)

    _logging_setup = False
    _console_log = None
    _profile_log = None

    init_logging()


def log_timed(message, warning_at=5, critical_at=15,
              log_beginning=True, default_level=logging.DEBUG):
    """
    Times an operation, displaying a log message before and after the
    operation. The log level for the final log message containing the
    operation runtime will be based on the runtime, the ``warning_at`` and
    the ``critical_at`` parameters.
    """
    return TimedLogInfo(message, warning_at, critical_at, default_level,
                        log_beginning)
