import json

from django.core.exceptions import ValidationError


def validate_json(value):
    """Validates content going into a JSONField.

    This will raise a ValidationError if the value is a string
    (representing a serialized JSON payload, possibly from the admin UI)
    and cannot be loaded properly.
    """
    if isinstance(value, str):
        try:
            json.loads(value)
        except ValueError as e:
            raise ValidationError(str(e), code='invalid')
