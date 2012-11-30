#
# tests.py -- Unit tests for extensions.
#
# Copyright (c) 2010-2011  Beanbag, Inc.
# Copyright (c) 2008-2010  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import os

from django.conf import settings
from django.conf.urls.defaults import include, patterns
from django.core.exceptions import ImproperlyConfigured
from mock import Mock

from djblets.extensions.base import _extension_managers, Extension, \
                                    ExtensionHook, ExtensionHookPoint, \
                                    ExtensionInfo, ExtensionManager, \
                                    Settings
from djblets.extensions.hooks import TemplateHook, URLHook
from djblets.testing.testcases import TestCase


class SettingsTest(TestCase):
    def setUp(self):
        # Build up a mocked extension
        self.extension = Mock()
        self.extension.registration = Mock()
        self.test_dict = {
            'test_key1': 'test_value1',
            'test_key2': 'test_value2',
        }
        self.extension.registration.settings = self.test_dict
        self.settings = Settings(self.extension)

    def test_constructor(self):
        """Testing the Extension's Settings constructor"""
        # Build the Settings objects
        self.assertEqual(self.extension, self.settings.extension)

        # Ensure that the registration settings dict gets
        # added to this Settings
        self.assertEqual(self.test_dict['test_key1'],
                         self.settings['test_key1'])

    def test_load_updates_dict(self):
        """Testing that Settings.load correctly updates core dict"""
        new_dict = {
            'test_new_key': 'test_new_value',
            'test_key1': 'new_value',
        }
        self.extension.registration.settings = new_dict
        self.settings.load()

        # Should have added test_new_key, and modified test_key1
        self.assertEqual(new_dict['test_new_key'],
                         self.settings['test_new_key'])
        self.assertEqual(new_dict['test_key1'], self.settings['test_key1'])

        # Should have left test_key2 alone
        self.assertEqual(self.test_dict['test_key2'],
                         self.settings['test_key2'])

    def test_load_silently_discards(self):
        """Testing that Settings.load silently ignores invalid settings"""
        some_string = 'This is a string'
        self.extension.registration.settings = some_string

        try:
            self.settings.load()
        except Exception:
            self.fail("Shouldn't have raised an exception")

    def test_save_updates_database(self):
        """Testing that Settings.save will correctly update registration"""
        registration = self.extension.registration
        self.settings['test_new_key'] = 'Test new value'
        generated_dict = dict(self.settings)
        self.settings.save()

        self.assertTrue(registration.save.called)
        self.assertEqual(generated_dict, registration.settings)


class TestExtensionWithRegistration(Extension):
    """A dummy extension for testing, with mocked
       registration and empty settings dict."""
    registration = Mock()
    registration.settings = dict()


class ExtensionTest(TestCase):
    def setUp(self):
        manager = ExtensionManager('')
        self.extension = \
            TestExtensionWithRegistration(extension_manager=manager)

        for index in range(0, 5):
            self.extension.hooks.add(Mock())

    def test_extension_constructor(self):
        """Tests the Extension constructor, ensures the defaults are what we
           expect"""
        self.assertEqual(type(self.extension.settings), Settings)
        self.assertEqual(self.extension, self.extension.settings.extension)

    def test_shutdown(self):
        """Tests that shutdown calls shutdown on all hooks"""
        self.extension.shutdown()

        for hook in self.extension.hooks:
            self.assertTrue(hook.shutdown.called)

    def test_get_admin_URLConf(self):
        """Tests that we can get and process admin URL configurations
           for an extension"""
        did_fail = False
        old_module = self.extension.__class__.__module__
        self.extension.__class__.__module__ = 'djblets.extensions.test.test'

        try:
            self.extension._get_admin_urlconf()
        except ImproperlyConfigured:
            did_fail = True
        finally:
            self.extension.__class__.__module__ = old_module

            if did_fail:
                self.fail("Should have loaded admin_urls.py")


