"""WebAPI scope dictionary tests."""

from __future__ import unicode_literals

from django.test.utils import override_settings
from django.utils import six
from oauth2_provider.settings import oauth2_settings

from djblets.extensions.extension import Extension
from djblets.extensions.manager import ExtensionManager
from djblets.extensions.models import RegisteredExtension
from djblets.extensions.testing.testcases import ExtensionTestCaseMixin
from djblets.testing.testcases import TestCase
from djblets.webapi.oauth2_scopes import (
    ExtensionEnabledWebAPIScopeDictionary,
    WebAPIScopeDictionary,
    enable_web_api_scopes,
    get_scope_dictionary)
from djblets.webapi.resources.mixins.oauth2_tokens import (
    ResourceOAuth2TokenMixin)
from djblets.webapi.testing.resources import make_resource_tree


class WebAPIScopeDictionaryTests(TestCase):
    """Tests for WebAPIScopeDictionary."""

    @classmethod
    def setUpClass(cls):
        super(WebAPIScopeDictionaryTests, cls).setUpClass()

        cls._resources = make_resource_tree(mixins=[
            ResourceOAuth2TokenMixin,
        ])

    def test_scope_dict(self):
        """Testing WebAPIScopeDictionary.scope_dict generates and caches scopes
        """
        scopes = WebAPIScopeDictionary(self._resources.root_resource)

        self.assertEqual(
            scopes.scope_dict,
            {
                'root:read': ('Ability to perform HTTP GET on the root '
                              'resource'),
                'item-child:read': ('Ability to perform HTTP GET on the '
                                    'item-child resource'),
                'item-child:write': ('Ability to perform HTTP POST, PUT on '
                                     'the item-child resource'),
                'list-child:read': ('Ability to perform HTTP GET on the '
                                    'list-child resource'),
                'list-child:destroy': ('Ability to perform HTTP DELETE on the '
                                       'list-child resource'),
                'parent:read': ('Ability to perform HTTP GET on the parent '
                                'resource'),
            })

    def test_getitem(self):
        """Testing WebAPIScopeDictionary.__getitem__"""
        scopes = WebAPIScopeDictionary(self._resources.root_resource)

        self.assertEqual(scopes['root:read'],
                         'Ability to perform HTTP GET on the root resource')

        with self.assertRaises(KeyError):
            scopes['bad-key']

    def test_contains(self):
        """Testing WebAPIScopeDictionary.__contains__"""
        scopes = WebAPIScopeDictionary(self._resources.root_resource)

        self.assertIn('root:read', scopes)
        self.assertNotIn('bad-key', scopes)

    def test_iterkeys(self):
        """Testing WebAPIScopeDictionary with six.iterkeys"""
        # Note that we have both implemented for Python 2/3 compatibility.
        # We'll actually be testing how this is used under the hood, with
        # six.iterkeys().
        scopes = WebAPIScopeDictionary(self._resources.root_resource)

        self.assertEqual(set(six.iterkeys(scopes)), {
            'root:read',
            'item-child:read',
            'item-child:write',
            'list-child:read',
            'list-child:destroy',
            'parent:read',
        })

    def test_clear(self):
        """Testing WebAPIScopeDictionary.clear"""
        scopes = WebAPIScopeDictionary(self._resources.root_resource)

        self.assertEqual(
            scopes.scope_dict,
            {
                'root:read': ('Ability to perform HTTP GET on the root '
                              'resource'),
                'item-child:read': ('Ability to perform HTTP GET on the '
                                    'item-child resource'),
                'item-child:write': ('Ability to perform HTTP POST, PUT on '
                                     'the item-child resource'),
                'list-child:read': ('Ability to perform HTTP GET on the '
                                    'list-child resource'),
                'list-child:destroy': ('Ability to perform HTTP DELETE on the '
                                       'list-child resource'),
                'parent:read': ('Ability to perform HTTP GET on the parent '
                                'resource'),
            })

        scopes.clear()
        self.assertEqual(scopes._scope_dict, {})


