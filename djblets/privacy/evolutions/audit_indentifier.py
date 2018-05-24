"""Evolution to remove unique constraint from StoredConsentData."""

from __future__ import unicode_literals

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('StoredConsentData', 'audit_identifier', initial=None,
                unique=False),
]
