"""Unit tests for djblets.privacy.consent.forms.MultiConsentRequirementsWidget.
"""

from __future__ import unicode_literals

from djblets.privacy.consent import BaseConsentRequirement
from djblets.privacy.consent.forms import MultiConsentRequirementsWidget
from djblets.testing.testcases import TestCase


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


class MultiConsentRequirementsWidgetTests(TestCase):
    """Unit tests for MultiConsentRequirementsWidget."""

    def setUp(self):
        super(MultiConsentRequirementsWidgetTests, self).setUp()

        self.widget = MultiConsentRequirementsWidget(consent_requirements=[
            MyConsentRequirement1(),
            MyConsentRequirement2(),
        ])

    def test_render(self):
        """Testing MultiConsentRequirementsWidget.render with value=[]"""
        html = self.widget.render(
            name='consent',
            value=[],
            attrs={
                'id': 'my_consent',
            })

        # Check for the first sub-widget.
        self.assertIn('<div id="my_consent_my-requirement-1"'
                      ' class="privacy-consent-field'
                      ' privacy-consent-field-has-icon">',
                      html)
        self.assertIn("<h2>We would like to use this thing</h2>", html)
        self.assertIn('<p>We need this for testing.</p>', html)
        self.assertIn('<p>Sending all the things.</p>', html)
        self.assertInHTML('<input type="radio"'
                          ' id="my_consent_my-requirement-1_choice_allow"'
                          ' name="consent_my-requirement-1_choice"'
                          ' value="allow">',
                          html)
        self.assertInHTML('<input type="radio"'
                          ' id="my_consent_my-requirement-1_choice_block"'
                          ' name="consent_my-requirement-1_choice"'
                          ' value="block">',
                          html)

        # Check for the second sub-widget.
        self.assertIn('<div id="my_consent_my-requirement-2"'
                      ' class="privacy-consent-field">',
                      html)
        self.assertIn("<h2>We would also like this</h2>", html)
        self.assertIn('<p>We need this for dancing.</p>', html)
        self.assertIn('<p>Dancing all the things.</p>', html)
        self.assertInHTML('<input type="radio"'
                          ' id="my_consent_my-requirement-2_choice_allow"'
                          ' name="consent_my-requirement-2_choice"'
                          ' value="allow">',
                          html)
        self.assertInHTML('<input type="radio"'
                          ' id="my_consent_my-requirement-2_choice_block"'
                          ' name="consent_my-requirement-2_choice"'
                          ' value="block">',
                          html)

    def test_render_with_values(self):
        """Testing MultiConsentRequirementsWidget.render with values"""
        html = self.widget.render(
            name='consent',
            value=['allow', 'block'],
            attrs={
                'id': 'my_consent',
            })

        # Check for the first sub-widget.
        self.assertIn('<div id="my_consent_my-requirement-1"'
                      ' class="privacy-consent-field'
                      ' privacy-consent-field-has-icon">',
                      html)
        self.assertIn("<h2>We would like to use this thing</h2>", html)
        self.assertIn('<p>We need this for testing.</p>', html)
        self.assertIn('<p>Sending all the things.</p>', html)
        self.assertInHTML('<input type="radio"'
                          ' id="my_consent_my-requirement-1_choice_allow"'
                          ' name="consent_my-requirement-1_choice"'
                          ' value="allow" checked>',
                          html)
        self.assertInHTML('<input type="radio"'
                          ' id="my_consent_my-requirement-1_choice_block"'
                          ' name="consent_my-requirement-1_choice"'
                          ' value="block">',
                          html)

        # Check for the second sub-widget.
        self.assertIn('<div id="my_consent_my-requirement-2"'
                      ' class="privacy-consent-field">',
                      html)
        self.assertIn("<h2>We would also like this</h2>", html)
        self.assertIn('<p>We need this for dancing.</p>', html)
        self.assertIn('<p>Dancing all the things.</p>', html)
        self.assertInHTML('<input type="radio"'
                          ' id="my_consent_my-requirement-2_choice_allow"'
                          ' name="consent_my-requirement-2_choice"'
                          ' value="allow">',
                          html)
        self.assertInHTML('<input type="radio"'
                          ' id="my_consent_my-requirement-2_choice_block"'
                          ' name="consent_my-requirement-2_choice"'
                          ' value="block" checked>',
                          html)

    def test_value_from_datadict_with_value(self):
        """Testing MultiConsentRequirementsWidget.value_from_datadict with
        values
        """
        data = {
            'consent_my-requirement-1_choice': 'allow',
            'consent_my-requirement-2_choice': 'block',
        }

        self.assertEqual(
            self.widget.value_from_datadict(data=data,
                                            files={},
                                            name='consent'),
            ['allow', 'block'])

    def test_value_from_datadict_without_values(self):
        """Testing MultiConsentRequirementsWidget.value_from_datadict without
        values
        """
        self.assertEqual(
            self.widget.value_from_datadict(data={}, files={}, name='consent'),
            [None, None])
