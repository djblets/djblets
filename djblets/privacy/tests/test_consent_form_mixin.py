"""Unit tests for djblets.privacy.consent.forms.ConsentFormMixin."""

from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.forms import Form

from djblets.privacy.consent import (BaseConsentRequirement, Consent,
                                     get_consent_requirements_registry)
from djblets.privacy.consent.forms import ConsentFormMixin
from djblets.privacy.tests.testcases import ConsentTestCase


class MyForm(ConsentFormMixin, Form):
    def __init__(self, user=None, *args, **kwargs):
        self.user = user

        super(MyForm, self).__init__(*args, **kwargs)

    def get_consent_user(self):
        return self.user

    def get_consent_source(self):
        return 'https://example.com/consent/'

    def get_extra_consent_data(self):
        return {
            'test': True,
        }


class MyConsentRequirement1(BaseConsentRequirement):
    requirement_id = 'my-requirement-1'
    name = 'My Requirement 1'
    summary = 'We would like to use this thing'
    intent_description = 'We need this for testing.'
    data_use_description = 'Sending all the things.'
    icons = {
        '1x': '/static/consent.png',
        '2x': '/static/consent@2x.png',
    }


class MyConsentRequirement2(BaseConsentRequirement):
    requirement_id = 'my-requirement-2'
    name = 'My Requirement 2'
    summary = 'We would also like this'
    intent_description = 'We need this for dancing.'
    data_use_description = 'Dancing all the things.'


class ConsentFormMixinTests(ConsentTestCase):
    """Unit tests for ConsentFormMixinTests."""

    def setUp(self):
        super(ConsentFormMixinTests, self).setUp()

        self.registry = get_consent_requirements_registry()

        self.consent_requirement_1 = MyConsentRequirement1()
        self.registry.register(self.consent_requirement_1)

        self.consent_requirement_2 = MyConsentRequirement2()
        self.registry.register(self.consent_requirement_2)

        self.user = User.objects.create(username='test-user')

    def test_init(self):
        """Testing ConsentFormMixin.__init__ defines field"""
        form = MyForm()
        self.assertIn('consent', form.fields)

        field = form.fields['consent']
        self.assertEqual(
            field.consent_requirements,
            [self.consent_requirement_1, self.consent_requirement_2])

        for subfield in field.fields:
            self.assertEqual(subfield.consent_source,
                             'https://example.com/consent/')
            self.assertEqual(
                subfield.extra_consent_data,
                {
                    'test': True,
                })

    def test_save_consent(self):
        """Testing ConsentFormMixin.save_consent"""
        form = MyForm(data={
            'consent_my-requirement-1_choice': 'allow',
            'consent_my-requirement-2_choice': 'block',
        })
        self.assertTrue(form.is_valid())

        self.assertEqual(self.consent_requirement_1.get_consent(self.user),
                         Consent.UNSET)
        self.assertEqual(self.consent_requirement_2.get_consent(self.user),
                         Consent.UNSET)

        form.save_consent(self.user)

        self.assertEqual(self.consent_requirement_1.get_consent(self.user),
                         Consent.GRANTED)
        self.assertEqual(self.consent_requirement_2.get_consent(self.user),
                         Consent.DENIED)
