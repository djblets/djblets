"""Unit tests for the Root Resource."""

from django.core.exceptions import ImproperlyConfigured
from django.test.client import RequestFactory
from django.test.utils import override_settings

from djblets.extensions.manager import ExtensionManager
from djblets.extensions.resources import ExtensionResource
from djblets.testing.testcases import TestCase
from djblets.webapi.resources import RootResource, WebAPIResource


# Will appear in the URI templates list under the names 'mock' and 'mocks'.
class MockResource(WebAPIResource):
    name = 'mock'
    uri_object_key = 'mock_id'


# Will cause a conflict with MockResource when added to the URI templates list.
class DuplicateMockResource(MockResource):
    uri_name = 'duplicatemocks'


# Will appear in the URI templates list under the names 'test_mock' and
# 'test_mocks'.
class OtherMockResource(MockResource):
    uri_template_name = 'test_mock'


# Will be excluded from the URI templates list.
class ExcludedResource(WebAPIResource):
    name = 'exclude'
    uri_template_name = None
    uri_object_key = 'exclude_id'


# Will have its item resource excluded but list resource included in the
# URI templates list.
class IncludedListResource(WebAPIResource):
    name = 'test_list'
    uri_template_name = None
    uri_template_name_plural = 'lists'


class RootResourceTests(TestCase):
    """Unit tests for RootResource.

    Version Added:
        3.1.0
    """

    def setUp(self):
        """Setup for the RootResource unit tests."""
        super().setUp()

        self.root_res = RootResource(
            [
                MockResource(),
                OtherMockResource(),
                ExcludedResource(),
                IncludedListResource(),
            ]
        )
        self.request = RequestFactory().get('/')

    def test_get_uri_templates_uses_uri_template_names(self):
        """Testing RootResource.get_uri_templates uses the uri_template_name
        and uri_template_name_plural for resources instead of name and
        plural_name
        """
        uri_templates = self.root_res.get_uri_templates(self.request)

        self.assertEqual(uri_templates['mock'],
                         'http://testserver/mocks/{mock_id}/')
        self.assertEqual(uri_templates['mocks'], 'http://testserver/mocks/')

        self.assertEqual(uri_templates['test_mock'],
                         'http://testserver/mocks/{mock_id}/')
        self.assertEqual(uri_templates['test_mocks'],
                         'http://testserver/mocks/')

        self.assertEqual(uri_templates['lists'],
                         'http://testserver/test-lists/')

    def test_get_uri_templates_skips_with_none(self):
        """Testing RootResource.get_uri_templates skips item resources that
        have their uri_template_name and list resources that have their
        uri_template_plural_name set to None
        """
        uri_templates = self.root_res.get_uri_templates(self.request)

        self.assertEqual(uri_templates['mock'],
                         'http://testserver/mocks/{mock_id}/')
        self.assertEqual(uri_templates['mocks'], 'http://testserver/mocks/')

        self.assertEqual(uri_templates['test_mocks'],
                         'http://testserver/mocks/')
        self.assertEqual(uri_templates['test_mock'],
                         'http://testserver/mocks/{mock_id}/')

        self.assertEqual(uri_templates['lists'],
                         'http://testserver/test-lists/')
        self.assertNotIn('test_list', uri_templates)

        self.assertNotIn('exclude', uri_templates)
        self.assertNotIn('excludes', uri_templates)

    @override_settings(DEBUG=False)
    def test_get_uri_templates_must_be_unique(self):
        """Testing RootResource.get_uri_templates logs an error when multiple
        URI templates are mapped to the same name in production mode
        """
        self.root_res = RootResource([MockResource(), DuplicateMockResource()])
        expected_message = (
            'More than one URI template was mapped to the "mocks" name: '
            'http://testserver/mocks/, http://testserver/duplicatemocks/. '
            'Only the first one will be included in the URI templates list. '
            'To include the other URI templates, they must be mapped to a '
            'unique name by setting each resource\'s uri_template_name '
            'property.'
        )

        with self.assertLogs() as logs:
            uri_templates = self.root_res.get_uri_templates(self.request)

            self.assertEqual(logs.records[0].getMessage(), expected_message)
            self.assertIn('mocks', uri_templates)
            self.assertEqual(uri_templates['mocks'],
                             'http://testserver/mocks/')

    @override_settings(DEBUG=True)
    def test_get_uri_templates_must_be_unique_debug(self):
        """Testing RootResource.get_uri_templates raises an error when multiple
        URI templates are mapped to the same name in debug mode
        """
        self.root_res = RootResource([MockResource(), DuplicateMockResource()])
        expected_message = (
            'More than one URI template was mapped to the "mocks" name: '
            'http://testserver/mocks/, http://testserver/duplicatemocks/. '
            'Each URI template must be mapped to a unique URI template '
            'name in order to be included in the URI templates list. This can '
            'be set through the uri_template_name property.'
        )

        with self.assertRaisesMessage(ImproperlyConfigured, expected_message):
            self.root_res.get_uri_templates(self.request)


