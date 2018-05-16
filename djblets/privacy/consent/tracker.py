"""Consent tracking and storage capabilities."""

from __future__ import unicode_literals

import hashlib
from importlib import import_module

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.utils import six

from djblets.cache.backend import cache_memoize, make_cache_key
from djblets.db.query import get_object_or_none
from djblets.privacy.consent.base import Consent
from djblets.privacy.consent.registry import get_consent_requirements_registry
from djblets.privacy.models import StoredConsentData


class BaseConsentTracker(object):
    """Base class for a consent tracker.

    Consent trackers are responsible for storing and looking up consent
    information from a source. This can be the database, an external record
    kept outside the database, a secure vault, or some other location as
    supported by the specific consent tracker being used.

    By default, :py:class:`DatabaseConsentTracker` is used. This can be changed
    through ``settings.DJBLETS_PRIVACY_CONSENT_TRACKER``.
    """

    def get_audit_identifier(self, user):
        """Return an identifier to store for audit purposes.

        This is used to help locate stored consent, perhaps after a user
        account was unregistered, in order to prove later that a user did
        or did not consent to something.

        Data used in this identifier should never be used for any purpose
        other than locating the record for legal reasons. Stored audit
        identifiers may be erased at any time.

        By default, this returns a SHA256 hash representing the user's e-mail
        address, allowing lookups for known e-mail addresses without risking
        exposure. Subclasses can modify this.

        Args:
            user (django.contrib.auth.models.User):
                The user to return an identifier for.

        Returns:
            str:
            An identifier to store to help locate the record of consent.
        """
        return hashlib.sha256(user.email.encode('utf-8')).hexdigest()

    def record_consent_data(self, user, consent_data):
        """Record information on a consent decision made by a user.

        Args:
            user (django.contrib.auth.models.User):
                The user to record the consent decision for.

            consent_data (djblets.privacy.consent.base.ConsentData):
                Data on the consent decision.
        """
        self.record_consent_data_list(user, [consent_data])

    def get_consent(self, user, requirement_id):
        """Return the user's consent decision for a given requirement.

        Args:
            user (django.contrib.auth.models.User):
                The user who made a decision on consent for a requirement.

            requirement_id (unicode):
                The ID of the requirement to check on consent for.

        Returns:
            djblets.privacy.consent.base.Consent:
            The user's consent decision for the requirement.
        """
        consents = self.get_all_consent(user) or {}

        return consents.get(requirement_id, Consent.UNSET)

    def get_pending_consent_requirements(self, user):
        """Return a list of consent requirements that are pending decisions.

        This can be used to determine whether a user needs to be immediately
        shown a UI for deciding on consent.

        Args:
            user (django.contrib.auth.models.User):
                The user to check consent decisions for.

        Returns:
            list of djblets.privacy.consent.base.ConsentRequirement:
            The list of consent requirements pending decisions.
        """
        all_consent = self.get_all_consent(user)

        return [
            consent_requirement
            for consent_requirement in get_consent_requirements_registry()
            if consent_requirement.requirement_id not in all_consent
        ]

    def record_consent_data_list(self, user, consent_data_list):
        """Record a list of all consent data made by a user.

        Args:
            user (django.contrib.auth.models.User):
                The user to record the consent data for.

            consent_data_list (list of
                               djblets.privacy.consent.base.ConsentData):
                A list of consent data to record.
        """
        self.store_recorded_consent_data_list(user, consent_data_list)
        cache.delete(make_cache_key(self._get_user_cache_key(user)))

    def get_all_consent(self, user):
        """Return all consent decisions made by a given user.

        It's important to note that a user may not have made a decision on
        consent for a given registered requirement, in which case the results
        will not include an entry for that requirement.

        Args:
            user (django.contrib.auth.models.User):
                The user to return all consent information for.

        Returns:
            dict:
            A dictionary of
            :py:class:`~djblets.privacy.consent.base.BaseConsentRequirement`
            IDs to :py:class:`~djblets.privacy.consent.base.Consent` values.
        """
        return cache_memoize(self._get_user_cache_key(user),
                             lambda: self.get_all_consent_uncached(user))

    def store_recorded_consent_data_list(self, user, consent_data_list):
        """Record a list of all consent data made by a user.

        Args:
            user (django.contrib.auth.models.User):
                The user to record the consent data for.

            consent_data_list (list of
                               djblets.privacy.consent.base.ConsentData):
                A list of consent data to record.
        """
        raise NotImplementedError

    def get_all_consent_uncached(self, user):
        """Return all consent decisions made by a given user from the backend.

        This is used by :py:meth:`get_all_consent` to return data directly
        from the backend, bypassing the cache.

        Args:
            user (django.contrib.auth.models.User):
                The user to return all consent information for.

        Returns:
            dict:
            A dictionary of
            :py:class:`~djblets.privacy.consent.base.BaseConsentRequirement`
            IDs to :py:class:`~djblets.privacy.consent.base.Consent` values.
        """
        raise NotImplementedError

    def _get_user_cache_key(self, user):
        """Return a consent cache key for the provided user.

        Args:
            user (django.contrib.auth.models.User):
                The user to generate the cache key for.

        Returns:
            unicode:
            The resulting cache key.
        """
        return 'privacy-consent:%s' % user.pk


