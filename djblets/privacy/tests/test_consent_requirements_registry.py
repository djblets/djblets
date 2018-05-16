"""Unit tests for djblets.privacy.consent.registry."""

from __future__ import unicode_literals

from djblets.privacy.consent import BaseConsentRequirement
from djblets.privacy.consent.errors import ConsentRequirementConflictError
from djblets.privacy.consent.registry import ConsentRequirementsRegistry
from djblets.privacy.tests.testcases import ConsentTestCase


class MyConsentRequirement(BaseConsentRequirement):
    requirement_id = 'test-requirement'
    name = 'Test Requirement'
    summary = 'We want this.'
    intent_description = 'Test.'
    data_use_description = 'All.'


class ConsentRequirementsRegistryTests(ConsentTestCase):
    """Unit tests for ConsentRequirementsRegistry."""

    def setUp(self):
        super(ConsentRequirementsRegistryTests, self).setUp()

        self.registry = ConsentRequirementsRegistry()

    def test_register(self):
        """Testing ConsentRequirementsRegistry.register"""
        requirement = MyConsentRequirement()
        self.registry.register(requirement)

        self.assertEqual(list(self.registry), [requirement])

    def test_register_with_conflict(self):
        """Testing ConsentRequirementsRegistry.register with conflicting ID"""
        requirement = MyConsentRequirement()
        self.registry.register(requirement)

        with self.assertRaises(ConsentRequirementConflictError):
            self.registry.register(requirement)

    def test_get_consent_requirement(self):
        """Testing ConsentRequirementsRegistry.get_consent_requirement"""
        requirement = MyConsentRequirement()
        self.registry.register(requirement)

        self.assertEqual(
            self.registry.get_consent_requirement('test-requirement'),
            requirement)

    def test_get_consent_requirement_with_invalid_id(self):
        """Testing ConsentRequirementsRegistry.get_consent_requirement with
        invalid ID
        """
        self.assertIsNone(
            self.registry.get_consent_requirement('test-requirement'))
