from __future__ import unicode_literals
from ast import literal_eval
import json

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import six


def decode_janky_json(value):
    try:
        decoded = json.loads(value, encoding=settings.DEFAULT_CHARSET)

        # XXX Sometimes things get double-encoded. We don't have a solid repro
        #     case.
        if isinstance(decoded, basestring):
            logging.warning("JSONField decode error. Expected dictionary, got "
                            "string for input '%s'",
                            value)
            decoded = json.loads(decoded, encoding=settings.DEFAULT_CHARSET)
    except ValueError:
        # There's probably embedded unicode markers (like u'foo') in the
        # string. This will evaluate it as python types instead of json.
        try:
            decoded = literal_eval(value)
        except Exception as e:
            logging.error("Failed to eval and decode JSONField data '%r': %s",
                          value, e)
            decoded = {}

        if isinstance(decoded, basestring):
            logging.error("JSONField decode error after literal_eval. "
                          "Expected dictionary, got string for input '%s'",
                          value)
            decoded = {}

    return decoded


def validate_json(value):
    """Validates content going into a JSONField.

    This will raise a ValidationError if the value is a string
    (representing a serialized JSON payload, possibly from the admin UI)
    and cannot be loaded properly.
    """
    if isinstance(value, six.string_types):
        try:
            decode_janky_json(value)
        except ValueError as e:
            raise ValidationError(unicode(e), code='invalid')