class DatabaseConsentTracker(BaseConsentTracker):
    """A consent tracker that stores results in the database.

    This consent tracker keeps the current consent information and audit
    history in the database for fast and easy lookup. This is the default
    consent tracker used.
    """

    #: The model used to store consent data in the database.
    model = StoredConsentData

    def store_recorded_consent_data_list(self, user, consent_data_list):
        """Store a recorded list of all consent data made by a user.

        Args:
            user (django.contrib.auth.models.User):
                The user to record the consent data for.

            consent_data_list (list of
                               djblets.privacy.consent.base.ConsentData):
                A list of consent data to record.
        """
        stored_consent = self.model.objects.get_or_create(user=user)[0]

        # Update this in case it has changed since the last recording.
        audit_identifier = self.get_audit_identifier(user)
        stored_consent.audit_identifier = audit_identifier

        # These just cut down on attribute access and verbosity.
        grants = stored_consent.consent_grants
        audit_trail = stored_consent.audit_trail

        for consent_data in consent_data_list:
            requirement_id = consent_data.requirement_id
            audit_info = consent_data.serialize_audit_info(audit_identifier)

            grants[requirement_id] = consent_data.granted
            audit_trail.setdefault(requirement_id, []).insert(0, audit_info)

        stored_consent.save()

        user._djblets_stored_consent = stored_consent

    def get_all_consent_uncached(self, user):
        """Return all consent decisions made by a given user.

        It's important to note that a user may not have made a decision on
        consent for a given registered requirement, in which case the results
        will not include an entry for that requirement.

        Args:
            user (django.contrib.auth.models.User):
                The user to return all consent information for.

        Returns:
            dict:
            A dictionary of
            :py:class:`~djblets.privacy.consent.base.BaseConsentRequirement`
            IDs to :py:class:`~djblets.privacy.consent.base.Consent` values.
        """
        stored_consent = self._get_stored_consent_for_user(user)
        result = {}

        if stored_consent:
            for key, value in six.iteritems(stored_consent.consent_grants):
                if value:
                    result[key] = Consent.GRANTED
                else:
                    result[key] = Consent.DENIED

        return result

    def _get_stored_consent_for_user(self, user):
        """Return stored consent data for a user.

        This will look up the consent data and cache it on the user, speeding
        up subsequent calls.

        Args:
            user (django.contrib.auth.models.User):
                The user to retrieve and cache stored consent data for.

        Returns:
            djblets.privacy.models.StoredConsentData:
            The stored consent data for the user, or ``None`` if there's no
            existing data on record.
        """
        if not hasattr(user, '_djblets_stored_consent'):
            user._djblets_stored_consent = \
                get_object_or_none(self.model, user=user)

        return user._djblets_stored_consent


_consent_tracker = None


def get_consent_tracker():
    """Return the registered consent tracker instance.

    Returns:
        BaseConsentTracker:
        The consent tracker instance.
    """
    global _consent_tracker

    if _consent_tracker is None:
        tracker_class_name = getattr(
            settings,
            'DJBLETS_PRIVACY_CONSENT_TRACKER',
            '%s.%s' % (DatabaseConsentTracker.__module__,
                       DatabaseConsentTracker.__name__))

        module_name, class_name = tracker_class_name.rsplit('.', 1)

        try:
            _consent_tracker = getattr(import_module(module_name),
                                       class_name)()
        except (AttributeError, ImportError):
            raise ImproperlyConfigured(
                'settings.DJBLETS_CONSENT_TRACKER must be set to a valid '
                'class path.')

    return _consent_tracker


def clear_consent_tracker():
    """Clear the registered consent tracker instance.

    This is primarily useful for unit tests. It will remove the consent
    tracker, causing it to be re-instantiated based on settings on the next
    attempt.
    """
    global _consent_tracker

    _consent_tracker = None
