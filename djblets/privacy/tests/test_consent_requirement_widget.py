"""Unit tests for djblets.privacy.consent.forms.ConsentRequirementWidget."""

from __future__ import unicode_literals

from djblets.privacy.consent import BaseConsentRequirement
from djblets.privacy.consent.forms import ConsentRequirementWidget
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


class ConsentRequirementWidgetTests(ConsentTestCase):
    """Unit tests for ConsentRequirementWidget."""

    def setUp(self):
        super(ConsentRequirementWidgetTests, self).setUp()

        self.widget = ConsentRequirementWidget(
            consent_requirement=MyConsentRequirement())

    def test_render(self):
        """Testing ConsentRequirementWidget.render with value=None"""
        html = self.widget.render(
            name='consent',
            value=None,
            attrs={
                'id': 'my_consent',
            })

        self.assertIn('<div id="my_consent" class="privacy-consent-field'
                      ' privacy-consent-field-has-icon">',
                      html)
        self.assertIn("<h2>We would like to use this thing</h2>", html)
        self.assertIn('<p>We need this for testing.</p>', html)
        self.assertIn('<p>Sending all the things.</p>', html)
        self.assertInHTML('<input type="radio" id="my_consent_choice_allow"'
                          ' name="consent_choice" value="allow">',
                          html)
        self.assertInHTML('<input type="radio" id="my_consent_choice_block"'
                          ' name="consent_choice" value="block">',
                          html)

    def test_render_with_value_allow(self):
        """Testing ConsentRequirementWidget.render with value=allow"""
        html = self.widget.render(
            name='consent',
            value='allow',
            attrs={
                'id': 'my_consent',
            })

        self.assertIn('<div id="my_consent" class="privacy-consent-field'
                      ' privacy-consent-field-has-icon">',
                      html)
        self.assertIn("<h2>We would like to use this thing</h2>", html)
        self.assertIn('<p>We need this for testing.</p>', html)
        self.assertIn('<p>Sending all the things.</p>', html)
        self.assertInHTML('<input type="radio" id="my_consent_choice_allow"'
                          ' name="consent_choice" value="allow" checked>',
                          html)
        self.assertInHTML('<input type="radio" id="my_consent_choice_block"'
                          ' name="consent_choice" value="block">',
                          html)

    def test_render_with_value_block(self):
        """Testing ConsentRequirementWidget.render with value=block"""
        html = self.widget.render(
            name='consent',
            value='block',
            attrs={
                'id': 'my_consent',
            })

        self.assertIn('<div id="my_consent" class="privacy-consent-field'
                      ' privacy-consent-field-has-icon">',
                      html)
        self.assertIn("<h2>We would like to use this thing</h2>", html)
        self.assertIn('<p>We need this for testing.</p>', html)
        self.assertIn('<p>Sending all the things.</p>', html)
        self.assertInHTML('<input type="radio" id="my_consent_choice_allow"'
                          ' name="consent_choice" value="allow">',
                          html)
        self.assertInHTML('<input type="radio" id="my_consent_choice_block"'
                          ' name="consent_choice" value="block" checked>',
                          html)

    def test_value_from_datadict_with_value(self):
        """Testing ConsentRequirementWidget.value_from_datadict with value"""
        data = {
            'consent_choice': 'allow',
        }

        self.assertEqual(
            self.widget.value_from_datadict(data=data,
                                            files={},
                                            name='consent'),
            'allow')

    def test_value_from_datadict_with_none(self):
        """Testing ConsentRequirementWidget.value_from_datadict without value
        """
        self.assertIsNone(
            self.widget.value_from_datadict(data={}, files={}, name='consent'))
