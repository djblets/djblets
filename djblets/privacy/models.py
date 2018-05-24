"""Database models for privacy-related data storage."""

from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from djblets.db.fields import JSONField


@python_2_unicode_compatible
class StoredConsentData(models.Model):
    """Stored information about a user's current and past consent decisions.

    This tracks what parts of a product a user has consented to, and how those
    decisions have changed in the past. The model is not meant to be queried
    directly by applications, but rather used behind the scenes by
    :py:class:`~djblets.privacy.consent.tracker.DatabaseConsentTracker`.

    Entries are associated with a user in the database (when available), but
    are also associated with a piece of identifying data for the purposes of
    privacy auditing. The identifying data (stored in
    :py:attr:`audit_identifier`) can be erased at any point without impacting
    the model, and can also store encrypted values if needed by the
    application.
    """

    user = models.OneToOneField(
        User,
        null=True,
        on_delete=models.SET_NULL,
        help_text=_('The user whose consent decisions are being stored.'))

    audit_identifier = models.CharField(
        max_length=255,
        db_index=True,
        blank=True,
        null=True,
        help_text=_('An identifier for locating the audit record as needed. '
                    'The value must be able to be compared against '
                    'information from the original user, but may be erased '
                    'or encrypted at any point.'))

    time_added = models.DateTimeField(
        auto_now_add=True,
        help_text=_('The date and time when the stored consent data was first '
                    'added to the database.'))

    last_updated = models.DateTimeField(
        auto_now=True,
        help_text=_('The date and time when the stored consent data was last '
                    'updated.'))

    #: The current consent grant state of each consent-tracking item.
    #:
    #: This is in the form of::
    #:
    #:     {
    #:         "<consent_requirement_id>": bool,
    #:         ...
    #:     }
    #:
    #: Each boolean indicates if consent is granted or denied.
    consent_grants = JSONField(
        default=dict,
        help_text=_('The consents granted or denied by the user.'))

    #: An audit trail of each consent-tracking decision.
    #:
    #: This is in the form of::
    #:
    #:     {
    #:         "<consent_requirement_id>": [
    #:             {
    #:                 "identifier": string,
    #:                 "granted": bool,
    #:                 "timestamp": UTC datetime,
    #:                 "source": string,
    #:                 "memo": string,
    #:             },
    #:             ...
    #:         ],
    #:         ...
    #:     }
    audit_trail = JSONField(
        default=dict,
        help_text=_('A record of all consent changes made by the user.'))

    def __str__(self):
        """Return a string representation of the object.

        Returns:
            unicode:
            The string representation of the object.
        """
        return 'Stored support data for %s' % (self.user or
                                               self.audit_identifier)

    class Meta:
        # Ensure we're using the same name across all versions of Django.
        db_table = 'djblets_privacy_storedconsentdata'

        ordering = ('-last_updated',)

        verbose_name = _('Stored consent data')
        verbose_name_plural = _('Stored consent data')