class RootResourceTemplateRegistrationTests(TestCase):
    """Unit tests for the (un)registration of templates in RootResource."""

    def setUp(self):
        super(RootResourceTemplateRegistrationTests, self).setUp()

        self.ext_mgr = ExtensionManager('')
        self.ext_res = ExtensionResource(self.ext_mgr)
        self.root_res = RootResource([self.ext_res])
        self.root_res._registered_uri_templates = {
            self.ext_res: {
                'extensions': 'http://localhost:8080/api/extensions/'
            },
            None: {
                'extensions': 'http://localhost:8080/api/extensions/none/'
            },
        }

    def test_register_uri_template_without_relative_resource(self):
        """Testing register_uri_templates without a relative resource"""
        self.root_res.register_uri_template(name='key', relative_path='value')
        actual_result = self.root_res._registered_uri_templates[None]
        self.assertEqual(actual_result, {
            'extensions': 'http://localhost:8080/api/extensions/none/',
            'key': 'value',
        })

    def test_register_uri_template_with_relative_resource(self):
        """Testing register_uri_templates with a relative resource"""
        mock_extension_resource = ExtensionResource(self.ext_mgr)
        self.root_res.register_uri_template(
            name='key',
            relative_path='value',
            relative_resource=mock_extension_resource)
        actual_result = self.root_res._registered_uri_templates[
            mock_extension_resource]
        self.assertEqual(actual_result, {'key': 'value'})

    def test_register_uri_template_clears_uri_template_cache(self):
        """Testing register_uri_templates clears the URI template cache"""
        self.root_res._uri_templates = {
            'key1': 'value1',
            'key2': 'value2',
        }
        self.root_res.register_uri_template(
            'extension_name', 'some/relative/path/')
        self.assertEqual(self.root_res._uri_templates, {})

    def test_register_uri_template_overwrites_existing_uri_template(self):
        """Testing register_uri_templates overwrites existing uri templates and
        logs a message saying so
        """
        expected_message = ('The extensions resource is already mapped to the '
                            'following URI template: '
                            'http://localhost:8080/api/extensions/none/. This '
                            'will be overwritten by the new URI template: '
                            'http://localhost:8080/api/different/.')

        with self.assertLogs(level='DEBUG') as logs:
            self.root_res.register_uri_template(
                name='extensions',
                relative_path='http://localhost:8080/api/different/')
            actual_result = self.root_res._registered_uri_templates[None]

            self.assertEqual(logs.records[0].getMessage(), expected_message)
            self.assertEqual(actual_result, {
                'extensions': 'http://localhost:8080/api/different/',
            })

    def test_unregister_uri_template_without_relative_resource(self):
        """Testing unregister_uri_template without a relative resource"""
        self.root_res.unregister_uri_template('extensions')
        self.assertFalse(self.root_res._registered_uri_templates[None])

    def test_unregister_uri_template_with_relative_resource(self):
        """Testing unregister_uri_template with a relative resource"""
        self.root_res.unregister_uri_template('extensions', self.ext_res)
        self.assertFalse(self.root_res._registered_uri_templates[
            self.ext_res])

    def test_unregister_uri_template_clears_uri_template_cache(self):
        """Testing unregister_uri_templates clears the URI template cache"""
        self.root_res._uri_templates = {
            'key1': 'value1',
            'key2': 'value2',
        }
        self.root_res.unregister_uri_template('extension-1')
        self.assertEqual(self.root_res._uri_templates, {})