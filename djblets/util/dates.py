"""Utilities for working with dates."""

import calendar
from datetime import datetime

from django.db.models import DateField
from django.utils.timezone import utc


def http_date(timestamp):
    """
    A wrapper around Django's http_date that accepts DateFields and
    datetime objects directly.
    """
    from django.utils.http import http_date

    if isinstance(timestamp, (DateField, datetime)):
        return http_date(calendar.timegm(timestamp.timetuple()))
    elif isinstance(timestamp, str):
        return timestamp
    else:
        return http_date(timestamp)


def get_latest_timestamp(timestamps):
    """
    Returns the latest timestamp in a list of timestamps.
    """
    latest = None

    for timestamp in timestamps:
        if latest is None or timestamp > latest:
            latest = timestamp

    return latest


def get_tz_aware_utcnow():
    """Returns a UTC aware datetime object"""
    return datetime.utcnow().replace(tzinfo=utc)
