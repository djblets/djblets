"""Unit tests for djblets.privacy.consent.forms.ConsentRequirementField."""

from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from djblets.privacy.consent import (BaseConsentRequirement, Consent,
                                     get_consent_tracker)
from djblets.privacy.consent.forms import ConsentRequirementField
from djblets.privacy.tests.testcases import ConsentTestCase


class MyConsentRequirement(BaseConsentRequirement):
    requirement_id = 'my-requirement'
    name = 'My Requirement'
    summary = 'We would like to use this thing'
    intent_description = 'We need this for testing.'
    data_use_description = 'Sending all the things.'
    icons = {
        '1x': '/static/consent.png',
        '2x': '/static/consent@2x.png',
    }


class ConsentRequirementFieldTests(ConsentTestCase):
    """Unit tests for ConsentRequirementField."""

    def setUp(self):
        super(ConsentRequirementFieldTests, self).setUp()

        self.consent_requirement = MyConsentRequirement()

        self.field = ConsentRequirementField(
            consent_requirement=self.consent_requirement,
            consent_source='https://example.com/consent/',
            extra_consent_data={
                'test': True,
            })

        self.user = User.objects.create(username='test-user')

    def test_init_with_user_and_no_existing_consent(self):
        """Testing ConsentRequirementField.__init__ with user and no existing
        consent data
        """
        self.field.set_initial_from_user(self.user)
        self.assertEqual(self.field.initial, Consent.UNSET)

    def test_init_with_user_and_existing_consent(self):
        """Testing ConsentRequirementField.__init__ with user and existing
        consent data
        """
        get_consent_tracker().record_consent_data(
            self.user,
            self.consent_requirement.build_consent_data(granted=True))

        self.field.set_initial_from_user(self.user)
        self.assertEqual(self.field.initial, Consent.GRANTED)

    def test_set_initial_from_user(self):
        """Testing ConsentRequirementField.set_initial_from_user"""
        get_consent_tracker().record_consent_data(
            self.user,
            self.consent_requirement.build_consent_data(granted=False))

        self.field.set_initial_from_user(self.user)
        self.assertEqual(self.field.initial, Consent.DENIED)

    def test_prepare_value(self):
        """Testing ConsentRequirementField.prepare_value"""
        self.assertEqual(self.field.prepare_value(Consent.GRANTED), 'allow')
        self.assertEqual(self.field.prepare_value(Consent.DENIED), 'block')
        self.assertIsNone(self.field.prepare_value(Consent.UNSET))

    def test_clean_with_allow(self):
        """Testing ConsentRequirementField.clean with allow"""
        consent_data = self.field.clean('allow')

        self.assertIsNotNone(consent_data)
        self.assertEqual(consent_data.requirement_id, 'my-requirement')
        self.assertEqual(consent_data.source, 'https://example.com/consent/')
        self.assertTrue(consent_data.granted)
        self.assertEqual(
            consent_data.extra_data,
            {
                'test': True,
            })

    def test_clean_with_block(self):
        """Testing ConsentRequirementField.clean with block"""
        consent_data = self.field.clean('block')

        self.assertIsNotNone(consent_data)
        self.assertEqual(consent_data.requirement_id, 'my-requirement')
        self.assertEqual(consent_data.source, 'https://example.com/consent/')
        self.assertFalse(consent_data.granted)
        self.assertEqual(
            consent_data.extra_data,
            {
                'test': True,
            })

    def test_clean_with_unset(self):
        """Testing ConsentRequirementField.clean with unset"""
        message = 'You must choose Allow or Block to continue.'

        with self.assertRaisesMessage(ValidationError, message):
            self.field.clean(None)
