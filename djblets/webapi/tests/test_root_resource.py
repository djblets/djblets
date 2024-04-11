"""Unit tests for the Root Resource."""

import kgb

from django.core.exceptions import ImproperlyConfigured
from django.test.client import RequestFactory
from django.test.utils import override_settings

from djblets.extensions.manager import ExtensionManager
from djblets.extensions.resources import ExtensionResource
from djblets.testing.testcases import TestCase
from djblets.webapi.resources import RootResource, WebAPIResource
from djblets.webapi.resources.root import _URITemplatesCache


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


class RootResourceTests(kgb.SpyAgency, TestCase):
    """Unit tests for RootResource.

    Version Added:
        3.1
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

    @override_settings(DEBUG=True,
                       PRODUCTION=True)
    def test_get_uri_templates_must_be_unique_with_debug_prod(
        self,
    ) -> None:
        """Testing RootResource.get_uri_templates logs an error when multiple
        URI templates are mapped to the same name in DEBUG, PRODUCTION modes
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

    @override_settings(DEBUG=False,
                       PRODUCTION=True)
    def test_get_uri_templates_must_be_unique_with_non_debug_prod(
        self,
    ) -> None:
        """Testing RootResource.get_uri_templates logs an error when multiple
        URI templates are mapped to the same name in non-DEBUG, PRODUCTION
        modes
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

    @override_settings(DEBUG=False,
                       PRODUCTION=False)
    def test_get_uri_templates_must_be_unique_non_debug_non_prod(
        self,
    ) -> None:
        """Testing RootResource.get_uri_templates raises an error when multiple
        URI templates are mapped to the same name in non-DEBUG, non-PRODUCTION
        modes
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

    @override_settings(DEBUG=True,
                       PRODUCTION=False)
    def test_get_uri_templates_must_be_unique_with_debug_non_prod(
        self,
    ) -> None:
        """Testing RootResource.get_uri_templates raises an error when multiple
        URI templates are mapped to the same name in DEBUG, non-PRODUCTION
        modes
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

    def test_get_uri_templates_caching(self):
        """Testing RootResource.get_uri_templates caching"""
        resource = self.root_res
        self.spy_on(resource.build_uri_templates)

        # Check repeated calls to the same URL.
        request1 = RequestFactory().get('/api1/')
        uri_templates1 = resource.get_uri_templates(request1)
        uri_templates2 = resource.get_uri_templates(request1)

        self.assertEqual(uri_templates1, {
            'lists': 'http://testserver/api1/test-lists/',
            'mock': 'http://testserver/api1/mocks/{mock_id}/',
            'mocks': 'http://testserver/api1/mocks/',
            'root': 'http://testserver/api1/',
            'test_mock': 'http://testserver/api1/mocks/{mock_id}/',
            'test_mocks': 'http://testserver/api1/mocks/',
        })
        self.assertIs(uri_templates1, uri_templates2)
        self.assertSpyCallCount(resource.build_uri_templates, 1)
        self.assertSpyLastCalledWith(resource.build_uri_templates,
                                     'http://testserver/api1/')

        # Check against a second API URL.
        request2 = RequestFactory().get('/api2/')
        uri_templates3 = resource.get_uri_templates(request2)
        uri_templates4 = resource.get_uri_templates(request2)

        self.assertEqual(uri_templates3, {
            'lists': 'http://testserver/api2/test-lists/',
            'mock': 'http://testserver/api2/mocks/{mock_id}/',
            'mocks': 'http://testserver/api2/mocks/',
            'root': 'http://testserver/api2/',
            'test_mock': 'http://testserver/api2/mocks/{mock_id}/',
            'test_mocks': 'http://testserver/api2/mocks/',
        })
        self.assertIs(uri_templates3, uri_templates4)
        self.assertSpyCallCount(resource.build_uri_templates, 2)
        self.assertSpyLastCalledWith(resource.build_uri_templates,
                                     'http://testserver/api2/')

        # And invalidate the cache.
        resource._cached_uri_templates.clear()

        uri_templates5 = resource.get_uri_templates(request1)
        uri_templates6 = resource.get_uri_templates(request2)

        self.assertIsNot(uri_templates5, uri_templates1)
        self.assertEqual(uri_templates5, uri_templates1)
        self.assertIsNot(uri_templates6, uri_templates3)
        self.assertEqual(uri_templates6, uri_templates3)
        self.assertSpyCallCount(resource.build_uri_templates, 4)


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

    @override_settings(DEBUG=True,
                       PRODUCTION=False)
    def test_register_uri_template_clears_uri_template_cache(self):
        """Testing register_uri_templates clears the URI template cache"""
        resource = self.root_res
        request = RequestFactory().get('/api/')
        resource.get_uri_templates(request)
        self.assertEqual(len(resource._cached_uri_templates._cache), 1)

        resource.register_uri_template('extension_name', 'some/relative/path/')
        self.assertEqual(len(resource._cached_uri_templates._cache), 0)

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
        self.assertEqual(
            self.root_res._registered_uri_templates[self.ext_res],
            {})

    @override_settings(DEBUG=True,
                       PRODUCTION=False)
    def test_unregister_uri_template_clears_uri_template_cache(self):
        """Testing unregister_uri_templates clears the URI template cache"""
        resource = self.root_res
        request = RequestFactory().get('/api/')
        resource.get_uri_templates(request)
        self.assertEqual(len(resource._cached_uri_templates._cache), 1)

        resource.unregister_uri_template('extensions')
        self.assertEqual(len(resource._cached_uri_templates._cache), 0)


class URITemplateCacheTests(TestCase):
    """Unit tests for _URITemplatesCache.

    Version Added:
        3.2
    """

    def test_add(self):
        """Testing _URITemplatesCache.add"""
        cache = _URITemplatesCache()

        cache.add('/api1/', {
            'template1': 'http://localhost:8080/api1/resource1/',
            'template2': 'http://localhost:8080/api1/resource2/',
        })

        cache.add('/api2/', {
            'template3': 'http://localhost:8080/api2/resource3/',
        })

        self.assertEqual(
            list(cache._cache.items()),
            [
                ('/api1/', {
                    'template1': 'http://localhost:8080/api1/resource1/',
                    'template2': 'http://localhost:8080/api1/resource2/',
                }),
                ('/api2/', {
                    'template3': 'http://localhost:8080/api2/resource3/',
                }),
            ])

    def test_add_when_full(self):
        """Testing _URITemplatesCache.add when cache is full"""
        cache = _URITemplatesCache(max_size=2)

        cache.add('/api1/', {
            'template1': 'http://localhost:8080/api1/resource1/',
            'template2': 'http://localhost:8080/api1/resource2/',
        })

        cache.add('/api2/', {
            'template3': 'http://localhost:8080/api2/resource3/',
        })

        cache.add('/api3/', {
            'template4': 'http://localhost:8080/api3/resource4/',
        })

        self.assertEqual(
            list(cache._cache.items()),
            [
                ('/api2/', {
                    'template3': 'http://localhost:8080/api2/resource3/',
                }),
                ('/api3/', {
                    'template4': 'http://localhost:8080/api3/resource4/',
                }),
            ])

    def test_get(self):
        """Testing _URITemplatesCache.get"""
        cache = _URITemplatesCache()

        cache.add('/api1/', {
            'template1': 'http://localhost:8080/api1/resource1/',
            'template2': 'http://localhost:8080/api1/resource2/',
        })

        cache.add('/api2/', {
            'template3': 'http://localhost:8080/api2/resource3/',
        })

        cache.add('/api3/', {
            'template4': 'http://localhost:8080/api3/resource4/',
        })

        # Retrieving the second item should reorder it to last.
        self.assertEqual(
            cache.get('/api2/'),
            {
                'template3': 'http://localhost:8080/api2/resource3/',
            })

        self.assertEqual(
            list(cache._cache.items()),
            [
                ('/api1/', {
                    'template1': 'http://localhost:8080/api1/resource1/',
                    'template2': 'http://localhost:8080/api1/resource2/',
                }),
                ('/api3/', {
                    'template4': 'http://localhost:8080/api3/resource4/',
                }),
                ('/api2/', {
                    'template3': 'http://localhost:8080/api2/resource3/',
                }),
            ])

    def test_get_and_not_found(self):
        """Testing _URITemplatesCache.get with URI templates not found"""
        cache = _URITemplatesCache()

        with self.assertRaises(KeyError):
            self.assertIsNone(cache.get('/api/'))

        self.assertEqual(cache._cache, {})

    def test_get_and_not_found_and_build_func(self):
        """Testing _URITemplatesCache.get with URI templates not found and
        build_func=
        """
        cache = _URITemplatesCache()

        self.assertEqual(
            cache.get(
                '/api1/',
                build_func=lambda base_href: {
                    'template1': 'http://localhost:8080/api1/resource1/',
                    'template2': 'http://localhost:8080/api1/resource2/',
                }),
            {
                'template1': 'http://localhost:8080/api1/resource1/',
                'template2': 'http://localhost:8080/api1/resource2/',
            })

        self.assertEqual(
            list(cache._cache.items()),
            [
                ('/api1/', {
                    'template1': 'http://localhost:8080/api1/resource1/',
                    'template2': 'http://localhost:8080/api1/resource2/',
                }),
            ])

    def test_clear(self):
        """Testing _URITemplatesCache.clear"""
        cache = _URITemplatesCache()

        cache.add('/api1/', {
            'template1': 'http://localhost:8080/api1/resource1/',
            'template2': 'http://localhost:8080/api1/resource2/',
        })
        cache.clear()

        self.assertEqual(cache._cache, {})
