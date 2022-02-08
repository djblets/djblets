"""Unit tests for extension middleware."""

import kgb
from django.test import override_settings

from djblets.extensions.extension import Extension
from djblets.extensions.testing import ExtensionTestCaseMixin
from djblets.testing.testcases import TestCase


MIDDLEWARE = [
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'djblets.extensions.middleware.ExtensionsMiddleware',
    'djblets.extensions.middleware.ExtensionsMiddlewareRunner',
]


class Middleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)


class MyTestExtension(Extension):
    middleware = [
        'djblets.extensions.tests.test_middleware.Middleware',
    ]


class MiddlewareTests(kgb.SpyAgency, ExtensionTestCaseMixin, TestCase):
    """Unit tests for extension middleware."""

    @override_settings(MIDDLEWARE=MIDDLEWARE)
    def test_extension_middleware(self):
        """Testing extension middleware"""
        self.spy_on(Middleware.__call__, owner=Middleware)
        self.setup_extension(MyTestExtension)
        self.client.get('/')
        self.assertSpyCalled(Middleware.__call__)
