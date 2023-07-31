"""General utility functions for working with e-mail."""

from __future__ import annotations

from email.utils import escapesre, parseaddr, specialsre
from typing import Optional, TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    from django.contrib.auth.models import User


def build_email_address(
    email: str,
    full_name: Optional[str] = None,
) -> str:
    """Build an e-mail address for a To/CC/BCC field from a user's information.

    Args:
        email (str):
            The e-mail address.

        full_name (str, optional):
            The optional full name associated with the e-mail address.

    Returns:
        str:
        A formatted e-mail address intended for a To/CC/BCC field.
    """
    if full_name:
        escaped_name = escapesre.sub(r'\\\g<0>', full_name)

        if specialsre.search(full_name):
            escaped_name = '"%s"' % escaped_name

        return '%s <%s>' % (escaped_name, email)

    return email


def build_email_address_for_user(
    user: User,
) -> str:
    """Build an e-mail address for a To/CC/BCC field from a User.

    Args:
        user (django.contrib.auth.models.User):
            The user.

    Returns:
        str:
        A formatted e-mail address intended for a To/CC/BCC field.
    """
    return build_email_address(email=user.email,
                               full_name=user.get_full_name())


def build_email_address_via_service(
    email: str,
    full_name: Optional[str] = None,
    service_name: Optional[str] = None,
    sender_email: Optional[str] = None,
) -> str:
    """Build an e-mail address for sending on behalf of a user via a service.

    This will construct a formatted e-mail address that can be safely used
    in a :mailheader:`From` field without risking being quarantined/rejected
    by DMARC rules.

    The address will be in the form of "Full Name via Service Name
    <sender@domain.tld>".

    Args:
        email (str):
            The unformatted e-mail address of the user.

        full_name (str, optional):
            The full name of the user.

            If not provided, the username in the e-mail address will be used.

        service_name (str, optional):
            The name of the service sending the e-mail.

            If not provided, ``settings.EMAIL_DEFAULT_SENDER_SERVICE_NAME``
            will be used.

        sender_email (str, optional):
            The unformatted e-mail address for the sending service.

            If not provided, the e-mail address in
            :django:setting:`DEFAULT_FROM_EMAIL` will be used.

    Returns:
        str:
        A formatted e-mail address safe to use in a :mailheader:`From` field.
    """
    if not service_name:
        # A service name wasn't specified. We'll try to use the one from
        # settings, and if that doesn't exist, we'll use the domain name
        # from the sender (assuming it parsed, and if it didn't, there are
        # bigger problems we're not going to deal with here).
        service_name = (
            getattr(settings, 'EMAIL_DEFAULT_SENDER_SERVICE_NAME', None) or
            email.split('@')[-1]
        )

    if not sender_email:
        sender_email = parseaddr(settings.DEFAULT_FROM_EMAIL)[1]

    # We need a name from the user. If a full name wasn't
    # available, use the first part of the e-mail address.
    if not full_name:
        full_name = email.split('@')[0]

    return build_email_address(
        email=sender_email,
        full_name='%s via %s' % (full_name, service_name))
