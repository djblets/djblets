"""Base test case for privacy consent tests."""

from __future__ import unicode_literals

from django.core.cache import cache

from djblets.privacy.consent import get_consent_requirements_registry
from djblets.privacy.consent.tracker import clear_consent_tracker
from djblets.testing.testcases import TestCase


class ConsentTestCase(TestCase):
    """Base test case for consent-related unit tests."""

    def setUp(self):
        super(ConsentTestCase, self).setUp()

        self.clear_consent_caches()

    def tearDown(self):
        super(ConsentTestCase, self).tearDown()

        self.clear_consent_caches()

    def clear_consent_caches(self):
        """Clear all consent-related caches."""
        cache.clear()
        get_consent_requirements_registry().reset()
        clear_consent_tracker()
