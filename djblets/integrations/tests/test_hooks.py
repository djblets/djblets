from __future__ import annotations

from typing import Set

from djblets.extensions.hooks import ExtensionHookPoint
from djblets.integrations.hooks import BaseIntegrationHook
from djblets.integrations.integration import Integration
from djblets.integrations.manager import IntegrationManager
from djblets.integrations.tests.models import IntegrationConfig
from djblets.integrations.tests.testcases import IntegrationsTestCase


class DummyIntegrationHook(BaseIntegrationHook, metaclass=ExtensionHookPoint):
    def __init__(self, manager, *args, **kwargs):
        self.manager = manager

        super().__init__(*args, **kwargs)

    def get_integration_manager(self):
        return self.manager


class DummyIntegration(Integration):
    def initialize(self):
        pass


class IntegrationHookTests(IntegrationsTestCase):
    """Unit tests for djblets.integrations.hooks.BaseIntegrationHook."""

    def setUp(self) -> None:
        super().setUp()

        self.manager = IntegrationManager(IntegrationConfig)

        # This will make this class a hook owner.
        self.hooks: Set[DummyIntegrationHook] = set()

        self.hook = DummyIntegrationHook(self.manager, self, DummyIntegration)

    def test_initialize(self) -> None:
        """Testing BaseIntegrationHook.initialize"""
        self.assertIn(DummyIntegration.integration_id,
                      self.manager._integration_classes)

    def test_shutdown(self) -> None:
        """Testing BaseIntegrationHook.initialize"""
        self.hook.disable_hook()

        self.assertNotIn(DummyIntegration.integration_id,
                         self.manager._integration_classes)
