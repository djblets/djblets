"""Basic utility functions for authentication.

This contains some validation functions that may be useful for forms.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.translation import gettext as _

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from django.forms import Form
    from django.http import HttpRequest


def validate_test_cookie(
    form: Form,
    request: HttpRequest,
) -> None:
    """Validate that the test cookie was properly set in a prior request.

    If the test cookie was not set, the given form's ``submit`` field will
    be set with an error saying that cookies must be enabled.

    Args:
        form (django.forms.Form):
            The form using the validator.

        request (django.http.HttpRequest):
            The HTTP request containing the test cookie.
    """
    if not request.session.test_cookie_worked():
        form.errors['submit'] = form.error_class(
            [_('Cookies must be enabled.')])


def validate_old_password(
    form: Form,
    user: User,
    field_name: str = 'password',
) -> None:
    """Validate that the password given on a form was valid.

    This is intended for Password Change forms, and will check that the
    specified password in the form matches the user's current password.

    Args:
        form (django.forms.Form):
            The form using the validator and containing the field.

        user (django.contrib.auth.models.User):
            The user whose password is being changed.

        field_name (str, optional):
            The name of the password field.
    """
    if not form.errors.get(field_name):
        password = form.data.get(field_name)

        if not isinstance(password, str) or not user.check_password(password):
            form.errors[field_name] = form.error_class([_('Incorrect password.')])
