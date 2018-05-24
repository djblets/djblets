"""Unit tests for djblets.privacy.consent.forms.MultiConsentRequirementsField.
"""

from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from djblets.privacy.consent import (BaseConsentRequirement, Consent,
                                     get_consent_tracker)
from djblets.privacy.consent.forms import MultiConsentRequirementsField
from djblets.privacy.tests.testcases import ConsentTestCase


class MyConsentRequirement1(BaseConsentRequirement):
    requirement_id = 'my-requirement-1'
    name = 'My Requirement 1'
    summary = 'We would like to use this thing'
    intent_description = 'We need this for testing.'
    data_use_description = 'Sending all the things.'


class MyConsentRequirement2(BaseConsentRequirement):
    requirement_id = 'my-requirement-2'
    name = 'My Requirement 2'
    summary = 'We would also like this'
    intent_description = 'We need this for dancing.'
    data_use_description = 'Dancing all the things.'


class MultiConsentRequirementsFieldTests(ConsentTestCase):
    """Unit tests for MultiConsentRequirementsField."""

    def setUp(self):
        super(MultiConsentRequirementsFieldTests, self).setUp()

        self.consent_requirement_1 = MyConsentRequirement1()
        self.consent_requirement_2 = MyConsentRequirement2()

        self.field = MultiConsentRequirementsField(
            consent_requirements=[
                self.consent_requirement_1,
                self.consent_requirement_2,
            ],
            consent_source='https://example.com/consent/',
            extra_consent_data={
                'test': True,
            })

        self.user = User.objects.create(username='test-user')

    def test_init_with_user_and_no_existing_consent(self):
        """Testing MultiConsentRequirementsField.__init__ with user and no
        existing consent data
        """
        self.field.set_initial_from_user(self.user)
        self.assertEqual(self.field.initial, [Consent.UNSET, Consent.UNSET])

    def test_init_with_user_and_existing_consent(self):
        """Testing MultiConsentRequirementsField.__init__ with user and
        existing consent data
        """
        tracker = get_consent_tracker()

        tracker.record_consent_data(
            self.user,
            self.consent_requirement_1.build_consent_data(granted=True))
        tracker.record_consent_data(
            self.user,
            self.consent_requirement_2.build_consent_data(granted=False))

        self.field.set_initial_from_user(self.user)
        self.assertEqual(self.field.initial, [Consent.GRANTED, Consent.DENIED])

    def test_set_initial_from_user(self):
        """Testing MultiConsentRequirementsField.set_initial_from_user"""
        get_consent_tracker().record_consent_data(
            self.user,
            self.consent_requirement_2.build_consent_data(granted=True))

        self.field.set_initial_from_user(self.user)
        self.assertEqual(self.field.initial, [Consent.UNSET, Consent.GRANTED])

    def test_prepare_value(self):
        """Testing MultiConsentRequirementsField.prepare_value"""
        self.assertEqual(
            self.field.prepare_value([Consent.GRANTED, Consent.UNSET]),
            ['allow', None])

    def test_clean_with_valid_values(self):
        """Testing MultiConsentRequirementsField.clean with valid values"""
        values = self.field.clean(['allow', 'block'])

        self.assertIsNotNone(values)
        self.assertEqual(len(values), 2)

        consent_data = values[0]
        self.assertEqual(consent_data.requirement_id, 'my-requirement-1')
        self.assertEqual(consent_data.source, 'https://example.com/consent/')
        self.assertTrue(consent_data.granted)
        self.assertEqual(
            consent_data.extra_data,
            {
                'test': True,
            })

        consent_data = values[1]
        self.assertEqual(consent_data.requirement_id, 'my-requirement-2')
        self.assertEqual(consent_data.source, 'https://example.com/consent/')
        self.assertFalse(consent_data.granted)
        self.assertEqual(
            consent_data.extra_data,
            {
                'test': True,
            })

        # Make sure the timestamps are identical.
        self.assertEqual(values[0].timestamp, values[1].timestamp)

    def test_clean_with_unset(self):
        """Testing MultiConsentRequirementsField.clean with unset"""
        message = 'You must choose Allow or Block for all options to continue.'

        with self.assertRaisesMessage(ValidationError, message):
            self.field.clean(['allow', None])
