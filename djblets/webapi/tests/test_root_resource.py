"""Unit tests for the Root Resource."""

from djblets.extensions.manager import ExtensionManager
from djblets.extensions.resources import ExtensionResource
from djblets.testing.testcases import TestCase
from djblets.webapi.resources import RootResource


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

    def test_unregister_uri_template_without_relative_resource(self):
        """Testing unregister_uri_template without a relative resource"""
        self.root_res.unregister_uri_template('extensions')
        self.assertFalse(self.root_res._registered_uri_templates[None])

    def test_unregister_uri_template_with_relative_resource(self):
        """Testing unregister_uri_template with a relative resource"""
        self.root_res.unregister_uri_template('extensions', self.ext_res)
        self.assertFalse(self.root_res._registered_uri_templates[
            self.ext_res])

    def test_register_uri_template_clears_uri_template_cache(self):
        """Testing register_uri_templates clears the URI template cache"""
        self.root_res._uri_templates = {
            'key1': 'value1',
            'key2': 'value2',
        }
        self.root_res.register_uri_template(
            'extension_name', 'some/relative/path/')
        self.assertEqual(self.root_res._uri_templates, {})

    def test_unregister_uri_template_clears_uri_template_cache(self):
        """Testing unregister_uri_templates clears the URI template cache"""
        self.root_res._uri_templates = {
            'key1': 'value1',
            'key2': 'value2',
        }
        self.root_res.unregister_uri_template('extension-1')
        self.assertEqual(self.root_res._uri_templates, {})
