"""Support for tracking and looking up user consent for privacy rights.

This provides convenience imports for the following:

.. autosummary::
   :nosignatures:

   ~djblets.privacy.consent.base.BaseConsentRequirement
   ~djblets.privacy.consent.base.Consent
   ~djblets.privacy.consent.base.ConsentData
   ~djblets.privacy.consent.registry.get_consent_requirements_registry
   ~djblets.privacy.consent.tracker.BaseConsentTracker
   ~djblets.privacy.consent.tracker.DatabaseConsentTracker
   ~djblets.privacy.consent.tracker.get_consent_tracker
"""

from __future__ import unicode_literals

from djblets.privacy.consent.base import (BaseConsentRequirement, Consent,
                                          ConsentData)
from djblets.privacy.consent.registry import get_consent_requirements_registry
from djblets.privacy.consent.tracker import (BaseConsentTracker,
                                             DatabaseConsentTracker,
                                             get_consent_tracker)


__all__ = (
    'BaseConsentRequirement',
    'BaseConsentTracker',
    'Consent',
    'ConsentData',
    'DatabaseConsentTracker',
    'get_consent_requirements_registry',
    'get_consent_tracker',
)

__autodoc_excludes__ = __all__