class ExtensionEnabledWebAPIScopeDictionaryTests(ExtensionTestCaseMixin,
                                                 TestCase):
    """Tests for ExtensionEnabledWebAPIScopeDictionary."""

    @classmethod
    def setUpClass(cls):
        super(ExtensionEnabledWebAPIScopeDictionaryTests, cls).setUpClass()

        cls._extension_manager = ExtensionManager('')

        cls._resources = make_resource_tree(mixins=[
            ResourceOAuth2TokenMixin,
        ], extension_manager=cls._extension_manager)

        class TestExtensionResource(cls._resources.base_resource):
            """An example resource on an extension."""

            name = 'test-ext'
            allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

        cls._extension_resource = TestExtensionResource()

        class TestExtension(Extension):
            """An example extension."""

            extension_id = \
                'djblets.webapi.tests.test_oauth2_scopes.TestExtension'
            resources = [cls._extension_resource]
            registration = RegisteredExtension()

        cls.extension_class = TestExtension

    def test_scope_dict(self):
        """Testing ExtensionEnabledWebAPIScopeDictionary.scope_dict generates
        and caches scopes
        """
        self.extension_mgr.disable_extension(self.extension_class.extension_id)
        scopes = ExtensionEnabledWebAPIScopeDictionary(
            self._resources.root_resource)

        original_scope_dict = scopes.scope_dict

        base_scopes = {
            'root:read': 'Ability to perform HTTP GET on the root resource',
            'extension:read': ('Ability to perform HTTP GET on the '
                               'extension resource'),
            'extension:write': ('Ability to perform HTTP PUT on the '
                                'extension resource'),
            'item-child:read': ('Ability to perform HTTP GET on the '
                                'item-child resource'),
            'item-child:write': ('Ability to perform HTTP POST, PUT on '
                                 'the item-child resource'),
            'list-child:read': ('Ability to perform HTTP GET on the '
                                'list-child resource'),
            'list-child:destroy': ('Ability to perform HTTP DELETE on the '
                                   'list-child resource'),
            'parent:read': ('Ability to perform HTTP GET on the parent '
                            'resource'),
        }
        self.assertEqual(original_scope_dict, base_scopes)

        self.extension_mgr.enable_extension(self.extension_class.extension_id)
        self.assertEqual(scopes._scope_dict, {})

        new_base_scopes = dict({
            'test-ext:read': ('Ability to perform HTTP GET on the test-ext '
                              'resource'),
            'test-ext:write': ('Ability to perform HTTP POST, PUT on the '
                               'test-ext resource'),
            'test-ext:destroy': ('Ability to perform HTTP DELETE on the '
                                 'test-ext resource'),
        }, **base_scopes)

        new_scope_dict = scopes.scope_dict
        self.assertIs(new_scope_dict, original_scope_dict)
        self.assertEqual(new_scope_dict, new_base_scopes)

        self.extension_mgr.disable_extension(self.extension_class.extension_id)
        self.assertEqual(scopes._scope_dict, {})

        newest_scope_dict = scopes.scope_dict
        self.assertIs(newest_scope_dict, new_scope_dict)
        self.assertIs(newest_scope_dict, original_scope_dict)
        self.assertEqual(newest_scope_dict, base_scopes)


class ScopeEnablingTests(TestCase):
    """Tests for enabling WebAPI scopes at runtime."""

    @override_settings(
        WEB_API_ROOT_RESOURCE='djblets.webapi.tests.test_oauth2_auth.'
                              'root_resource',
    )
    def test_enable_webapi_scopes(self):
        """Testing enable_web_api_scopes()"""
        enable_web_api_scopes()
        scopes = get_scope_dictionary()

        self.assertIs(oauth2_settings.SCOPES, scopes)
        self.assertEqual(set(oauth2_settings._SCOPES), {
            'root:read',
            'item-child:read',
            'item-child:write',
            'list-child:read',
            'list-child:destroy',
            'parent:read',
        })
