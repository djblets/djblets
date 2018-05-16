"""Common consent requirements for use in applications.

This provides some basic definitions with standard requirement IDs that can be
further customized by applications needing to offer consent for services.
"""

from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from djblets.privacy.consent.base import BaseConsentRequirement


class BaseGravatarConsentRequirement(BaseConsentRequirement):
    """Base consent requirement for Gravatar usage.

    This supplies a requirement ID, name, default summary, and default data
    use description for Gravatar consent requirements. Subclasses should
    provide their own intent and data use descriptions.
    """

    requirement_id = 'gravatar'
    name = _('Gravatar')
    summary = _("We'd like to use Gravatar.com for your avatars")

    data_use_description = _(
        "Gravatar will receive a one-way hashed version of your e-mail "
        "address. This is not personally identifiable, but could potentially "
        "be used to track you across multiple sites that use Gravatar. "
        "Gravatar only has an avatar for you if you've set one with their "
        "service."
    )


class BaseIntercomConsentRequirement(BaseConsentRequirement):
    """Base consent requirement for Intercom usage.

    This supplies a requirement ID, name, and default summary for Intercom
    consent requirements. Subclasses should provide their own intent and
    data use descriptions.
    """

    requirement_id = 'intercom'
    name = 'Intercom'
    summary = _("We'd like to support and track activity using Intercom")
