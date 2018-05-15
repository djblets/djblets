"""Unit tests for djblets.privacy.consent.base.ConsentRequirement."""

from __future__ import unicode_literals

from datetime import datetime

from django.contrib.auth.models import User
from django.utils import timezone

from djblets.privacy.consent import (Consent, ConsentData, ConsentRequirement,
                                     get_consent_tracker)
from djblets.privacy.tests.testcases import ConsentTestCase


class ConsentRequirementTests(ConsentTestCase):
    """Unit tests for djblets.privacy.consent.base.ConsentRequirement."""

    def test_build_consent_data(self):
        """Testing ConsentRequirement.build_consent_data"""
        requirement = ConsentRequirement(
            requirement_id='my-requirement',
            name='My Requirement',
            summary='We would like to use this thing',
            intent_description='We need this for testing.',
            data_use_description='Sending all the things.')

        timestamp = datetime(2018, 1, 2, 13, 14, 15, tzinfo=timezone.utc)

        consent_data = requirement.build_consent_data(
            granted=False,
            timestamp=timestamp,
            source='http://example.com/account/profile/#consent',
            extra_data={
                'test': True,
            })

        self.assertEqual(consent_data.requirement_id, 'my-requirement')
        self.assertFalse(consent_data.granted)
        self.assertEqual(consent_data.timestamp, timestamp)
        self.assertEqual(consent_data.source,
                         'http://example.com/account/profile/#consent')
        self.assertEqual(
            consent_data.extra_data,
            {
                'test': True,
            })

    def test_get_consent(self):
        """Testing ConsentRequirement.get_consent"""
        requirement = ConsentRequirement(
            requirement_id='my-requirement',
            name='My Requirement',
            summary='We would like to use this thing',
            intent_description='We need this for testing.',
            data_use_description='Sending all the things.')

        timestamp = datetime(2018, 1, 2, 13, 14, 15, tzinfo=timezone.utc)
        user = User.objects.create(username='test-user')

        consent_data = ConsentData(
            requirement_id='my-requirement',
            granted=True,
            timestamp=timestamp,
            source='http://example.com/account/profile/#consent',
            extra_data={
                'test': True,
            })

        get_consent_tracker().record_consent_data(user, consent_data)

        self.assertEqual(requirement.get_consent(user), Consent.GRANTED)
