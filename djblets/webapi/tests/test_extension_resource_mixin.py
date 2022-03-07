"""Unit tests for the ExtensionResource mixin."""

from django.test import RequestFactory

from djblets.extensions.extension import Extension
from djblets.extensions.resources import (ExtensionResource,
                                          ExtensionRootResourceMixin)
from djblets.extensions.testing import ExtensionTestCaseMixin
from djblets.testing.testcases import TestCase
from djblets.webapi.resources import RootResource, WebAPIResource


class MyTestChildResource1(WebAPIResource):
    """Test api resource item under MockResourceOne."""

    name = 'test_child_resource_item_1'
    uri_object_key = 'test_child_resource_item_1_id'


class MyTestChildResource2(WebAPIResource):
    """Test api resource item under MockResourceTwo."""

    name = 'test_child_resource_item_2'
    uri_object_key = 'test_child_resource_item_2_id'


class MyTestResource1(WebAPIResource):
    """Test api resource exposed by MockExtension."""

    name = 'test_resource_1'
    item_child_resources = [MyTestChildResource1()]


class MyTestResource2(WebAPIResource):
    """Test api resource exposed by MockExtension."""

    name = 'test_resource_2'
    item_child_resources = [MyTestChildResource2()]


class MyTestExtension(Extension):
    """Test extension for use by ExtensionTemplateTests."""

    resources = [MyTestResource1(), MyTestResource2()]


class MyTestRootResource(ExtensionRootResourceMixin, RootResource):
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

    extension_class = MyTestExtension

    def setUp(self):
        super(ExtensionRootResourceMixinTests, self).setUp()

        self.ext_resource = ExtensionResource(self.extension_mgr)
        self.root_resource = MyTestRootResource([self.ext_resource])
        self.request = RequestFactory().get('/')

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
                'MyTestExtension/test-resource-1s/'
            ),
            'test_resource_2s': (
                'http://testserver/extensions/djblets.webapi.tests.'
                'test_extension_resource_mixin.'
                'MyTestExtension/test-resource-2s/'
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
