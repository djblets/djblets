"""Siteconfig definitions for the log app."""

from djblets.log import DEFAULT_LOG_LEVEL

settings_map = {
    'logging_enabled':         'LOGGING_ENABLED',
    'logging_directory':       'LOGGING_DIRECTORY',
    'logging_allow_profiling': 'LOGGING_ALLOW_PROFILING',
    'logging_level':           'LOGGING_LEVEL',
}

defaults = {
    'logging_enabled':         False,
    'logging_directory':       None,
    'logging_allow_profiling': False,
    'logging_level':           DEFAULT_LOG_LEVEL,
}
