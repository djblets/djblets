"""General utility functions for working with e-mail."""

from __future__ import unicode_literals

from email.utils import formataddr


def build_email_address(email, full_name=None):
    """Build an e-mail address for a To/CC/BCC field from a user's information.

    Args:
        email (unicode):
            The e-mail address.

        full_name (unicode, optional):
            The optional full name associated with the e-mail address.

    Returns:
        unicode:
        A formatted e-mail address intended for a To/CC/BCC field.
    """
    return formataddr((full_name, email))


def build_email_address_for_user(user):
    """Build an e-mail address for a To/CC/BCC field from a User.

    Args:
        user (django.contrib.auth.models.User):
            The user.

    Returns:
        unicode:
        A formatted e-mail address intended for a To/CC/BCC field.
    """
    return build_email_address(email=user.email,
                               full_name=user.get_full_name())
