"""Base testcases for integrations unit tests."""

from __future__ import annotations

from typing import List

from django.conf import settings
from django.core.cache import cache

from djblets.integrations.manager import shutdown_integration_managers
from djblets.testing.testcases import TestCase, TestModelsLoaderMixin


class IntegrationsTestCase(TestModelsLoaderMixin, TestCase):
    """Base class for unit tests that work with integrations."""

    tests_app = 'djblets.integrations.tests'

    old_middleware_classes: List[str]

    def setUp(self) -> None:
        super().setUp()

        self.old_middleware_classes = list(settings.MIDDLEWARE)
        settings.MIDDLEWARE = self.old_middleware_classes + [
            'djblets.integrations.middleware.IntegrationsMiddleware',
        ]

        cache.clear()

    def tearDown(self) -> None:
        settings.MIDDLEWARE = self.old_middleware_classes

        shutdown_integration_managers()

        super().tearDown()
