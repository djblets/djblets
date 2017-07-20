"""WebAPI scope dictionary tests."""

from __future__ import unicode_literals

from oauth2_provider.settings import oauth2_settings
from django.test.utils import override_settings

from djblets.extensions.extension import Extension
from djblets.extensions.manager import ExtensionManager
from djblets.extensions.models import RegisteredExtension
from djblets.extensions.testing.testcases import ExtensionTestCaseMixin
from djblets.testing.testcases import TestCase
from djblets.webapi.oauth2_scopes import (
    ExtensionEnabledWebAPIScopeDictionary,
    WebAPIScopeDictionary,
    enable_web_api_scopes,
    disable_web_api_scopes,
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

    def test_scope_list(self):
        """Testing WebAPIScopeDictionary.scope_list generates and caches
        scopes
        """
        scopes = WebAPIScopeDictionary.from_root(self._resources.root_resource)
        scope_list = scopes.scope_list

        # Ensure the scope list is correctly cached.
        self.assertIs(scopes.scope_list, scope_list)

        self.assertEqual(
            set(scope_list),
            {
                'root:read',
                'item-child:read',
                'item-child:write',
                'list-child:read',
                'list-child:destroy',
                'parent:read',
            })


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

    def test_scope_list(self):
        """Testing ExtensionEnabledWebAPIScopeDictionary.scope_list generates
        and caches scopes
        """
        self.extension_mgr.disable_extension(self.extension_class.extension_id)
        scopes = ExtensionEnabledWebAPIScopeDictionary.from_root(
            self._resources.root_resource)

        original_scope_list = scopes.scope_list
        self.assertIs(scopes.scope_list, original_scope_list)

        base_scopes = {
            'root:read',
            'extension:read',
            'extension:write',
            'item-child:read',
            'item-child:write',
            'list-child:read',
            'list-child:destroy',
            'parent:read',
        }
        self.assertEqual(set(original_scope_list), base_scopes)

        self.extension_mgr.enable_extension(self.extension_class.extension_id)

        new_scope_list = scopes.scope_list
        self.assertIs(scopes.scope_list, new_scope_list)
        self.assertIsNot(new_scope_list, original_scope_list)
        self.assertEqual(
            set(new_scope_list),
            base_scopes | {
                'test-ext:read',
                'test-ext:write',
                'test-ext:destroy',
            }
        )

        self.extension_mgr.disable_extension(self.extension_class.extension_id)
        newest_scope_list = scopes.scope_list
        self.assertIs(scopes.scope_list, newest_scope_list)
        self.assertIsNot(newest_scope_list, new_scope_list)
        self.assertIsNot(newest_scope_list, original_scope_list)
        self.assertEqual(set(newest_scope_list), base_scopes)


class ScopeEnablingTests(TestCase):
    """Tests for enabling WebAPI scopes at runtime."""

    def tearDown(self):
        super(ScopeEnablingTests, self).tearDown()

        disable_web_api_scopes()

    @override_settings(
        WEB_API_ROOT_RESOURCE='djblets.webapi.tests.test_oauth2_auth.'
                              'root_resource',
    )
    def test_enable_webapi_scopes(self):
        """Testing enable_web_api_scopes()"""
        enable_web_api_scopes()
        scopes = get_scope_dictionary()

        self.assertIs(oauth2_settings.SCOPES, scopes)
        self.assertIs(oauth2_settings._SCOPES, scopes.scope_list)
