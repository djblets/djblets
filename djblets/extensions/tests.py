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
from django.conf.urls import include, patterns
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
    """Dummy extension for testing."""
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
        """Testing Extension construction"""
        self.assertEqual(type(self.extension.settings), Settings)
        self.assertEqual(self.extension, self.extension.settings.extension)

    def test_shutdown(self):
        """Testing Extension.shutdown"""
        self.extension.shutdown()

        for hook in self.extension.hooks:
            self.assertTrue(hook.shutdown.called)

    def test_get_admin_urlconf(self):
        """Testing Extension with admin URLConfs"""
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
    def test_metadata_from_package(self):
        """Testing ExtensionInfo metadata from package"""
        entrypoint = Mock()
        entrypoint.dist = Mock()

        test_author = 'Test author lorem ipsum'
        test_description = 'Test description lorem ipsum'
        test_email = 'Test author@email.com'
        test_home_page = 'http://www.example.com'
        test_license = 'Test License MIT GPL Apache Drivers'
        test_module_name = 'testextension.dummy.dummy'
        test_module_to_app = 'testextension.dummy'
        test_project_name = 'TestProjectName'
        test_summary = 'Test summary lorem ipsum'
        test_version = '1.0'

        test_htdocs_path = os.path.join(settings.EXTENSIONS_STATIC_ROOT,
                                        test_project_name)

        test_metadata = {
            'Name': test_project_name,
            'Version': test_version,
            'Summary': test_summary,
            'Description': test_description,
            'Author': test_author,
            'Author-email': test_email,
            'License': test_license,
            'Home-page': test_home_page,
        }

        entrypoint.dist.get_metadata_lines = Mock(
            return_value=[
                "%s: %s" % (key, value)
                for key, value in test_metadata.iteritems()
            ])

        entrypoint.dist.project_name = test_project_name
        entrypoint.dist.version = test_version

        ext_class = Mock()
        ext_class.__module__ = test_module_name
        ext_class.metadata = None
        extension_info = ExtensionInfo(entrypoint, ext_class)

        self.assertEqual(extension_info.app_name, test_module_to_app)
        self.assertEqual(extension_info.author, test_author)
        self.assertEqual(extension_info.author_email, test_email)
        self.assertEqual(extension_info.description, test_description)
        self.assertFalse(extension_info.enabled)
        self.assertEqual(extension_info.htdocs_path, test_htdocs_path)
        self.assertFalse(extension_info.installed)
        self.assertEqual(extension_info.license, test_license)
        self.assertEqual(extension_info.metadata, test_metadata)
        self.assertEqual(extension_info.name, test_project_name)
        self.assertEqual(extension_info.summary, test_summary)
        self.assertEqual(extension_info.url, test_home_page)
        self.assertEqual(extension_info.version, test_version)

    def test_custom_metadata(self):
        """Testing ExtensionInfo metadata from Extension.metadata"""
        entrypoint = Mock()
        entrypoint.dist = Mock()

        test_author = 'Test author lorem ipsum'
        test_description = 'Test description lorem ipsum'
        test_email = 'Test author@email.com'
        test_home_page = 'http://www.example.com'
        test_license = 'Test License MIT GPL Apache Drivers'
        test_module_name = 'testextension.dummy.dummy'
        test_module_to_app = 'testextension.dummy'
        test_project_name = 'TestProjectName'
        test_summary = 'Test summary lorem ipsum'
        test_version = '1.0'

        test_htdocs_path = os.path.join(settings.EXTENSIONS_STATIC_ROOT,
                                        'Dummy')

        test_metadata = {
            'Name': test_project_name,
            'Version': test_version,
            'Summary': test_summary,
            'Description': test_description,
            'Author': test_author,
            'Author-email': test_email,
            'License': test_license,
            'Home-page': test_home_page,
        }

        entrypoint.dist.get_metadata_lines = Mock(
            return_value=[
                "%s: %s" % (key, 'Dummy')
                for key, value in test_metadata.iteritems()
            ])

        entrypoint.dist.project_name = 'Dummy'
        entrypoint.dist.version = 'Dummy'

        ext_class = Mock()
        ext_class.__module__ = test_module_name
        ext_class.metadata = test_metadata

        extension_info = ExtensionInfo(entrypoint, ext_class)

        self.assertEqual(extension_info.app_name, test_module_to_app)
        self.assertEqual(extension_info.author, test_author)
        self.assertEqual(extension_info.author_email, test_email)
        self.assertEqual(extension_info.description, test_description)
        self.assertFalse(extension_info.enabled)
        self.assertEqual(extension_info.htdocs_path, test_htdocs_path)
        self.assertFalse(extension_info.installed)
        self.assertEqual(extension_info.license, test_license)
        self.assertEqual(extension_info.metadata, test_metadata)
        self.assertEqual(extension_info.name, test_project_name)
        self.assertEqual(extension_info.summary, test_summary)
        self.assertEqual(extension_info.url, test_home_page)
        self.assertEqual(extension_info.version, test_version)


