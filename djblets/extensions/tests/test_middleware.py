"""Unit tests for extension middleware."""

from __future__ import unicode_literals

import warnings

import kgb
from django.conf import settings
from django.test import override_settings

from djblets.deprecation import RemovedInDjblets30Warning
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


class NewStyleMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)


class OldStyleMiddleware(object):
    def __init__(self):
        pass

    def process_request(self, request):
        return None

    def process_response(self, request, response):
        return response


class MyTestExtension1(Extension):
    middleware = [
        'djblets.extensions.tests.test_middleware.NewStyleMiddleware',
    ]


class MyTestExtension2(Extension):
    middleware = [
        'djblets.extensions.tests.test_middleware.OldStyleMiddleware',
    ]


class MyTestExtension3(Extension):
    middleware = [
        'djblets.extensions.tests.test_middleware.OldStyleMiddleware',
        'djblets.extensions.tests.test_middleware.NewStyleMiddleware',
    ]


class MiddlewareTests(kgb.SpyAgency, ExtensionTestCaseMixin, TestCase):
    """Unit tests for extension middleware."""

    @override_settings(MIDDLEWARE_CLASSES=MIDDLEWARE,
                       MIDDLEWARE=None)
    def test_new_style_middleware_with_old_setting(self):
        """Testing new-style extension middleware with MIDDLEWARE_CLASSES
        setting
        """
        self.spy_on(NewStyleMiddleware.__call__,
                    owner=NewStyleMiddleware)

        message = (
            'Application is running with old-style MIDDLEWARE_CLASSES '
            'setting but extension TestPackage defines the following '
            'new-style (Django 1.10+) middleware entries:\n'
            '*  <class \'djblets.extensions.tests.test_middleware.'
            'NewStyleMiddleware\'>'
        )

        with self.assertWarns(RemovedInDjblets30Warning, message):
            self.setup_extension(MyTestExtension1)

        self.client.get('/')

        self.assertSpyNotCalled(NewStyleMiddleware.__call__)

    @override_settings(MIDDLEWARE_CLASSES=None,
                       MIDDLEWARE=MIDDLEWARE)
    def test_new_style_middleware_with_new_setting(self):
        """Testing new-style extension middleware with MIDDLEWARE setting"""
        del settings.MIDDLEWARE_CLASSES

        self.spy_on(NewStyleMiddleware.__call__,
                    owner=NewStyleMiddleware)

        self.setup_extension(MyTestExtension1)

        self.client.get('/')

        self.assertSpyCalled(NewStyleMiddleware.__call__)

    @override_settings(MIDDLEWARE_CLASSES=MIDDLEWARE,
                       MIDDLEWARE=None)
    def test_old_style_middleware_with_old_setting(self):
        """Testing old-style extension middleware with MIDDLEWARE_CLASSES
        setting
        """
        self.spy_on(OldStyleMiddleware.process_request,
                    owner=OldStyleMiddleware)
        self.spy_on(OldStyleMiddleware.process_response,
                    owner=OldStyleMiddleware)

        self.setup_extension(MyTestExtension2)

        self.client.get('/')

        self.assertSpyCalled(OldStyleMiddleware.process_request)
        self.assertSpyCalled(OldStyleMiddleware.process_response)

    @override_settings(MIDDLEWARE_CLASSES=None,
                       MIDDLEWARE=MIDDLEWARE)
    def test_old_style_middleware_with_new_setting(self):
        """Testing old-style extension middleware with MIDDLEWARE setting"""
        del settings.MIDDLEWARE_CLASSES

        self.spy_on(OldStyleMiddleware.process_request,
                    owner=OldStyleMiddleware)
        self.spy_on(OldStyleMiddleware.process_response,
                    owner=OldStyleMiddleware)

        message = (
            "Application is running with new-style MIDDLEWARE setting "
            "but extension TestPackage defined the following old-style "
            "(pre-Django 1.10) middleware entries:\n"
            "*  <class 'djblets.extensions.tests.test_middleware."
            "OldStyleMiddleware'>"
        )

        with self.assertWarns(RemovedInDjblets30Warning, message):
            self.setup_extension(MyTestExtension2)

        self.client.get('/')

        self.assertSpyCalled(OldStyleMiddleware.process_request)
        self.assertSpyCalled(OldStyleMiddleware.process_response)

    @override_settings(MIDDLEWARE_CLASSES=MIDDLEWARE,
                       MIDDLEWARE=None)
    def test_mixed_style_middleware_with_old_setting(self):
        """Testing mixed-style extension middlewares with MIDDLEWARE_CLASSES
        setting
        """
        self.spy_on(NewStyleMiddleware.__call__,
                    owner=NewStyleMiddleware)
        self.spy_on(OldStyleMiddleware.process_request,
                    owner=OldStyleMiddleware)
        self.spy_on(OldStyleMiddleware.process_response,
                    owner=OldStyleMiddleware)

        message = (
            "Application is running with old-style MIDDLEWARE_CLASSES "
            "setting but extension TestPackage defines the following "
            "new-style (Django 1.10+) middleware entries:\n"
            "*  <class 'djblets.extensions.tests.test_middleware."
            "NewStyleMiddleware'>"
        )

        with self.assertWarns(RemovedInDjblets30Warning, message):
            self.setup_extension(MyTestExtension3)

        self.client.get('/')

        self.assertSpyNotCalled(NewStyleMiddleware.__call__)
        self.assertSpyCalled(OldStyleMiddleware.process_request)
        self.assertSpyCalled(OldStyleMiddleware.process_response)

    @override_settings(MIDDLEWARE_CLASSES=None,
                       MIDDLEWARE=MIDDLEWARE)
    def test_mixed_style_middleware_with_new_setting(self):
        """Testing mixed-style extension middlewares with MIDDLEWARE setting"""
        del settings.MIDDLEWARE_CLASSES

        self.spy_on(NewStyleMiddleware.__call__,
                    owner=NewStyleMiddleware)
        self.spy_on(OldStyleMiddleware.process_request,
                    owner=OldStyleMiddleware)
        self.spy_on(OldStyleMiddleware.process_response,
                    owner=OldStyleMiddleware)

        message = (
            "Application is running with new-style MIDDLEWARE setting "
            "but extension TestPackage defined the following old-style "
            "(pre-Django 1.10) middleware entries:\n"
            "*  <class 'djblets.extensions.tests.test_middleware."
            "OldStyleMiddleware'>"
        )

        with self.assertWarns(RemovedInDjblets30Warning, message):
            self.setup_extension(MyTestExtension3)

        self.client.get('/')

        self.assertSpyCalled(NewStyleMiddleware.__call__)
        self.assertSpyCalled(OldStyleMiddleware.process_request)
        self.assertSpyCalled(OldStyleMiddleware.process_response)
