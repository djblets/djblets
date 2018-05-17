"""Base support for consent types, data, and requirements."""

from __future__ import unicode_literals

try:
    # Python >= 3.4
    from enum import Enum
except ImportError:
    # Python < 3.4
    Enum = object

import dateutil.parser
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _


class Consent(Enum):
    """Values for representing consent decisions."""

    #: Consent has not been set.
    UNSET = 0

    #: Consent was granted.
    GRANTED = 1

    #: Consent was denied.
    DENIED = 2


class ConsentData(object):
    """Data representing a granted or denied consent for a requirement.

    This tracks data about granted or denied consent for use in both setting
    a consent decision and for recording in an audit trail. The data tracks
    a number of important bits of information for later proving that consent
    was granted or denied at a particular point in time.

    Note that this does not track unset consent. It's only used when a decision
    was specifically made.

    Attributes:
        granted (bool):
            Whether consent was granted (``True``) or denied (``False``).

        extra_data (dict):
            Additional data to include that may be relevant for an audit.
            This can contain any information, and is up to the caller to
            determine.

        requirement_id (unicode):
            The ID of a :py:class:`ConsentRequirement` for which consent was
            granted or denied.

        source (unicode):
            The source where consent was decided. This is free-form text,
            and may represent a URL, API endpoint, or include other additional
            source-identifying information.

        timestamp (datetime.datetime):
            The date/time when the consent was decided.
    """

    @classmethod
    def parse_audit_info(cls, requirement_id, data):
        """Parse stored audit information.

        This data may come from the database or another tracking store.

        Args:
            requirement_id (unicode):
                The ID of a :py:class:`ConsentRequirement` for which consent
                was granted or denied.

            data (dict):
                The deserialized data to parse.

        Returns:
            ConsentData:
            The resulting consent data from the audit log.
        """
        return cls(requirement_id=requirement_id,
                   granted=data['granted'],
                   timestamp=dateutil.parser.parse(data['timestamp']),
                   source=data.get('source'),
                   extra_data=data.get('extra_data'))

    def __init__(self, requirement_id, granted=False, timestamp=None,
                 source=None, extra_data=None):
        """Initialize the consent data.

        Args:
            requirement_id (unicode):
                The ID of a :py:class:`ConsentRequirement` for which consent
                was granted or denied.

            granted (bool, optional):
                Whether consent was granted (``True``) or denied (``False``).
                Defaults to denied.

            timestamp (datetime.datetime, optional):
                The date/time when the consent was decided. If not specified,
                the current date/time will be used.

            source (unicode, optional):
                The source where consent was decided. This is free-form text,
                and may represent a URL, API endpoint, or include other
                additional source-identifying information.

            extra_data (dict, optional):
                Additional data to include that may be relevant for an audit.
                This can contain any information, and is up to the caller to
                determine.
        """
        self.requirement_id = requirement_id
        self.granted = granted
        self.timestamp = timestamp or timezone.now()
        self.source = source
        self.extra_data = extra_data

    def serialize_audit_info(self, identifier):
        """Serialize the consent data for audit tracking.

        Args:
            identifier (unicode):
                The identifier to store along with the rest of the data,
                to help identify the data subject at that point in time. This
                is considered opaque, and is up to the consent tracker.

        Returns:
            dict:
            Serialized data for the audit log.
        """
        result = {
            'identifier': identifier,
            'granted': self.granted,
            'timestamp': self.timestamp.isoformat(),
        }

        if self.source:
            result['source'] = self.source

        if self.extra_data:
            result['extra_data'] = self.extra_data

        return result


class BaseConsentRequirement(object):
    """Represents an aspect of the product requiring consent.

    For every piece of a product that requires consent (sending data to a
    tracking service, for instance), a Requirement must be registered in the
    :py:class:`registry
    <djblets.privacy.consent.registry.ConsentRequirementRegistry>`.

    This lists information on the requirement, describing it and optionally
    providing a URL for learning more about it (which may point to a privacy
    policy).

    It also contains helper functions to perform the lookups and generate
    consent data for this requirement.
    """

    #: The unique ID of the requirement.
    requirement_id = None

    #: The name of the requirement.
    name = None

    #: A brief summary of the requirement.
    summary = None

    #: A short description of why the requirement is needed.
    intent_description = None

    #: A short description of what data will be sent and how it will be used.
    data_use_description = None

    #: Text to use for the allow action.
    allow_text = _('Allow')

    #: Text to use for when the allow action is selected.
    allowed_text = _('Allowed')

    #: Text to use for the block action.
    block_text = _('Block')

    #: Text to use for when the block action is selected.
    blocked_text = _('Blocked')

    #: The icons used to represent this service or topic.
    #:
    #: This is in the form of a dictionary of icon resolution indicators (for
    #: ``srcset`` values) to URLs or relative static media paths.
    icons = {}

    def get_consent(self, user):
        """Return the user's consent decision for this requirement.

        Args:
            user (django.contrib.auth.models.User):
                The user who made a decision on consent for this requirement.

        Returns:
            djblets.privacy.consent.base.Consent:
            The user's consent decision for this requirement.
        """
        from djblets.privacy.consent.tracker import get_consent_tracker

        return get_consent_tracker().get_consent(user, self.requirement_id)

    def build_consent_data(self, **kwargs):
        """Returns ConsentData for this requirement.

        Args:
            **kwargs (dict):
                Positional arguments to pass to :py:class:`ConsentData`.

        Returns:
            ConsentData:
            The resulting consent data for this requirement and the specified
            arguments.
        """
        return ConsentData(requirement_id=self.requirement_id, **kwargs)
