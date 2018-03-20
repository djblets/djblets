"""Unit tests for the ExtensionResource mixin."""

from __future__ import unicode_literals

from django.test import RequestFactory

from djblets.extensions.extension import Extension
from djblets.extensions.manager import ExtensionManager
from djblets.extensions.resources import (ExtensionResource,
                                          ExtensionRootResourceMixin)
from djblets.extensions.testing import ExtensionTestCaseMixin
from djblets.testing.testcases import TestCase
from djblets.webapi.resources import RootResource, WebAPIResource


class TestChildResource1(WebAPIResource):
    """Test api resource item under MockResourceOne."""

    name = 'test_child_resource_item_1'
    uri_object_key = 'test_child_resource_item_1_id'


class TestChildResource2(WebAPIResource):
    """Test api resource item under MockResourceTwo."""

    name = 'test_child_resource_item_2'
    uri_object_key = 'test_child_resource_item_2_id'


class TestResource1(WebAPIResource):
    """Test api resource exposed by MockExtension."""

    name = 'test_resource_1'
    item_child_resources = [TestChildResource1()]


class TestResource2(WebAPIResource):
    """Test api resource exposed by MockExtension."""

    name = 'test_resource_2'
    item_child_resources = [TestChildResource2()]


class TestExtension(Extension):
    """Test extension for use by ExtensionTemplateTests."""

    resources = [TestResource1(), TestResource2()]


class TestRootResource(ExtensionRootResourceMixin, RootResource):
    """RootResource for testing ExtensionRootResourceMixin."""

    def get_extension_resource(self):
        """Return the mocked extension resource.

        Returns:
            djblets.extensions.resources.ExtensionResource:
            The mock extension resource.
        """
        return self.list_child_resources[0]


class ExtensionRootResourceMixinTests(ExtensionTestCaseMixin, TestCase):
    """Unit tests for the ExtensionRootResourceMixin."""

    extension_class = TestExtension

    def setUp(self):
        self.mgr = ExtensionManager('')
        self.ext_resource = ExtensionResource(self.mgr)
        self.root_resource = TestRootResource([self.ext_resource])
        self.request = RequestFactory().get('/')

        super(ExtensionRootResourceMixinTests, self).setUp()

    def test_generate_extension_uris_for_template(self):
        """Testing ExtensionRootResourceMixin generates URI templates when
        extensions are initialized
        """
        self.root_resource._generate_extension_uris_for_template(
            self.extension)
        actual_result = self.root_resource.get_uri_templates(
            self.request)
        self.assertEqual(actual_result, {
            'extensions': 'http://testserver/extensions/',
            'extension': 'http://testserver/extensions/{extension_name}/',
            'test_resource_1s': (
                'http://testserver/extensions/djblets.webapi.tests.'
                'test_extension_resource_mixin.'
                'TestExtension/test-resource-1s/'
            ),
            'test_resource_2s': (
                'http://testserver/extensions/djblets.webapi.tests.'
                'test_extension_resource_mixin.'
                'TestExtension/test-resource-2s/'
            ),
            'root': 'http://testserver/',
        })

    def test_remove_extension_uris_from_template(self):
        """Testing ExtensionRootResourceMixin removes URI templates when
        extensions are disabled
        """
        self.root_resource._generate_extension_uris_for_template(
            self.extension)
        self.root_resource._remove_extension_uris_from_template(
            self.extension)
        actual_result = self.root_resource.get_uri_templates(
            self.request)
        self.assertEqual(actual_result, {
            'extensions': u'http://testserver/extensions/',
            'root': 'http://testserver/',
            'extension': 'http://testserver/extensions/{extension_name}/',
        })