class TestExtensionHook(ExtensionHook):
    """A dummy ExtensionHook to test with"""
    __metaclass__ = ExtensionHookPoint


class ExtensionHookTest(TestCase):
    def setUp(self):
        manager = ExtensionManager('')
        self.extension = \
            TestExtensionWithRegistration(extension_manager=manager)
        self.extension_hook = TestExtensionHook(self.extension)

    def test_registration(self):
        """Testing ExtensionHook registration"""
        self.assertEqual(self.extension, self.extension_hook.extension)
        self.assertTrue(self.extension_hook in self.extension.hooks)
        self.assertTrue(self.extension_hook in
                        self.extension_hook.__class__.hooks)

    def test_shutdown(self):
        """Testing ExtensionHook.shutdown"""
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
        """Testing ExtensionHookPoint.hooks"""
        self.assertTrue(hasattr(self.extension_hook_class, "hooks"))

    def test_add_hook(self):
        """Testing ExtensionHookPoint.add_hook"""
        self.assertTrue(self.dummy_hook in self.extension_hook_class.hooks)

    def test_remove_hook(self):
        """Testing ExtensionHookPoint.remove_hook"""
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
            'Name': self.test_project_name,
            'Version': self.test_version,
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
        """Testing ExtensionManager registration"""
        self.assertTrue(self.manager in _extension_managers)

    def test_get_enabled_extensions_returns_empty(self):
        """Testing ExtensionManager.get_enabled_extensions with no extensions"""
        self.assertEqual(len(self.manager.get_enabled_extensions()), 0)

    def test_load(self):
        """Testing ExtensionManager.get_installed_extensions with loaded extensions"""
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
        """Testing ExtensionManager.load with full_reload=True"""
        self.assertEqual(len(self.manager.get_installed_extensions()), 1)

        extension = self.extension_class(extension_manager=self.manager)
        extension = self.manager.enable_extension(self.extension_class.id)

        URLHook(extension, ())
        self.assertEqual(len(URLHook.hooks), 1)
        self.assertEqual(URLHook.hooks[0].extension, extension)

        self.manager.load(full_reload=True)

        self.assertEqual(len(URLHook.hooks), 0)

    def test_extension_list_sync(self):
        """Testing ExtensionManager extension list synchronization cross-process."""
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
        """Testing ExtensionManager extension settings synchronization cross-process."""
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

    def test_url_registration(self):
        """Testing URLHook URL registration"""
        self.assertTrue(set(self.patterns)
            .issubset(set(self.url_hook.dynamic_urls.url_patterns)))
        # And the URLHook should be added to the extension's list of hooks
        self.assertTrue(self.url_hook in self.test_extension.hooks)

    def test_shutdown_removes_urls(self):
        """Testing URLHook.shutdown"""
        # On shutdown, a URLHook's patterns should no longer be in its
        # parent URL resolver's pattern collection.
        self.url_hook.shutdown()
        self.assertFalse(
            set(self.patterns).issubset(
                set(self.url_hook.dynamic_urls.url_patterns)))

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
        """Testing TemplateHook registration"""
        self.assertTrue(self.template_hook_with_applies in
                        self.template_hook_with_applies.__class__
                            ._by_name[self.hook_with_applies_name])

        # The TemplateHook should also be added to the Extension's collection
        # of hooks.
        self.assertTrue(self.template_hook_with_applies in
                        self.extension.hooks)

    def test_hook_shutdown(self):
        """Testing TemplateHook shutdown"""
        self.template_hook_with_applies.shutdown()
        self.assertTrue(self.template_hook_with_applies not in
                        self.template_hook_with_applies.__class__
                            ._by_name[self.hook_with_applies_name])

        # The TemplateHook should still be in the Extension's collection
        # of hooks.
        self.assertTrue(self.template_hook_with_applies in
                        self.extension.hooks)

    def test_applies_to_default(self):
        """Testing TemplateHook.applies_to defaults to everything"""
        self.assertTrue(self.template_hook_no_applies.applies_to(self.context))
        self.assertTrue(self.template_hook_no_applies.applies_to(None))

    def test_applies_to(self):
        """Testing TemplateHook.applies_to customization"""
        self.fake_request.path_info = '/some_other/url'
        self.assertFalse(
            self.template_hook_with_applies.applies_to(self.context))

# A dummy function that acts as a View method
test_view_method = Mock()
