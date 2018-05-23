"""Unit tests for djblets.privacy.consent.base.ConsentData."""

from __future__ import unicode_literals

from datetime import datetime

from django.utils import timezone

from djblets.privacy.consent import ConsentData
from djblets.privacy.tests.testcases import ConsentTestCase


class ConsentDataTests(ConsentTestCase):
    """Unit tests for djblets.privacy.consent.base.ConsentData."""

    def test_parse_audit_info_with_all_data(self):
        """Testing ConsentData.parse_audit_info with all data"""
        consent_data = ConsentData.parse_audit_info('test-requirement', {
            'granted': True,
            'timestamp': '2018-01-02T13:14:15+00:00',
            'source': 'http://example.com/account/profile/#consent',
            'extra_data': {
                'test': True,
            },
        })

        self.assertEqual(consent_data.requirement_id, 'test-requirement')
        self.assertTrue(consent_data.granted)
        self.assertEqual(consent_data.timestamp,
                         datetime(2018, 1, 2, 13, 14, 15, tzinfo=timezone.utc))
        self.assertEqual(consent_data.source,
                         'http://example.com/account/profile/#consent')
        self.assertEqual(
            consent_data.extra_data,
            {
                'test': True,
            })

    def test_parse_audit_info_with_minimum_data(self):
        """Testing ConsentData.parse_audit_info with minimum required data"""
        consent_data = ConsentData.parse_audit_info('test-requirement', {
            'granted': False,
            'timestamp': '2018-01-02T13:14:15+00:00',
        })

        self.assertEqual(consent_data.requirement_id, 'test-requirement')
        self.assertFalse(consent_data.granted)
        self.assertEqual(consent_data.timestamp,
                         datetime(2018, 1, 2, 13, 14, 15, tzinfo=timezone.utc))
        self.assertIsNone(consent_data.source)
        self.assertIsNone(consent_data.extra_data)

    def test_serialize_audit_info_with_all_data(self):
        """Testing ConsentData.serialize_audit_info with all data"""
        consent_data = ConsentData(
            requirement_id='test-requirement',
            granted=True,
            timestamp=datetime(2018, 1, 2, 13, 14, 15, tzinfo=timezone.utc),
            source='http://example.com/account/profile/#consent',
            extra_data={
                'test': True,
            })

        self.assertEqual(
            consent_data.serialize_audit_info('123:test@example.com'),
            {
                'identifier': '123:test@example.com',
                'granted': True,
                'timestamp': '2018-01-02T13:14:15+00:00',
                'source': 'http://example.com/account/profile/#consent',
                'extra_data': {
                    'test': True,
                },
            })

    def test_serialize_audit_info_with_minimum_data(self):
        """Testing ConsentData.serialize_audit_info with minimum required data
        """
        consent_data = ConsentData(
            requirement_id='test-requirement',
            granted=False,
            timestamp=datetime(2018, 1, 2, 13, 14, 15, tzinfo=timezone.utc))

        self.assertEqual(
            consent_data.serialize_audit_info('123:test@example.com'),
            {
                'identifier': '123:test@example.com',
                'granted': False,
                'timestamp': '2018-01-02T13:14:15+00:00',
            })
