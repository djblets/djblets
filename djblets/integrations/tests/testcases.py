from __future__ import unicode_literals

from django.conf import settings
from django.core.cache import cache

from djblets.integrations.manager import shutdown_integration_managers
from djblets.testing.testcases import TestCase, TestModelsLoaderMixin


class IntegrationsTestCase(TestModelsLoaderMixin, TestCase):
    """Base class for unit tests that work with integrations."""

    tests_app = 'djblets.integrations.tests'

    def setUp(self):
        super(IntegrationsTestCase, self).setUp()

        self.old_middleware_classes = list(settings.MIDDLEWARE_CLASSES)
        settings.MIDDLEWARE_CLASSES = self.old_middleware_classes + [
            'djblets.integrations.middleware.IntegrationsMiddleware',
        ]

        cache.clear()

    def tearDown(self):
        super(IntegrationsTestCase, self).tearDown()

        settings.MIDDLEWARE_CLASSES = self.old_middleware_classes

        shutdown_integration_managers()
