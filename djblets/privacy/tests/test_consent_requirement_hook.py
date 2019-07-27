"""Unit tests for djblets.privacy.consent.hooks.ConsentRequirementHook."""

from __future__ import unicode_literals

from djblets.extensions.extension import Extension
from djblets.extensions.tests.base import ExtensionTestsMixin
from djblets.privacy.consent import (BaseConsentRequirement,
                                     get_consent_requirements_registry)
from djblets.privacy.consent.hooks import ConsentRequirementHook
from djblets.testing.testcases import TestCase


class MyExtension(Extension):
    pass


class MyConsentRequirement(BaseConsentRequirement):
    requirement_id = 'my-requirement'
    name = 'My Requirement'
    summary = 'We would like to use this thing'
    intent_description = 'We need this for testing.'
    data_use_description = 'Sending all the things.'


class ConsentRequirementHookTests(ExtensionTestsMixin, TestCase):
    """Unit tests for djblets.privacy.consent.hooks.ConsentRequirementHook."""

    extension_class = MyExtension

    def setUp(self):
        super(ConsentRequirementHookTests, self).setUp()

        self.registry = get_consent_requirements_registry()
        self.extension = self.setup_extension(MyExtension)
        self.consent_requirement = MyConsentRequirement()
        self.consent_requirement_id = self.consent_requirement.requirement_id

    def tearDown(self):
        super(ConsentRequirementHookTests, self).tearDown()

        # The requirement should definitely not be in the registry at this
        # point. Even if we left it there at the end of the test, the parent
        # tearDown() should have shut down the extension, removing the item.
        self.assertNotIn(self.consent_requirement, self.registry)

    def test_registration(self):
        """Testing ConsentRequirementHook registration"""
        self.assertIsNone(self.registry.get_consent_requirement(
            self.consent_requirement_id))

        ConsentRequirementHook(self.extension, self.consent_requirement)
        self.assertEqual(
            self.registry.get_consent_requirement(self.consent_requirement_id),
            self.consent_requirement)

    def test_unregistration(self):
        """Testing ConsentRequirementHook unregistration"""
        self.assertIsNone(self.registry.get_consent_requirement(
            self.consent_requirement_id))

        ConsentRequirementHook(self.extension, self.consent_requirement)
        self.assertEqual(
            self.registry.get_consent_requirement(self.consent_requirement_id),
            self.consent_requirement)

        self.extension.shutdown()
        self.assertIsNone(self.registry.get_consent_requirement(
            self.consent_requirement_id))