class ExtensionInfoTest(TestCase):
    def setUp(self):
        self.entrypoint = Mock()
        self.entrypoint.dist = Mock()

        self.test_author = 'Test author lorem ipsum'
        self.test_description = 'Test description lorem ipsum'
        self.test_email = 'Test author@email.com'
        self.test_home_page = 'http://www.example.com'
        self.test_license = 'Test License MIT GPL Apache Drivers'
        self.test_module_name = 'testextension.dummy.dummy'
        self.test_module_to_app = 'testextension.dummy'
        self.test_project_name = 'TestProjectName'
        self.test_summary = 'Test summary lorem ipsum'
        self.test_version = '1.0'

        self.test_htdocs_path = os.path.join(settings.EXTENSIONS_STATIC_ROOT,
                                             self.test_project_name)

        self.test_metadata = {
            'Summary': self.test_summary,
            'Description': self.test_description,
            'Author': self.test_author,
            'Author-email': self.test_email,
            'License': self.test_license,
            'Home-page': self.test_home_page,
        }

        self.entrypoint.dist.get_metadata_lines = Mock(
            return_value=[
                "%s: %s" % (key, value)
                for key, value in self.test_metadata.iteritems()
            ])

        self.entrypoint.dist.project_name = self.test_project_name
        self.entrypoint.dist.version = self.test_version

        self.ext_class = Mock()
        self.ext_class.__module__ = self.test_module_name
        self.extension_info = ExtensionInfo(self.entrypoint, self.ext_class)

    def test_proper_construction(self):
        """Tests that an ExtensionInfo class is correctly generated
           from a given Extension class and entrypoint"""
        self.assertEqual(self.extension_info.app_name, self.test_module_to_app)
        self.assertEqual(self.extension_info.author, self.test_author)
        self.assertEqual(self.extension_info.author_email, self.test_email)
        self.assertEqual(self.extension_info.description,
                         self.test_description)
        self.assertFalse(self.extension_info.enabled)
        self.assertEqual(self.extension_info.htdocs_path,
                         self.test_htdocs_path)
        self.assertFalse(self.extension_info.installed)
        self.assertEqual(self.extension_info.license, self.test_license)
        self.assertEqual(self.extension_info.metadata, self.test_metadata)
        self.assertEqual(self.extension_info.name, self.test_project_name)
        self.assertEqual(self.extension_info.summary, self.test_summary)
        self.assertEqual(self.extension_info.url, self.test_home_page)
        self.assertEqual(self.extension_info.version, self.test_version)


class TestExtensionHook(ExtensionHook):
    """A dummy ExtensionHook to test with"""
    __metaclass__ = ExtensionHookPoint


class ExtensionHookTest(TestCase):
    def setUp(self):
        manager = ExtensionManager('')
        self.extension = \
            TestExtensionWithRegistration(extension_manager=manager)
        self.extension_hook = TestExtensionHook(self.extension)

    def test_extension_set(self):
        """Test to ensure that the ExtensionHook knows about the
           associated Extension"""
        self.assertEqual(self.extension, self.extension_hook.extension)

    def test_extension_knows_about_hook(self):
        """Test to ensure that the Extension knows about the associated
           ExtensionHook through its hooks set."""
        self.assertTrue(self.extension_hook in self.extension.hooks)

    def test_extension_hook_added_to_class_hooks(self):
        """Test to ensure that the ExtensionHook class knows about the
           instantiated ExtensionHook."""
        self.assertTrue(self.extension_hook in
                        self.extension_hook.__class__.hooks)

    def test_shutdown_removes_hook_from_class_hooks(self):
        """Test to ensure that when a hook is shutdown, that it is removed
           from the class list of instantiated ExtensionHooks."""
        self.extension_hook.shutdown()
        self.assertTrue(self.extension_hook not in
                        self.extension_hook.__class__.hooks)


class ExtensionHookPointTest(TestCase):
    def setUp(self):
        manager = ExtensionManager('')
        self.extension = \
            TestExtensionWithRegistration(extension_manager=manager)
        self.extension_hook_class = TestExtensionHook
        self.dummy_hook = Mock()
        self.extension_hook_class.add_hook(self.dummy_hook)

    def test_extension_hook_class_gets_hooks(self):
        """A class that derives from ExtensionHook gets a hooks collection for
           the entire class."""
        self.assertTrue(hasattr(self.extension_hook_class, "hooks"))

    def test_add_hook(self):
        """An ExtensionHookPoint will remember some hook passed into it through
           add_hook."""
        self.assertTrue(self.dummy_hook in self.extension_hook_class.hooks)

    def test_remove_hook(self):
        """An ExtensionHookPoint will forget some hook passed into it through
           remove_hook."""
        self.extension_hook_class.remove_hook(self.dummy_hook)
        self.assertTrue(self.dummy_hook not in self.extension_hook_class.hooks)


