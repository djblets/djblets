"""Unit tests for djblets.privacy.consent.forms.ConsentConfigPageFormMixin."""

from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.test.client import RequestFactory

from djblets.configforms.forms import ConfigPageForm
from djblets.configforms.pages import ConfigPage
from djblets.configforms.views import ConfigPagesView
from djblets.privacy.consent import (BaseConsentRequirement, Consent,
                                     get_consent_tracker,
                                     get_consent_requirements_registry)
from djblets.privacy.consent.forms import ConsentConfigPageFormMixin
from djblets.privacy.tests.testcases import ConsentTestCase


class MyForm(ConsentConfigPageFormMixin, ConfigPageForm):
    def get_extra_consent_data(self):
        return {
            'test': True,
        }


class MyPage(ConfigPage):
    form_classes = [MyForm]


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


class ConsentConfigPageFormMixinTests(ConsentTestCase):
    """Unit tests for ConsentConfigPageFormMixinTests."""

    def setUp(self):
        super(ConsentConfigPageFormMixinTests, self).setUp()

        self.registry = get_consent_requirements_registry()

        self.consent_requirement_1 = MyConsentRequirement1()
        self.registry.register(self.consent_requirement_1)

        self.consent_requirement_2 = MyConsentRequirement2()
        self.registry.register(self.consent_requirement_2)

        self.user = User.objects.create(username='test-user')

        self.request = RequestFactory().get('/consent/')
        self.request.user = self.user

        # Enable support for messages.
        SessionMiddleware().process_request(self.request)
        MessageMiddleware().process_request(self.request)

        self.page = MyPage(config_view=ConfigPagesView(),
                           request=self.request,
                           user=self.user)

    def test_init(self):
        """Testing ConsentConfigPageFormMixin.__init__ defines field"""
        get_consent_tracker().record_consent_data(
            self.user,
            self.consent_requirement_2.build_consent_data(granted=False))

        form = MyForm(page=self.page,
                      request=self.request,
                      user=self.user)
        self.assertIn('consent', form.fields)

        field = form.fields['consent']
        self.assertEqual(field.initial, [Consent.UNSET, Consent.DENIED])
        self.assertEqual(
            field.consent_requirements,
            [self.consent_requirement_1, self.consent_requirement_2])

        for subfield in field.fields:
            self.assertEqual(subfield.consent_source,
                             'http://testserver/consent/')
            self.assertEqual(
                subfield.extra_consent_data,
                {
                    'test': True,
                })

    def test_save(self):
        """Testing ConsentConfigPageFormMixin.save"""
        form = MyForm(
            page=self.page,
            request=self.request,
            user=self.user,
            data={
                'consent_my-requirement-1_choice': 'allow',
                'consent_my-requirement-2_choice': 'block',
            })
        self.assertTrue(form.is_valid())

        self.assertEqual(self.consent_requirement_1.get_consent(self.user),
                         Consent.UNSET)
        self.assertEqual(self.consent_requirement_2.get_consent(self.user),
                         Consent.UNSET)

        form.save()

        self.assertEqual(self.consent_requirement_1.get_consent(self.user),
                         Consent.GRANTED)
        self.assertEqual(self.consent_requirement_2.get_consent(self.user),
                         Consent.DENIED)

        # Check that the success message appeared.
        messages = list(get_messages(self.request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].message,
                         'Your choices have been saved. You can make '
                         'changes to these at any time.')
