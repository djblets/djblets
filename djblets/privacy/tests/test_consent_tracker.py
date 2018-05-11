"""Unit tests for djblets.privacy.consent.tracker."""

from __future__ import unicode_literals

from datetime import datetime

from django.contrib.auth.models import User
from django.test.utils import override_settings
from django.utils import timezone
from kgb import SpyAgency

from djblets.privacy.consent import (BaseConsentTracker, Consent, ConsentData,
                                     DatabaseConsentTracker,
                                     get_consent_tracker)
from djblets.privacy.consent.tracker import clear_consent_tracker
from djblets.privacy.models import StoredConsentData
from djblets.testing.testcases import TestCase


class CustomConsentTracker(BaseConsentTracker):
    pass


class DatabaseConsentTrackerTests(SpyAgency, TestCase):
    """Unit tests for DatabaseConsentTracker."""

    def setUp(self):
        super(DatabaseConsentTrackerTests, self).setUp()

        self.tracker = DatabaseConsentTracker()
        self.user = User.objects.create(username='test-user',
                                        email='test@example.com')
        self.timestamp = datetime(2018, 1, 2, 13, 14, 15, tzinfo=timezone.utc)

        self.spy_on(timezone.now, call_fake=lambda: self.timestamp)

    def test_record_consent_data(self):
        """Testing DatabaseConsentTracker.record_consent_data"""
        consent_data = ConsentData(
            requirement_id='test-requirement-1',
            granted=True,
            source='http://example.com/account/profile/#consent',
            extra_data={
                'test': True,
            })

        self.tracker.record_consent_data(self.user, consent_data)

        stored_consents = list(StoredConsentData.objects.all())
        self.assertEqual(len(stored_consents), 1)

        stored_consent = stored_consents[0]
        self.assertEqual(stored_consent.user, self.user)
        self.assertEqual(stored_consent.audit_identifier,
                         '973dfe463ec85785f5f95af5ba3906eedb2d931c24e69'
                         '824a89ea65dba4e813b')
        self.assertEqual(stored_consent.time_added, self.timestamp)
        self.assertEqual(stored_consent.last_updated, self.timestamp)
        self.assertEqual(
            stored_consent.consent_grants,
            {
                'test-requirement-1': True,
            })
        self.assertEqual(
            stored_consent.audit_trail,
            {
                'test-requirement-1': [{
                    'identifier': '973dfe463ec85785f5f95af5ba3906eedb2d931c2'
                                  '4e69824a89ea65dba4e813b',
                    'granted': True,
                    'timestamp': '2018-01-02T13:14:15+00:00',
                    'source': 'http://example.com/account/profile/#consent',
                    'extra_data': {
                        'test': True,
                    },
                }],
            })

    def test_record_consent_data_list(self):
        """Testing DatabaseConsentTracker.record_consent_data_list"""
        consent_data_1 = ConsentData(
            requirement_id='test-requirement-1',
            granted=True,
            source='http://example.com/account/profile/#consent',
            extra_data={
                'test': True,
            })

        consent_data_2 = ConsentData(
            requirement_id='test-requirement-2',
            granted=False,
            source='http://example.com/account/profile/#consent')

        self.tracker.record_consent_data_list(self.user,
                                              [consent_data_1, consent_data_2])

        stored_consents = list(StoredConsentData.objects.all())
        self.assertEqual(len(stored_consents), 1)

        stored_consent = stored_consents[0]
        self.assertEqual(stored_consent.user, self.user)
        self.assertEqual(stored_consent.audit_identifier,
                         '973dfe463ec85785f5f95af5ba3906eedb2d931c24e69'
                         '824a89ea65dba4e813b')
        self.assertEqual(stored_consent.time_added, self.timestamp)
        self.assertEqual(stored_consent.last_updated, self.timestamp)
        self.assertEqual(
            stored_consent.consent_grants,
            {
                'test-requirement-1': True,
                'test-requirement-2': False,
            })
        self.assertEqual(
            stored_consent.audit_trail,
            {
                'test-requirement-1': [{
                    'identifier': '973dfe463ec85785f5f95af5ba3906eedb2d931c2'
                                  '4e69824a89ea65dba4e813b',
                    'granted': True,
                    'timestamp': '2018-01-02T13:14:15+00:00',
                    'source': 'http://example.com/account/profile/#consent',
                    'extra_data': {
                        'test': True,
                    },
                }],
                'test-requirement-2': [{
                    'identifier': '973dfe463ec85785f5f95af5ba3906eedb2d931c2'
                                  '4e69824a89ea65dba4e813b',
                    'granted': False,
                    'timestamp': '2018-01-02T13:14:15+00:00',
                    'source': 'http://example.com/account/profile/#consent',
                }],
            })

    def test_get_consent(self):
        """Testing DatabaseConsentTracker.get_consent"""
        # Populate some data we can fetch.
        self.test_record_consent_data_list()

        self.assertEqual(
            self.tracker.get_consent(self.user, 'test-requirement-1'),
            Consent.GRANTED)

        self.assertEqual(
            self.tracker.get_consent(self.user, 'test-requirement-2'),
            Consent.DENIED)

        self.assertEqual(
            self.tracker.get_consent(self.user, 'test-requirement-3'),
            Consent.UNSET)

    def test_get_consent_with_no_user_data(self):
        """Testing DatabaseConsentTracker.get_consent with user without any
        consent data
        """
        self.assertEqual(self.tracker.get_consent(self.user, 'test'),
                         Consent.UNSET)

    def test_get_all_consent(self):
        """Testing DatabaseConsentTracker.get_all_consent"""
        # Populate some data we can fetch.
        self.test_record_consent_data_list()

        self.assertEqual(
            self.tracker.get_all_consent(self.user),
            {
                'test-requirement-1': Consent.GRANTED,
                'test-requirement-2': Consent.DENIED,
            })

    def test_get_all_consent_with_no_user_data(self):
        """Testing DatabaseConsentTracker.get_all_consent with user without any
        consent data
        """
        self.assertEqual(self.tracker.get_all_consent(self.user), {})


class ConsentTrackerInstanceTests(TestCase):
    """Unit tests for consent tracker instance management."""

    def setUp(self):
        super(ConsentTrackerInstanceTests, self).setUp()

        clear_consent_tracker()

    def tearDown(self):
        super(ConsentTrackerInstanceTests, self).tearDown()

        clear_consent_tracker()

    def test_get_consent_tracker_with_default(self):
        """Testing get_consent_tracker with default tracker"""
        self.assertIsInstance(get_consent_tracker(), DatabaseConsentTracker)

    @override_settings(
        DJBLETS_PRIVACY_CONSENT_TRACKER=('%s.CustomConsentTracker'
                                         % __name__))
    def test_get_consent_tracker_with_custom(self):
        """Testing get_consent_tracker with custom tracker"""
        self.assertIsInstance(get_consent_tracker(), CustomConsentTracker)