class ExtensionManagerTest(TestCase):
    def setUp(self):
        class TestExtension(Extension):
            """An empty, dummy extension for testing"""
            pass

        self.key = 'test_key'
        self.extension_class = TestExtension
        self.manager = ExtensionManager(self.key)
        self.fake_entrypoint = Mock()
        self.fake_entrypoint.load = Mock(return_value=self.extension_class)
        self.fake_entrypoint.dist = Mock()

        self.test_author = 'Test author lorem ipsum'
        self.test_description = 'Test description lorem ipsum'
        self.test_email = 'Test author@email.com'
        self.test_home_page = 'http://www.example.com'
        self.test_license = 'Test License MIT GPL Apache Drivers'
        self.test_module_name = 'testextension.dummy.dummy'
        self.test_module_to_app = 'testextension.dummy'
        self.test_project_name = 'TestProjectName'
        self.test_summary = 'Test summary lorem ipsum'
        self.test_version = '1.0'

        self.test_htdocs_path = os.path.join(settings.EXTENSIONS_STATIC_ROOT,
                                             self.test_project_name)

        self.test_metadata = {
            'Summary': self.test_summary,
            'Description': self.test_description,
            'Author': self.test_author,
            'Author-email': self.test_email,
            'License': self.test_license,
            'Home-page': self.test_home_page,
        }

        self.fake_entrypoint.dist.get_metadata_lines = Mock(
            return_value=[
                "%s: %s" % (key, value)
                for key, value in self.test_metadata.iteritems()
            ])

        self.fake_entrypoint.dist.project_name = self.test_project_name
        self.fake_entrypoint.dist.version = self.test_version

        self.manager._entrypoint_iterator = Mock(
            return_value=[self.fake_entrypoint]
        )
        self.manager.load()

    def tearDown(self):
        self.manager.clear_sync_cache()

    def test_added_to_extension_managers(self):
        """An ExtensionManager gets added to the _extension_managers list
           in the djblets.extensions.base module."""
        self.assertTrue(self.manager in _extension_managers)

    def test_get_enabled_extensions_returns_empty(self):
        """An ExtensionManager should return an empty collection when asked
           for the enabled extensions, if there are no extensions currently
           enabled."""
        self.assertEqual(len(self.manager.get_enabled_extensions()), 0)

    def test_load(self):
        """An ExtensionManager should load any extensions that it finds
           registered at entrypoints with its key.  The loaded extension
           should have an ExtensionRegistration and ExtensionInfo attached
           to its class."""
        self.assertEqual(len(self.manager.get_installed_extensions()), 1)
        self.assertTrue(self.extension_class in
            self.manager.get_installed_extensions())
        self.assertTrue(hasattr(self.extension_class, 'info'))
        self.assertEqual(self.extension_class.info.name,
            self.test_project_name)
        self.assertTrue(hasattr(self.extension_class, 'registration'))
        self.assertEqual(self.extension_class.registration.name,
            self.test_project_name)

    def test_load_full_reload_hooks(self):
        """Testing ExtensionManager.load(full_reload=True) with hook registration."""
        self.assertEqual(len(self.manager.get_installed_extensions()), 1)

        extension = self.extension_class(extension_manager=self.manager)
        extension = self.manager.enable_extension(self.extension_class.id)

        URLHook(extension, ())
        self.assertEqual(len(URLHook.hooks), 1)
        self.assertEqual(URLHook.hooks[0].extension, extension)

        self.manager.load(full_reload=True)

        self.assertEqual(len(URLHook.hooks), 0)

    def test_extension_list_sync(self):
        """Testing extension list synchronization cross-process."""
        key = 'extension-list-sync'

        manager1 = ExtensionManager(key)
        manager2 = ExtensionManager(key)

        for manager in (manager1, manager2):
            manager._entrypoint_iterator = Mock(
                return_value=[self.fake_entrypoint]
            )

        manager1.load()
        manager2.load()

        self.assertEqual(len(manager1.get_installed_extensions()), 1)
        self.assertEqual(len(manager2.get_installed_extensions()), 1)
        self.assertEqual(len(manager1.get_enabled_extensions()), 0)
        self.assertEqual(len(manager2.get_enabled_extensions()), 0)

        manager1.enable_extension(self.extension_class.id)
        self.assertEqual(len(manager1.get_enabled_extensions()), 1)
        self.assertEqual(len(manager2.get_enabled_extensions()), 0)

        self.assertFalse(manager1.is_expired())
        self.assertTrue(manager2.is_expired())

        manager2.load(full_reload=True)
        self.assertEqual(len(manager1.get_enabled_extensions()), 1)
        self.assertEqual(len(manager2.get_enabled_extensions()), 1)
        self.assertFalse(manager1.is_expired())
        self.assertFalse(manager2.is_expired())

    def test_extension_settings_sync(self):
        """Testing extension settings synchronization cross-process."""
        key = 'extension-settings-sync'
        setting_key = 'foo'
        setting_val = 'abc123'

        manager1 = ExtensionManager(key)
        manager2 = ExtensionManager(key)

        for manager in (manager1, manager2):
            manager._entrypoint_iterator = Mock(
                return_value=[self.fake_entrypoint]
            )

        manager1.load()

        extension1 = manager1.enable_extension(self.extension_class.id)

        manager2.load()

        self.assertFalse(manager1.is_expired())
        self.assertFalse(manager2.is_expired())

        extension2 = manager2.get_enabled_extension(self.extension_class.id)
        self.assertNotEqual(extension2, None)

        self.assertFalse(setting_key in extension1.settings)
        self.assertFalse(setting_key in extension2.settings)
        extension1.settings[setting_key] = setting_val
        extension1.settings.save()

        self.assertFalse(setting_key in extension2.settings)

        self.assertFalse(manager1.is_expired())
        self.assertTrue(manager2.is_expired())

        manager2.load(full_reload=True)
        extension2 = manager2.get_enabled_extension(self.extension_class.id)

        self.assertFalse(manager1.is_expired())
        self.assertFalse(manager2.is_expired())
        self.assertTrue(setting_key in extension1.settings)
        self.assertTrue(setting_key in extension2.settings)
        self.assertEqual(extension1.settings[setting_key], setting_val)
        self.assertEqual(extension2.settings[setting_key], setting_val)


