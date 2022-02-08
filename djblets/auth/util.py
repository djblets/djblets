"""Basic utility functions for authentication.

This contains some validation functions that may be useful for forms.
"""

from django.utils.translation import gettext as _


def validate_test_cookie(form, request):
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


def validate_old_password(form, user, field_name='password'):
    """Validate that the password given on a form was valid.

    This is intended for Password Change forms, and will check that the
    specified password in the form matches the user's current password.

    Args:
        form (django.forms.Form):
            The form using the validator and containing the field.

        user (django.contrib.auth.models.User):
            The user whose password is being changed.

        field_name (unicode, optional):
            The name of the password field.
    """
    if (not form.errors.get(field_name) and
        not user.check_password(form.data.get(field_name))):
        form.errors[field_name] = form.error_class([_('Incorrect password.')])