class URLHookTest(TestCase):
    def setUp(self):
        manager = ExtensionManager('')
        self.test_extension = \
            TestExtensionWithRegistration(extension_manager=manager)
        self.patterns = patterns('',
            (r'^url_hook_test/', include('djblets.extensions.test.urls')))
        self.url_hook = URLHook(self.test_extension, self.patterns)

    def test_urls_appended(self):
        """On initialization, a URLHook should extend its parent URL resolver's
           patterns with the patterns passed into the URLHook."""
        self.assertTrue(set(self.patterns)
            .issubset(set(self.url_hook.dynamic_urls.url_patterns)))
        # And the URLHook should be added to the extension's list of hooks
        self.assertTrue(self.url_hook in self.test_extension.hooks)

    def test_shutdown_removes_urls(self):
        """On shutdown, a URLHook's patterns should no longer be in its
           parent URL resolver's pattern collection."""
        self.url_hook.shutdown()
        self.assertFalse(set(self.patterns)
            .issubset(set(self.url_hook.dynamic_urls.url_patterns)))
        # But the URLHook should still be in the extension's list of hooks
        self.assertTrue(self.url_hook in self.test_extension.hooks)


class TemplateHookTest(TestCase):
    def setUp(self):
        manager = ExtensionManager('')
        self.extension = \
            TestExtensionWithRegistration(extension_manager=manager)
        self.hook_with_applies_name = "template-hook-with-applies-name"
        self.hook_no_applies_name = "template-hook-no-applies-name"
        self.template_hook_no_applies = TemplateHook(self.extension,
            self.hook_no_applies_name, "test_module/some_template.html", [])
        self.template_hook_with_applies = TemplateHook(self.extension,
            self.hook_with_applies_name, "test_module/some_template.html", [
                'test-url-name',
                'url_2',
                'url_3',
            ]
        )

        self.fake_request = Mock()
        self.fake_request._djblets_extensions_kwargs = {}
        self.fake_request.path_info = '/'
        self.context = {
            'request': self.fake_request,
        }

    def test_hook_added_to_class_by_name(self):
        """The TemplateHook should be added to the _by_name collection
           in the TemplateHook class."""
        self.assertTrue(self.template_hook_with_applies in
            self.template_hook_with_applies.__class__
                ._by_name[self.hook_with_applies_name])
        # The TemplateHook should also be added to the Extension's collection
        # of hooks.
        self.assertTrue(self.template_hook_with_applies in
            self.extension.hooks)

    def test_hook_shutdown(self):
        """The TemplateHook should remove itself from the _by_name collection
           in the TemplateHook class if the TemplateHook is shutdown."""
        self.template_hook_with_applies.shutdown()
        self.assertTrue(self.template_hook_with_applies not in
            self.template_hook_with_applies.__class__
               ._by_name[self.hook_with_applies_name])
        # The TemplateHook should still be in the Extension's collection
        # of hooks.
        self.assertTrue(self.template_hook_with_applies in
            self.extension.hooks)

    def test_applies_by_default(self):
        """If a TemplateHook was constructed without an apply_to collection,
           then the applies_to method should automatically return True."""
        self.assertTrue(self.template_hook_no_applies.applies_to(self.context))
        self.assertTrue(self.template_hook_no_applies.applies_to(None))

    def test_applies_with_apply_to(self):
        """If a TemplateHook was constructed with an apply_to collection,
           then the applies_to method should return True if and only if
           the desired URL in the context maps to one of the named URL's
           in the apply_to collection."""
        self.assertTrue(self.template_hook_with_applies
            .applies_to(self.context))

    def test_doesnt_apply_appropriately(self):
        """If a TemplateHook was constructed with an apply_to collection,
           and the desired URL in the context does not map to one of the
           named URL's in the apply_to collection, then the applies_to
           method should return False."""
        self.fake_request.path_info = '/some_other/url'
        self.assertFalse(self.template_hook_with_applies
            .applies_to(self.context))

# A dummy function that acts as a View method
test_view_method = Mock()
