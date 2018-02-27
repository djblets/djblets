#
# tests.py -- Unit tests for extensions.
#
# Copyright (c) 2010-2013  Beanbag, Inc.
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

from __future__ import unicode_literals

import logging
import os
import shutil
import threading
import time
import warnings

import nose
from django import forms
from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.dispatch import Signal
from django.template import (Context, RequestContext, Template,
                             TemplateSyntaxError)
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.utils import six
from django.utils.six.moves import cPickle as pickle
from kgb import SpyAgency
from mock import Mock
from pipeline.conf import settings as pipeline_settings

try:
    # Django >= 1.6, <= 1.8
    from django.template.base import get_templatetags_modules
except ImportError:
    # Django >= 1.9
    get_templatetags_modules = None

from djblets.datagrid.grids import Column, DataGrid
from djblets.extensions.extension import Extension, ExtensionInfo
from djblets.extensions.forms import SettingsForm
from djblets.extensions.hooks import (DataGridColumnsHook, ExtensionHook,
                                      ExtensionHookPoint, BaseRegistryHook,
                                      BaseRegistryMultiItemHook, SignalHook,
                                      TemplateHook, URLHook)
from djblets.extensions.manager import (ExtensionManager, SettingListWrapper,
                                        get_extension_managers)
from djblets.extensions.settings import Settings
from djblets.extensions.signals import settings_saved
from djblets.extensions.views import configure_extension
from djblets.registries.errors import AlreadyRegisteredError
from djblets.registries.registry import Registry
from djblets.testing.testcases import TestCase


class FakeEntryPoint(object):
    """A fake entry point.

    This is modelled after :py:class:`pkg_resources.EntryPoint`.
    """

    def __init__(self, value, **metadata_kwargs):
        """Initialize the FakeEntryPoint.

        Args:
            value (object):
                The value to be returned when the entry point is loaded.

            **metadata_kwargs (dict):
                Keyword arguments to pass to the associated
                :py:class:`FakeDistribution` constructor.
        """
        self._value = value
        self.dist = FakeDistribution(**metadata_kwargs)

    def load(self):
        """Load the entry point.

        Returns:
            object: The value specified at initialization time.
        """
        return self._value


class FakeDistribution(object):
    """A fake distribution.

    This is modelled after :py:class`pkg_resources.Distribution`.
    """

    def __init__(self, author='Example Author',
                 author_email='author@example.com',
                 description='Test description',
                 home_page='http://example.com',
                 project_name='ExampleProject', license_name='Drivers',
                 summary='Test summary', version='1.0'):
        """Initialize the FakeDistribution.

        Args:
            author (unicode):
                The package author.

            author_email (unicode):
                The package author's e-mail address.

            description (unicode):
                The package description.

            home_page (unicode):
                The package's URL.

            project_name (unicode):
                The package's name.

            license_name (unicode):
                The name of the package license.

            summary (unicode):
                The package summary.
        """
        self.metadata = {
            'Author': author,
            'Author-email': author_email,
            'Description': description,
            'Home-page': home_page,
            'Name': project_name,
            'License': license_name,
            'Summary': summary,
            'Version': version,
        }

    def get_metadata_lines(self, *args):
        """Return the metadata lines.

        Returns:
            list:
            A list of the package metadata lines, as :py:class:`unicode`
            objects.
        """
        return [
            '%s: %s' % (field_name, value)
            for field_name, value in six.iteritems(self.metadata)
        ]

    @property
    def project_name(self):
        """The project name.

        Returns:
            unicode:
            The project name.
        """
        return self.metadata['Name']

    @property
    def version(self):
        """The project version.

        Returns:
            unicode:
            The project version.
        """
        return self.metadata['version']


class TestExtensionManager(ExtensionManager):
    """An extension manager for testing.

    The entry points are provided at initialization time.
    """

    def __init__(self, entry_points=None, *args, **kwargs):
        """Initialize the TestExtensionManager.

        Args:
            entry_points (list):
                A list of :py:class:`FakeEntryPoint`s.

            *args (tuple):
                Additional positional arguments to pass to the base class'
                constructor.

            **kwargs (dict):
                Additional keyword arguments to pass to the base class'
                constructor.
        """
        super(TestExtensionManager, self).__init__(*args, **kwargs)
        self._entry_points = entry_points or []

    def _entrypoint_iterator(self):
        """Return the entry points.

        Returns:
            list: The entry points.
        """
        return self._entry_points


class ExtensionTestsMixin(object):
    """Mixin for Djblets extension-related unit tests.

    This is used to help set up an extension and extension manager to test
    with.

    This shouldn't generally be used by third-parties writing unit tests for
    their extensions. For those, see
    :py:mod:`djblets.extensions.testing.testcases`.
    """

    #: The project name to use in the entrypoint.
    test_project_name = 'TestProject'

    def setUp(self):
        """Set up state before a test run."""
        super(ExtensionTestsMixin, self).setUp()

        self.manager = None

    def tearDown(self):
        """Tear down state after a test run.

        This will properly ensure that the extension manager, if one was
        created, will clear all state and shut down.
        """
        super(ExtensionTestsMixin, self).tearDown()

        if self.manager:
            self.manager.clear_sync_cache()
            self.manager.shutdown()

    def setup_extension(self, extension_cls, enable=True, manager_key='tests'):
        """Set up an extension for use in a test.

        This will register the class in a new extension manager and then
        enable or otherwise instantiate the extension, returning the instance.

        Args:
            extension_cls (type):
                The extension class to register.

            enable (bool, optional):
                Whether the returned extension should be enabled.

            manager_key (unicode, optional):
                The key to use for the extension manager.

        Returns:
            djblets.extensions.extension.Extension:
            The resulting extension instance.
        """
        fake_entry_point = FakeEntryPoint(extension_cls,
                                          project_name=self.test_project_name)

        self.manager = TestExtensionManager([fake_entry_point], manager_key)
        self.manager.load()

        if enable:
            return self.manager.enable_extension(extension_cls.id)
        else:
            return extension_cls(self.manager)


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

    def test_save_emits_settings_saved_signal(self):
        """Testing that Settings.save emits the settings_saved signal"""
        saw = {}

        def on_settings_saved(*args, **kwargs):
            saw['signal'] = True

        settings_saved.connect(on_settings_saved, sender=self.extension)

        self.settings['test_new_key'] = 'Test new value'
        self.settings.save()

        self.assertIn('signal', saw)


class TestExtensionWithRegistration(Extension):
    """Dummy extension for testing."""
    id = 'TestExtensionWithRegistration'
    registration = Mock()
    registration.settings = dict()


@six.add_metaclass(ExtensionHookPoint)
class DummyHook(ExtensionHook):
    def initialize(self):
        self.foo = [1]

    def shutdown(self):
        self.foo.pop()


class ExtensionTest(SpyAgency, ExtensionTestsMixin, TestCase):
    def test_extension_constructor(self):
        """Testing Extension construction"""
        class TestExtension(Extension):
            pass

        extension = self.setup_extension(TestExtension)

        self.assertEqual(type(extension.settings), Settings)
        self.assertEqual(extension, extension.settings.extension)

    def test_shutdown(self):
        """Testing Extension.shutdown"""
        class TestExtension(Extension):
            def initialize(self):
                for index in range(0, 5):
                    DummyHook(self)

        extension = self.setup_extension(TestExtension)

        for hook in extension.hooks:
            self.spy_on(hook.shutdown)

        extension.shutdown()

        for hook in extension.hooks:
            self.assertTrue(hook.shutdown.called)

    def test_shutdown_twice(self):
        """Testing Extension.shutdown when called twice"""
        class TestExtension(Extension):
            def initialize(self):
                for index in range(0, 5):
                    DummyHook(self)

        extension = self.setup_extension(TestExtension)

        for hook in extension.hooks:
            self.spy_on(hook.shutdown)

        extension.shutdown()

        for hook in extension.hooks:
            self.assertTrue(hook.shutdown.called)
            hook.shutdown.reset_calls()

        extension.shutdown()

        for hook in extension.hooks:
            self.assertFalse(hook.shutdown.called)

    def test_admin_urlconf(self):
        """Testing Extension with admin URLConfs"""
        class TestExtension(Extension):
            __module__ = 'djblets.extensions.test.test'

        extension = self.setup_extension(TestExtension, enable=False)

        try:
            extension.admin_urlconf
        except ImproperlyConfigured:
            self.fail('Should have loaded admin_urls.py')


class ExtensionInfoTests(TestCase):
    def test_create_from_entrypoint(self):
        """Testing ExtensionInfo.create_from_entrypoint"""
        module_name = 'test_extension.dummy.submodule'
        package_name = 'DummyExtension'
        extension_id = '%s:DummyExtension' % module_name

        class TestExtension(Extension):
            __module__ = module_name
            id = extension_id

        entrypoint = FakeEntryPoint(TestExtension, project_name=package_name)
        extension_info = ExtensionInfo.create_from_entrypoint(entrypoint,
                                                              TestExtension)

        self._check_extension_info(extension_info=extension_info,
                                   app_name='test_extension.dummy',
                                   package_name=package_name,
                                   extension_id=extension_id,
                                   metadata=entrypoint.dist.metadata)

    def test_create_from_entrypoint_with_custom_metadata(self):
        """Testing ExtensionInfo.create_from_entrypoint with custom
        Extension.metadata
        """
        package_name = 'DummyExtension'
        module_name = 'test_extension.dummy.submodule'
        extension_id = '%s:DummyExtension' % module_name

        class TestExtension(Extension):
            __module__ = module_name
            id = extension_id
            metadata = {
                'Name': 'OverrideName',
                'Version': '3.14159',
                'Summary': 'Lorem ipsum dolor sit amet.',
                'Description': 'Tempus fugit.',
                'License': 'None',
                'Home-page': 'http://127.0.0.1/',
            }

        entrypoint = FakeEntryPoint(TestExtension, project_name=package_name)
        extension_info = ExtensionInfo.create_from_entrypoint(entrypoint,
                                                              TestExtension)

        expected_metadata = entrypoint.dist.metadata.copy()
        expected_metadata.update(TestExtension.metadata)

        self._check_extension_info(extension_info=extension_info,
                                   app_name='test_extension.dummy',
                                   package_name=package_name,
                                   extension_id=extension_id,
                                   metadata=expected_metadata)

    def test_deprecated_entrypoint_in_init(self):
        """Testing ExtensionInfo.__init__ with deprecated entrypoint support"""
        module_name = 'test_extension.dummy.submodule'
        package_name = 'DummyExtension'
        extension_id = '%s:DummyExtension' % module_name

        class TestExtension(Extension):
            __module__ = module_name
            id = extension_id

        entrypoint = FakeEntryPoint(TestExtension, project_name=package_name)

        with warnings.catch_warnings(record=True) as w:
            extension_info = ExtensionInfo(entrypoint, TestExtension)

            self.assertEqual(six.text_type(w[0].message),
                             'ExtensionInfo.__init__() no longer accepts an '
                             'EntryPoint. Please update your code to call '
                             'ExtensionInfo.create_from_entrypoint() instead.')

        self._check_extension_info(extension_info=extension_info,
                                   app_name='test_extension.dummy',
                                   package_name=package_name,
                                   extension_id=extension_id,
                                   metadata=entrypoint.dist.metadata)

    def _check_extension_info(self, extension_info, app_name, package_name,
                              extension_id, metadata):
        htdocs_path = os.path.join(settings.MEDIA_ROOT, 'ext', package_name)
        static_path = os.path.join(settings.STATIC_ROOT, 'ext', extension_id)

        self.assertEqual(extension_info.app_name, app_name)
        self.assertEqual(extension_info.author, metadata['Author'])
        self.assertEqual(extension_info.author_email, metadata['Author-email'])
        self.assertEqual(extension_info.description, metadata['Description'])
        self.assertFalse(extension_info.enabled)
        self.assertEqual(extension_info.installed_htdocs_path, htdocs_path)
        self.assertEqual(extension_info.installed_static_path, static_path)
        self.assertFalse(extension_info.installed)
        self.assertEqual(extension_info.license, metadata['License'])
        self.assertEqual(extension_info.metadata, metadata)
        self.assertEqual(extension_info.name, metadata['Name'])
        self.assertEqual(extension_info.package_name, package_name)
        self.assertEqual(extension_info.summary, metadata['Summary'])
        self.assertEqual(extension_info.url, metadata['Home-page'])
        self.assertEqual(extension_info.version, metadata['Version'])


@six.add_metaclass(ExtensionHookPoint)
class TestExtensionHook(ExtensionHook):
    """A dummy ExtensionHook to test with"""


class ExtensionHookTest(ExtensionTestsMixin, TestCase):
    def setUp(self):
        class TestExtension(Extension):
            pass

        super(ExtensionHookTest, self).setUp()

        self.extension = self.setup_extension(TestExtension)

    def test_init_hook_states(self):
        """Testing ExtensionHook enabling hook states"""
        @six.add_metaclass(ExtensionHookPoint)
        class InitTestHook(ExtensionHook):
            def initialize(hook):
                self.assertFalse(hook.initialized)
                self.assertEqual(hook.hook_state,
                                 ExtensionHook.HOOK_STATE_ENABLING)

        hook = InitTestHook(self.extension)
        self.assertEqual(hook.hook_state, ExtensionHook.HOOK_STATE_ENABLED)
        self.assertTrue(hook.initialized)

    def test_disable_hook_states(self):
        """Testing ExtensionHook disabling states"""
        @six.add_metaclass(ExtensionHookPoint)
        class InitTestHook(ExtensionHook):
            def shutdown(hook):
                self.assertFalse(hook.initialized)
                self.assertEqual(hook.hook_state,
                                 ExtensionHook.HOOK_STATE_DISABLING)

        hook = InitTestHook(self.extension)
        hook.disable_hook()
        self.assertEqual(hook.hook_state, ExtensionHook.HOOK_STATE_DISABLED)
        self.assertFalse(hook.initialized)

    def test_init_with_start_enabled_false(self):
        """Testing ExtensionHook construction with start_enabled=False"""
        @six.add_metaclass(ExtensionHookPoint)
        class InitTestHook(ExtensionHook):
            def initialize(hook):
                self.fail('initialize() should not have been reached')

        hook = InitTestHook(self.extension, start_enabled=False)
        self.assertEqual(hook.hook_state, ExtensionHook.HOOK_STATE_DISABLED)
        self.assertFalse(hook.initialized)

    def test_registration(self):
        """Testing ExtensionHook registration"""
        extension_hook = TestExtensionHook(self.extension)

        self.assertEqual(self.extension, extension_hook.extension)
        self.assertIn(extension_hook, self.extension.hooks)
        self.assertIn(extension_hook, extension_hook.__class__.hooks)

    def test_shutdown(self):
        """Testing ExtensionHook.shutdown"""
        extension_hook = TestExtensionHook(self.extension)
        extension_hook.disable_hook()

        self.assertNotIn(extension_hook, extension_hook.__class__.hooks)


class ExtensionHookPointTest(ExtensionTestsMixin, TestCase):
    def setUp(self):
        class TestExtension(Extension):
            pass

        super(ExtensionHookPointTest, self).setUp()

        self.extension = self.setup_extension(TestExtension)
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


class ExtensionManagerTest(SpyAgency, ExtensionTestsMixin, TestCase):
    def test_added_to_extension_managers(self):
        """Testing ExtensionManager registration"""
        self.manager = TestExtensionManager([], '')
        self.assertIn(self.manager, get_extension_managers())

    def test_get_enabled_extensions_returns_empty(self):
        """Testing ExtensionManager.get_enabled_extensions with no
        extensions
        """
        self.manager = TestExtensionManager([], '')
        self.manager.load()

        self.assertEqual(len(self.manager.get_enabled_extensions()), 0)

    def test_load(self):
        """Testing ExtensionManager.get_installed_extensions with loaded
        extensions
        """
        class TestExtension(Extension):
            pass

        self.setup_extension(TestExtension, enable=False)

        self.assertEqual(self.manager.get_installed_extensions(),
                         [TestExtension])
        self.assertEqual(len(self.manager.get_enabled_extensions()), 0)
        self.assertTrue(hasattr(TestExtension, 'info'))
        self.assertEqual(TestExtension.info.name, self.test_project_name)
        self.assertTrue(hasattr(TestExtension, 'registration'))
        self.assertEqual(TestExtension.registration.name,
                         self.test_project_name)

    def test_load_full_reload_hooks(self):
        """Testing ExtensionManager.load with full_reload=True"""
        class TestExtension(Extension):
            pass

        extension = self.setup_extension(TestExtension)

        self.assertEqual(len(self.manager.get_installed_extensions()), 1)
        self.assertEqual(len(self.manager.get_enabled_extensions()), 1)

        URLHook(extension, ())
        self.assertEqual(len(URLHook.hooks), 1)
        self.assertEqual(URLHook.hooks[0].extension, extension)

        self.manager.load(full_reload=True)

        self.assertEqual(len(URLHook.hooks), 0)

    def test_load_concurrent_threads(self):
        """Testing ExtensionManager.load with concurrent threads"""
        # There are a number of things that could go wrong both during
        # uninitialization and during initialization of extensions, if
        # two threads attempt to reload at the same time and locking isn't
        # properly implemented.
        #
        # Extension uninit could be called twice, resulting in one thread
        # attempting to access state that's already been destroyed. We
        # could end up hitting:
        #
        #     "Extension's installed app <app> is missing a ref count."
        #     "'<Extension>' object has no attribute 'info'."
        #
        # (Without locking, we end up hitting the latter in this test.)
        #
        # If an extension is being initialized twice simultaneously, then
        # it can hit other errors. An easy one to hit is this assertion:
        #
        #     assert extension_id not in self._extension_instances
        #
        # With proper locking, these issues don't come up. That's what
        # this test case is attempting to check for.

        # Enable one extension. This extension's state will get a bit messed
        # up if the thread locking fails. We only need one to trigger this.
        class TestExtension(Extension):
            pass

        self.setup_extension(TestExtension)

        self.spy_on(self.manager._load_extensions)
        self._spy_sleep_and_call(self.manager._init_extension)
        self._spy_sleep_and_call(self.manager._uninit_extension)

        self._run_thread_test(lambda: self.manager.load(full_reload=True))

        self.assertEqual(len(self.manager._load_extensions.calls), 2)
        self.assertEqual(len(self.manager._uninit_extension.calls), 2)
        self.assertEqual(len(self.manager._init_extension.calls), 2)
        self.assertEqual(self.exceptions, [])

    @override_settings(EXTENSIONS_ENABLED_BY_DEFAULT=[
        'djblets.extensions.tests.TestExtension',
    ])
    def test_load_with_enabled_by_default(self):
        """Testing ExtensionManager.load with
        settings.EXTENSIONS_ENABLED_BY_DEFAULT
        """
        class TestExtension(Extension):
            pass

        self.setup_extension(TestExtension, enable=False)

        self.assertEqual(self.manager.get_installed_extensions(),
                         [TestExtension])

        enabled_extensions = self.manager.get_enabled_extensions()
        self.assertEqual(len(enabled_extensions), 1)
        self.assertIsInstance(enabled_extensions[0], TestExtension)

        self.assertTrue(hasattr(TestExtension, 'info'))
        self.assertEqual(TestExtension.info.name, self.test_project_name)
        self.assertIsNotNone(TestExtension.instance)
        self.assertTrue(hasattr(TestExtension, 'registration'))
        self.assertEqual(TestExtension.registration.name,
                         self.test_project_name)
        self.assertTrue(TestExtension.registration.enabled)

    def test_sync_database_with_no_settings_version(self):
        """Testing ExtensionManager synchronizes database when no version
        found in settings (new install)
        """
        class TestExtension(Extension):
            pass

        extension = self.setup_extension(TestExtension, enable=False)
        extension.registration.installed = True
        extension.registration.save()

        self.assertNotIn(self.manager.VERSION_SETTINGS_KEY, extension.settings)

        self.spy_on(self.manager._sync_database, call_original=False)

        extension = self.manager.enable_extension(TestExtension.id)

        self.assertTrue(extension.registration.installed)
        self.assertTrue(self.manager._sync_database.called)
        self.assertIn(self.manager.VERSION_SETTINGS_KEY, extension.settings)
        self.assertEqual(extension.settings[self.manager.VERSION_SETTINGS_KEY],
                         extension.info.version)

    def test_sync_database_with_old_settings_version(self):
        """Testing ExtensionManager synchronizes database when old version
        found in settings (upgrade)
        """
        class TestExtension(Extension):
            pass

        extension = self.setup_extension(TestExtension, enable=False)
        extension.registration.installed = True
        extension.registration.save()

        self.assertNotIn(self.manager.VERSION_SETTINGS_KEY, extension.settings)
        extension.settings.set(self.manager.VERSION_SETTINGS_KEY, '0.5')
        extension.settings.save()

        self.spy_on(self.manager._sync_database, call_original=False)

        extension = self.manager.enable_extension(TestExtension.id)

        self.assertTrue(extension.registration.installed)
        self.assertTrue(self.manager._sync_database.called)
        self.assertIn(self.manager.VERSION_SETTINGS_KEY, extension.settings)
        self.assertEqual(extension.settings[self.manager.VERSION_SETTINGS_KEY],
                         extension.info.version)

    def test_sync_database_with_current_settings_version(self):
        """Testing ExtensionManager doesn't synchronize database when current
        version found in settings
        """
        class TestExtension(Extension):
            pass

        extension = self.setup_extension(TestExtension, enable=False)
        extension.registration.installed = True
        extension.registration.save()

        self.assertNotIn(self.manager.VERSION_SETTINGS_KEY, extension.settings)
        extension.settings.set(self.manager.VERSION_SETTINGS_KEY,
                               extension.info.version)
        extension.settings.save()

        self.spy_on(self.manager._sync_database, call_original=False)

        extension = self.manager.enable_extension(TestExtension.id)

        self.assertTrue(extension.registration.installed)
        self.assertFalse(self.manager._sync_database.called)
        self.assertIn(self.manager.VERSION_SETTINGS_KEY, extension.settings)
        self.assertEqual(extension.settings[self.manager.VERSION_SETTINGS_KEY],
                         extension.info.version)

    def test_sync_database_with_newer_settings_version(self):
        """Testing ExtensionManager doesn't synchronize database when newer
        version found in settings (downgrade)
        """
        class TestExtension(Extension):
            pass

        extension = self.setup_extension(TestExtension, enable=False)
        extension.registration.installed = True
        extension.registration.save()

        self.assertNotIn(self.manager.VERSION_SETTINGS_KEY, extension.settings)
        extension.settings.set(self.manager.VERSION_SETTINGS_KEY, '100.0')
        extension.settings.save()

        self.spy_on(self.manager._sync_database, call_original=False)
        self.spy_on(logging.warning)

        extension = self.manager.enable_extension(TestExtension.id)

        self.assertTrue(extension.registration.installed)
        self.assertFalse(self.manager._sync_database.called)
        self.assertIn(self.manager.VERSION_SETTINGS_KEY, extension.settings)
        self.assertEqual(extension.settings[self.manager.VERSION_SETTINGS_KEY],
                         '100.0')
        self.assertIn('is older than the version recorded',
                      logging.warning.spy.calls[-1].args[0])

    def test_install_extension_media_with_no_version_file(self):
        """Testing ExtensionManager installs media when no version file exists
        in the media directory (new install or upgrade from pre-version file)
        """
        class TestExtension(Extension):
            pass

        extension = self.setup_extension(TestExtension, enable=False)
        extension.registration.installed = True
        extension.registration.enabled = True
        extension.registration.save()
        TestExtension.instance = extension

        # Re-create the directories.
        shutil.rmtree(extension.info.installed_static_path)
        os.mkdir(extension.info.installed_static_path, 0755)

        self.manager.should_install_static_media = True

        self.spy_on(self.manager.install_extension_media)
        self.spy_on(self.manager._install_extension_media_internal,
                    call_original=False)

        # Fake the current version being installed.
        version_filename = os.path.join(extension.info.installed_static_path,
                                        '.version')
        self.assertFalse(os.path.exists(version_filename))

        # Enable the extension. We shouldn't install anything.
        extension = self.manager.enable_extension(TestExtension.id)
        self.assertTrue(extension.registration.installed)

        self.assertEqual(len(self.manager.install_extension_media.calls), 1)
        self.assertEqual(
            len(self.manager._install_extension_media_internal.calls), 1)

        with open(version_filename, 'r') as fp:
            self.assertEqual(fp.read().strip(), extension.info.version)

    def test_install_extension_media_with_outdated_version(self):
        """Testing ExtensionManager installs media when version file is
        older than the current version (upgrade)
        """
        class TestExtension(Extension):
            pass

        extension = self.setup_extension(TestExtension, enable=False)
        extension.registration.installed = True
        extension.registration.enabled = True
        extension.registration.save()
        TestExtension.instance = extension

        # Re-create the directories.
        shutil.rmtree(extension.info.installed_static_path)
        os.mkdir(extension.info.installed_static_path, 0755)

        self.manager.should_install_static_media = True

        self.spy_on(self.manager.install_extension_media)
        self.spy_on(self.manager._install_extension_media_internal,
                    call_original=False)

        # Fake the current version being installed.
        version_filename = os.path.join(extension.info.installed_static_path,
                                        '.version')

        with open(version_filename, 'w') as fp:
            fp.write('0.5\n')

        # Enable the extension. We shouldn't install anything.
        extension = self.manager.enable_extension(TestExtension.id)
        self.assertTrue(extension.registration.installed)

        self.assertEqual(len(self.manager.install_extension_media.calls), 1)
        self.assertEqual(
            len(self.manager._install_extension_media_internal.calls), 1)

        with open(version_filename, 'r') as fp:
            self.assertEqual(fp.read().strip(), extension.info.version)

    def test_install_extension_media_with_newer_version(self):
        """Testing ExtensionManager installs media when version file is
        newer than the current version (downgrade)
        """
        class TestExtension(Extension):
            pass

        extension = self.setup_extension(TestExtension, enable=False)
        extension.registration.installed = True
        extension.registration.enabled = True
        extension.registration.save()
        TestExtension.instance = extension

        # Re-create the directories.
        shutil.rmtree(extension.info.installed_static_path)
        os.mkdir(extension.info.installed_static_path, 0755)

        self.manager.should_install_static_media = True

        self.spy_on(self.manager.install_extension_media)
        self.spy_on(self.manager._install_extension_media_internal,
                    call_original=False)

        # Fake the current version being installed.
        version_filename = os.path.join(extension.info.installed_static_path,
                                        '.version')

        with open(version_filename, 'w') as fp:
            fp.write('100.0\n')

        # Enable the extension. We shouldn't install anything.
        extension = self.manager.enable_extension(TestExtension.id)
        self.assertTrue(extension.registration.installed)

        self.assertEqual(len(self.manager.install_extension_media.calls), 1)
        self.assertEqual(
            len(self.manager._install_extension_media_internal.calls), 1)

        with open(version_filename, 'r') as fp:
            self.assertEqual(fp.read().strip(), extension.info.version)

    def test_install_media_concurrent_threads(self):
        """Testing ExtensionManager installs media safely with multiple
        threads
        """
        class TestExtension(Extension):
            pass

        # Manually mark the extension as installed and enabled without going
        # through the enable process, since we don't want to trigger any
        # static media saving yet.
        extension = self.setup_extension(TestExtension, enable=False)
        extension.registration.installed = True
        extension.registration.enabled = True
        extension.registration.save()
        TestExtension.instance = extension

        # Clear out the old directory, if it exists.
        shutil.rmtree(extension.info.installed_static_path)

        self.manager.should_install_static_media = True

        self.assertEqual(len(self.manager.get_installed_extensions()), 1)

        self.spy_on(self.manager.install_extension_media)
        self.spy_on(self.manager._install_extension_media_internal,
                    call_original=False)

        # Simulate numerous simultaneous attempts at installing static media.
        self._run_thread_test(
            lambda: self.manager.install_extension_media(extension.__class__))

        self.assertEqual(
            len(self.manager.install_extension_media.calls), 2)
        self.assertEqual(
            len(self.manager._install_extension_media_internal.calls), 1)
        self.assertEqual(self.exceptions, [])

        version_filename = os.path.join(extension.info.installed_static_path,
                                        '.version')

        with open(version_filename, 'r') as fp:
            self.assertEqual(fp.read().strip(), extension.info.version)

    def test_install_extension_media_with_current_version(self):
        """Testing ExtensionManager doesn't install media when version file
        matches current version
        """
        class TestExtension(Extension):
            pass

        extension = self.setup_extension(TestExtension, enable=False)
        extension.registration.installed = True
        extension.registration.enabled = True
        extension.registration.save()
        TestExtension.instance = extension

        # Re-create the directories.
        shutil.rmtree(extension.info.installed_static_path)
        os.mkdir(extension.info.installed_static_path, 0755)

        self.manager.should_install_static_media = True

        self.spy_on(self.manager.install_extension_media)
        self.spy_on(self.manager._install_extension_media_internal,
                    call_original=False)

        # Fake the current version being installed.
        version_filename = os.path.join(extension.info.installed_static_path,
                                        '.version')

        with open(version_filename, 'w') as fp:
            fp.write('%s\n' % extension.info.version)

        # Enable the extension. We shouldn't install anything.
        extension = self.manager.enable_extension(TestExtension.id)
        self.assertTrue(extension.registration.installed)

        self.assertEqual(len(self.manager.install_extension_media.calls), 1)
        self.assertEqual(
            len(self.manager._install_extension_media_internal.calls), 0)

        with open(version_filename, 'r') as fp:
            self.assertEqual(fp.read().strip(), extension.info.version)

    def test_enable_extension_registers_static_bundles(self):
        """Testing ExtensionManager.enable_extension registers static bundles
        """
        class TestExtension(Extension):
            css_bundles = {
                'default': {
                    'source_filenames': ['test.css'],
                }
            }

            js_bundles = {
                'default': {
                    'source_filenames': ['test.js'],
                }
            }

        pipeline_settings.STYLESHEETS = {}
        pipeline_settings.JAVASCRIPT = {}

        extension = self.setup_extension(TestExtension)

        self.assertEqual(len(pipeline_settings.STYLESHEETS), 1)
        self.assertEqual(len(pipeline_settings.JAVASCRIPT), 1)

        key = '%s-default' % extension.id
        self.assertIn(key, pipeline_settings.STYLESHEETS)
        self.assertIn(key, pipeline_settings.JAVASCRIPT)

        css_bundle = pipeline_settings.STYLESHEETS[key]
        js_bundle = pipeline_settings.JAVASCRIPT[key]

        self.assertIn('source_filenames', css_bundle)
        self.assertEqual(css_bundle['source_filenames'],
                         ['ext/%s/test.css' % extension.id])

        self.assertIn('output_filename', css_bundle)
        self.assertEqual(css_bundle['output_filename'],
                         'ext/%s/css/default.min.css' % extension.id)

        self.assertIn('source_filenames', js_bundle)
        self.assertEqual(js_bundle['source_filenames'],
                         ['ext/%s/test.js' % extension.id])

        self.assertIn('output_filename', js_bundle)
        self.assertEqual(js_bundle['output_filename'],
                         'ext/%s/js/default.min.js' % extension.id)

    def test_enable_extension_registers_context_processors(self):
        """Testing ExtensionManager.enable_extension registers template
        context processors
        """
        class TestExtension(Extension):
            context_processors = ['my_custom_processor']

        # Back up the list, so we can replace it later.
        if hasattr(settings, 'TEMPLATES'):
            orig_context_processors_list = \
                list(settings.TEMPLATES[0]['OPTIONS']['context_processors'])
        else:
            orig_context_processors_list = \
                list(settings.TEMPLATE_CONTEXT_PROCESSORS)

        # Sanity-check that the context processor didn't wind up in here.
        self.assertNotIn('my_custom_processor', orig_context_processors_list)

        try:
            extension = self.setup_extension(TestExtension)

            # We have to re-fetch these lists now, since they may have
            # been normalized to lists.
            if hasattr(settings, 'TEMPLATES'):
                context_processors_list = \
                    settings.TEMPLATES[0]['OPTIONS']['context_processors']
            else:
                context_processors_list = \
                    settings.TEMPLATE_CONTEXT_PROCESSORS

            # This should have been added, since the extension was enabled.
            self.assertIn('my_custom_processor', context_processors_list)

            # Shutting down the extension should remove the context
            # processor.
            self.manager.disable_extension(extension.id)
            self.assertNotIn('my_custom_processor',
                             context_processors_list)
        finally:
            if hasattr(settings, 'TEMPLATES'):
                settings.TEMPLATES[0]['OPTIONS']['context_processors'] = \
                    orig_context_processors_list
            else:
                settings.TEMPLATE_CONTEXT_PROCESSORS = \
                    orig_context_processors_list

    def test_enable_extension_registers_template_tags(self):
        """Testing ExtensionManager.enable_extension registers template tags"""
        class TestExtension(Extension):
            __module__ = 'djblets.extensions.test.templatetag_tests.__init__'

        templatetags_module = \
            'djblets.extensions.test.templatetag_tests.templatetags'

        def _check_state(enabled):
            if enabled:
                if get_templatetags_modules:
                    self.assertIn(templatetags_module,
                                  get_templatetags_modules())

                self.assertEqual(
                    Template(template_str).render(Context({})),
                    'Hello, world!')
            else:
                if get_templatetags_modules:
                    self.assertNotIn(templatetags_module,
                                     get_templatetags_modules())

                with self.assertRaisesRegexp(TemplateSyntaxError,
                                             'is not a (valid|registered) tag '
                                             'library'):
                    Template(template_str).render(Context({}))

        template_str = (
            '{% load templatetag_tests %}'
            '{% my_extension_template_tag %}'
        )

        # Sanity-check that the template tag module isn't registered.
        _check_state(enabled=False)

        # Enabling the extension should register the template tags module and
        # clear the cache.
        extension = self.setup_extension(TestExtension)

        _check_state(enabled=True)

        # Shutting down the extension should remove the template tags module
        # and clear the cache.
        self.manager.disable_extension(extension.id)

        _check_state(enabled=False)

        # Other libraries should still work.
        Template('{% load djblets_js djblets_extensions %}').render(
            Context({}))

    def test_enable_syncs_models(self):
        """Testing ExtensionManager.enable_extension synchronizes database
        models
        """
        class TestExtension(Extension):
            apps = [
                'djblets.extensions.test.model_tests',
            ]

        extension = self.setup_extension(TestExtension)

        from djblets.extensions.test.model_tests.models import \
            TestExtensionModel

        # We should be able to create entries and query them.
        TestExtensionModel.objects.create(test_field='test')
        self.assertEqual(TestExtensionModel.objects.count(), 1)

        # Re-enabling shouldn't break anything.
        self.manager.disable_extension(extension.id)
        self.manager.enable_extension(extension.id)
        self.assertEqual(TestExtensionModel.objects.count(), 1)

    def test_enable_extension_evolves_models(self):
        """Testing ExtensionManager.enable_extension evolves database models"""
        try:
            from django_evolution.models import Version
            from django_evolution.signature import create_model_sig
        except ImportError:
            raise nose.SkipTest()

        class TestExtension(Extension):
            apps = [
                'djblets.extensions.test.evolve_tests',
            ]

        # We need to set some initial state in the database for the model and
        # for the evolution history.
        connection.cursor().execute(
            'CREATE TABLE evolve_tests_testextensionmodel ('
            '    id INTEGER PRIMARY KEY AUTOINCREMENT,'
            '    test_field VARCHAR(16) NOT NULL'
            ')')

        from djblets.extensions.test.model_tests.models import \
            TestExtensionModel

        latest_version = Version.objects.current_version()
        sig = pickle.loads(bytes(latest_version.signature))

        model_sig = create_model_sig(TestExtensionModel)
        model_sig['meta']['db_table'] = 'evolve_tests_testevolveextensionmodel'

        sig['evolve_tests'] = {
            'TestEvolveExtensionModel': model_sig,
        }

        Version.objects.create(signature=pickle.dumps(sig))

        # We can now enable the extension, which will perform an evolution.
        extension = self.setup_extension(TestExtension)

        from djblets.extensions.test.evolve_tests.models import \
            TestEvolveExtensionModel

        # We should be able to create entries and query them.
        TestEvolveExtensionModel.objects.create(test_field='test')
        self.assertEqual(TestEvolveExtensionModel.objects.count(), 1)

        # We're now going to shut down and re-enable, but with a different
        # version of the model. This should trigger an evolution sequence.
        self.manager.disable_extension(extension.id)

        self.manager.enable_extension(extension.id)

        TestEvolveExtensionModel.objects.create(test_field='test',
                                                new_field=100)
        self.assertEqual(TestEvolveExtensionModel.objects.count(), 2)

        obj = TestEvolveExtensionModel.objects.get(pk=2)
        self.assertEqual(obj.new_field, 100)


    def test_disable_unregisters_static_bundles(self):
        """Testing ExtensionManager unregisters static bundles when disabling
        extension
        """
        class TestExtension(Extension):
            css_bundles = {
                'default': {
                    'source_filenames': ['test.css'],
                }
            }

            js_bundles = {
                'default': {
                    'source_filenames': ['test.js'],
                }
            }

        pipeline_settings.STYLESHEETS = {}
        pipeline_settings.JAVASCRIPT = {}

        extension = self.setup_extension(TestExtension)

        self.assertEqual(len(pipeline_settings.STYLESHEETS), 1)
        self.assertEqual(len(pipeline_settings.JAVASCRIPT), 1)

        self.manager.disable_extension(extension.id)

        self.assertEqual(len(pipeline_settings.STYLESHEETS), 0)
        self.assertEqual(len(pipeline_settings.JAVASCRIPT), 0)

    def test_extension_list_sync(self):
        """Testing ExtensionManager extension list synchronization
        cross-process
        """
        class TestExtension(Extension):
            pass

        key = 'extension-list-sync'
        fake_entry_point = FakeEntryPoint(TestExtension,
                                          project_name=self.test_project_name)

        manager1 = TestExtensionManager([fake_entry_point], key)
        manager2 = TestExtensionManager([fake_entry_point], key)

        manager1.load()
        manager2.load()

        self.assertEqual(len(manager1.get_installed_extensions()), 1)
        self.assertEqual(len(manager2.get_installed_extensions()), 1)
        self.assertEqual(len(manager1.get_enabled_extensions()), 0)
        self.assertEqual(len(manager2.get_enabled_extensions()), 0)

        manager1.enable_extension(TestExtension.id)
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
        """Testing ExtensionManager extension settings synchronization
        cross-process
        """
        class TestExtension(Extension):
            pass

        key = 'extension-settings-sync'
        setting_key = 'foo'
        setting_val = 'abc123'
        fake_entry_point = FakeEntryPoint(TestExtension,
                                          project_name=self.test_project_name)

        manager1 = TestExtensionManager([fake_entry_point], key)
        manager2 = TestExtensionManager([fake_entry_point], key)

        manager1.load()

        extension1 = manager1.enable_extension(TestExtension.id)

        manager2.load()

        self.assertFalse(manager1.is_expired())
        self.assertFalse(manager2.is_expired())

        extension2 = manager2.get_enabled_extension(TestExtension.id)
        self.assertNotEqual(extension2, None)

        self.assertNotIn(setting_key, extension1.settings)
        self.assertNotIn(setting_key, extension2.settings)
        extension1.settings[setting_key] = setting_val
        extension1.settings.save()

        self.assertNotIn(setting_key, extension2.settings)

        self.assertFalse(manager1.is_expired())
        self.assertTrue(manager2.is_expired())

        manager2.load(full_reload=True)
        extension2 = manager2.get_enabled_extension(TestExtension.id)

        self.assertFalse(manager1.is_expired())
        self.assertFalse(manager2.is_expired())
        self.assertIn(setting_key, extension1.settings)
        self.assertIn(setting_key, extension2.settings)
        self.assertEqual(extension1.settings[setting_key], setting_val)
        self.assertEqual(extension2.settings[setting_key], setting_val)

    def test_load_blocks_sync_gen(self):
        """Testing ExtensionManager.load blocks bumping sync generation
        number
        """
        class TestExtension(Extension):
            pass

        key = 'check-expired-test'
        fake_entry_point = FakeEntryPoint(TestExtension,
                                          project_name=self.test_project_name)

        manager1 = TestExtensionManager([fake_entry_point], key)
        manager2 = TestExtensionManager([fake_entry_point], key)

        manager1.load()
        manager1.enable_extension(TestExtension.id)
        manager2.load()

        self.assertEqual(manager1._gen_sync.sync_gen,
                         manager2._gen_sync.sync_gen)

        # Trigger a save whenever the extension initializes.
        TestExtension.initialize = lambda ext: ext.settings.save()

        # Bump the generation number.
        extension = manager2.get_enabled_extension(TestExtension.id)
        extension.settings.save()
        self.assertNotEqual(manager1._gen_sync.sync_gen,
                            manager2._gen_sync.sync_gen)

        # Loading now should retain the new sync generation number, instead
        # of bumping it.
        manager1.load(full_reload=True)
        self.assertEqual(manager1._gen_sync.sync_gen,
                         manager2._gen_sync.sync_gen)

    def _run_thread_test(self, main_func):
        def _thread_main(main_connection, main_func, sleep_time):
            # Insert the connection from the main thread, so that we can
            # perform lookups. We never write.
            from django.db import connections

            connections['default'] = main_connection

            time.sleep(sleep_time)
            main_func()

        # Store the main connection. We're going to let the threads share it.
        # This trick courtesy of the Django unit tests
        # (django/tests/backends/tests.py).
        from django.db import connections

        main_connection = connections['default']
        main_connection.allow_thread_sharing = True

        self.exceptions = []

        t1 = threading.Thread(target=_thread_main,
                              args=[main_connection, main_func, 0.2])
        t2 = threading.Thread(target=_thread_main,
                              args=[main_connection, main_func, 0.1])
        t1.start()
        t2.start()
        t1.join()
        t2.join()

    def _sleep_and_call(self, manager, orig_func, *args, **kwargs):
        # This works well enough to throw a monkey wrench into things.
        # One thread will be slightly ahead of the other.
        time.sleep(0.2)

        try:
            orig_func(*args, **kwargs)
        except Exception as e:
            logging.error('%s\n', e, exc_info=1)
            self.exceptions.append(e)

    def _spy_sleep_and_call(self, func):
        def _call(manager, *args, **kwargs):
            self._sleep_and_call(manager, orig_func, *args, **kwargs)

        orig_func = func

        self.spy_on(func, call_fake=_call)


class SettingListWrapperTests(TestCase):
    """Unit tests for djblets.extensions.manager.SettingListWrapper."""
    def test_loading_from_setting(self):
        """Testing SettingListWrapper constructor loading from settings"""
        settings.TEST_SETTING_LIST = ['item1', 'item2']
        wrapper = SettingListWrapper('TEST_SETTING_LIST', 'test setting list')

        self.assertEqual(wrapper.ref_counts.get('item1'), 1)
        self.assertEqual(wrapper.ref_counts.get('item2'), 1)

    def test_add_with_new_item(self):
        """Testing SettingListWrapper.add with new item"""
        settings.TEST_SETTING_LIST = []
        wrapper = SettingListWrapper('TEST_SETTING_LIST', 'test setting list')
        wrapper.add('item1')

        self.assertEqual(settings.TEST_SETTING_LIST, ['item1'])
        self.assertEqual(wrapper.ref_counts.get('item1'), 1)

    def test_add_with_existing_item(self):
        """Testing SettingListWrapper.add with existing item"""
        settings.TEST_SETTING_LIST = ['item1']
        wrapper = SettingListWrapper('TEST_SETTING_LIST', 'test setting list')
        wrapper.add('item1')

        self.assertEqual(settings.TEST_SETTING_LIST, ['item1'])
        self.assertEqual(wrapper.ref_counts.get('item1'), 2)

    def test_remove_with_ref_count_1(self):
        """Testing SettingListWrapper.remove with ref_count == 1"""
        settings.TEST_SETTING_LIST = ['item1']
        wrapper = SettingListWrapper('TEST_SETTING_LIST', 'test setting list')

        self.assertEqual(wrapper.ref_counts.get('item1'), 1)
        wrapper.remove('item1')

        self.assertEqual(settings.TEST_SETTING_LIST, [])
        self.assertFalse('item1' in wrapper.ref_counts)

    def test_remove_with_ref_count_gt_1(self):
        """Testing SettingListWrapper.remove with ref_count > 1"""
        settings.TEST_SETTING_LIST = ['item1']
        wrapper = SettingListWrapper('TEST_SETTING_LIST', 'test setting list')
        wrapper.add('item1')

        self.assertEqual(wrapper.ref_counts.get('item1'), 2)
        wrapper.remove('item1')

        self.assertEqual(settings.TEST_SETTING_LIST, ['item1'])
        self.assertEqual(wrapper.ref_counts.get('item1'), 1)


class SignalHookTests(SpyAgency, ExtensionTestsMixin, TestCase):
    """Unit tests for djblets.extensions.hooks.SignalHook."""
    def setUp(self):
        class TestExtension(Extension):
            pass

        super(SignalHookTests, self).setUp()

        self.test_extension = self.setup_extension(TestExtension)

        self.signal = Signal()
        self.spy_on(self._on_signal_fired)
        self.spy_on(self._on_signal_exception)

    def test_initialize(self):
        """Testing SignalHook initialization connects to signal"""
        SignalHook(self.test_extension, self.signal, self._on_signal_fired)

        self.assertEqual(len(self._on_signal_fired.calls), 0)
        self.signal.send(self)
        self.assertEqual(len(self._on_signal_fired.calls), 1)

    def test_shutdown(self):
        """Testing SignalHook.shutdown disconnects from signal"""
        hook = SignalHook(self.test_extension, self.signal,
                          self._on_signal_fired)
        hook.disable_hook()

        self.assertEqual(len(self._on_signal_fired.calls), 0)
        self.signal.send(self)
        self.assertEqual(len(self._on_signal_fired.calls), 0)

    def test_shutdown_with_sender(self):
        """Testing SignalHook.shutdown disconnects when a sender was set"""
        hook = SignalHook(self.test_extension, self.signal,
                          self._on_signal_fired, sender=self)
        hook.disable_hook()

        self.assertEqual(len(self._on_signal_fired.calls), 0)
        self.signal.send(self)
        self.assertEqual(len(self._on_signal_fired.calls), 0)

    def test_forwards_args(self):
        """Testing SignalHook forwards arguments to callback"""
        seen_kwargs = {}

        def callback(**kwargs):
            seen_kwargs.update(kwargs)

        SignalHook(self.test_extension, self.signal, callback)
        self.signal.send(sender=self, foo=1, bar=2)

        self.assertTrue('foo', seen_kwargs)
        self.assertEqual(seen_kwargs['foo'], 1)
        self.assertTrue('bar', seen_kwargs)
        self.assertEqual(seen_kwargs['bar'], 2)

    def test_sandbox_errors_true(self):
        """Testing SignalHook with sandbox_errors set to True logs errors"""
        SignalHook(self.test_extension, self.signal, self._on_signal_exception,
                   sandbox_errors=True)

        self.assertEqual(len(self._on_signal_exception.calls), 0)
        self.signal.send(self)
        self.assertEqual(len(self._on_signal_exception.calls), 1)

    def test_sandbox_errors_false(self):
        """Testing SignalHook with sandbox_errors set to False"""
        SignalHook(self.test_extension, self.signal, self._on_signal_exception,
                   sandbox_errors=False)

        self.assertEqual(len(self._on_signal_exception.calls), 0)
        self.assertRaises(Exception, self.signal.send, self)
        self.assertEqual(len(self._on_signal_exception.calls), 1)

    def _on_signal_fired(self, *args, **kwargs):
        pass

    def _on_signal_exception(self, *args, **kwargs):
        raise Exception


class URLHookTest(ExtensionTestsMixin, TestCase):
    def setUp(self):
        class TestExtension(Extension):
            def initialize(self):
                self.patterns = [
                    url(r'^url_hook_test/',
                        include('djblets.extensions.test.urls')),
                ]
                self.url_hook = URLHook(self, self.patterns)

        super(URLHookTest, self).setUp()

        self.extension = self.setup_extension(TestExtension)

    def test_url_registration(self):
        """Testing URLHook URL registration"""
        self.assertTrue(
            set(self.extension.patterns)
            .issubset(set(self.extension.url_hook.dynamic_urls.url_patterns)))

        # And the URLHook should be added to the extension's list of hooks
        self.assertIn(self.extension.url_hook, self.extension.hooks)

    def test_shutdown_removes_urls(self):
        """Testing URLHook.shutdown"""
        # On shutdown, a URLHook's patterns should no longer be in its
        # parent URL resolver's pattern collection.
        self.extension.url_hook.disable_hook()
        self.assertFalse(
            set(self.extension.patterns).issubset(
                set(self.extension.url_hook.dynamic_urls.url_patterns)))

        # But the URLHook should still be in the extension's list of hooks
        self.assertIn(self.extension.url_hook, self.extension.hooks)


class TemplateHookTests(SpyAgency, ExtensionTestsMixin, TestCase):
    """Unit tests for djblets.extensions.hooks.TemplateHook."""

    def setUp(self):
        class TestExtension(Extension):
            def initialize(self):
                self.hook_no_applies_name = 'template-hook-no-applies-name'
                self.template_hook_no_applies = TemplateHook(
                    self,
                    self.hook_no_applies_name,
                    'test_module/some_template.html',
                    [])

                self.hook_with_applies_name = 'template-hook-with-applies-name'
                self.template_hook_with_applies = TemplateHook(
                    self,
                    self.hook_with_applies_name,
                    'test_module/some_template.html',
                    [
                        'test-url-name',
                        'url_2',
                        'url_3',
                    ]
                )

        super(TemplateHookTests, self).setUp()

        self.extension = self.setup_extension(TestExtension)

        self.request = Mock()
        self.request._djblets_extensions_kwargs = {}
        self.request.path_info = '/'
        self.request.resolver_match = Mock()
        self.request.resolver_match.url_name = 'root'

    def test_hook_added_to_class_by_name(self):
        """Testing TemplateHook registration"""
        self.assertIn(
            self.extension.template_hook_with_applies,
            TemplateHook._by_name[self.extension.hook_with_applies_name])

        # The TemplateHook should also be added to the Extension's collection
        # of hooks.
        self.assertIn(self.extension.template_hook_with_applies,
                      self.extension.hooks)

    def test_hook_shutdown(self):
        """Testing TemplateHook shutdown"""
        self.extension.template_hook_with_applies.disable_hook()
        self.assertNotIn(
            self.extension.template_hook_with_applies,
            TemplateHook._by_name[self.extension.hook_with_applies_name])

        # The TemplateHook should still be in the Extension's collection
        # of hooks.
        self.assertIn(self.extension.template_hook_with_applies,
                      self.extension.hooks)

    def test_applies_to_default(self):
        """Testing TemplateHook.applies_to defaults to everything"""
        self.assertTrue(
            self.extension.template_hook_no_applies.applies_to(self.request))
        self.assertTrue(
            self.extension.template_hook_no_applies.applies_to(None))

    def test_applies_to(self):
        """Testing TemplateHook.applies_to customization"""
        self.assertFalse(
            self.extension.template_hook_with_applies.applies_to(self.request))

        self.request.resolver_match.url_name = 'test-url-name'
        self.assertTrue(
            self.extension.template_hook_with_applies.applies_to(self.request))

    def test_render_to_string(self):
        """Testing TemplateHook.render_to_string"""
        hook = TemplateHook(
            self.extension,
            name='test',
            template_name='deco/box.html',
            extra_context={
                'content': 'Hello world',
            })

        request = RequestFactory().request()
        result = hook.render_to_string(request, RequestContext(request, {
            'classname': 'test',
        }))

        self.assertHTMLEqual(
            result,
            '<div class="box-container">'
            ' <div class="box test">'
            '  <div class="box-inner">'
            '   Hello world'
            '  </div>'
            ' </div>'
            '</div>')

    def test_context_doesnt_leak(self):
        """Testing TemplateHook's context won't leak state"""
        class MyTemplateHook(TemplateHook):
            def render_to_string(self, request, context):
                context['leaky'] = True

                return ''

        MyTemplateHook(self.extension, 'test')
        context = Context({})
        context['request'] = None

        t = Template(
            '{% load djblets_extensions %}'
            '{% template_hook_point "test" %}')
        t.render(context).strip()

        self.assertNotIn('leaky', context)

    def test_render_to_string_sandbox(self):
        """Testing TemplateHook sandboxing"""
        class MyTemplateHook(TemplateHook):
            def render_to_string(self, request, context):
                raise Exception('Oh noes')

        MyTemplateHook(self.extension, 'test')
        context = Context({})
        context['request'] = None

        t = Template(
            '{% load djblets_extensions %}'
            '{% template_hook_point "test" %}')
        t.render(context).strip()

        # Didn't crash. We're good.

    def test_applies_to_sandbox(self):
        """Testing TemplateHook for applies_to"""
        class MyTemplateHook(TemplateHook):
            def applies_to(self, request):
                raise Exception

        hook = MyTemplateHook(extension=self.extension, name='test')
        context = Context({})
        context['request'] = self.request

        self.spy_on(hook.applies_to)

        t = Template(
            '{% load djblets_extensions %}'
            '{% template_hook_point "test" %}')
        string = t.render(context).strip()

        self.assertEqual(string, '')

        self.assertTrue(hook.applies_to.called)


class DataGridColumnsHookTest(SpyAgency, ExtensionTestsMixin, TestCase):
    def setUp(self):
        class TestExtension(Extension):
            pass

        super(DataGridColumnsHookTest, self).setUp()

        self.extension = self.setup_extension(TestExtension)

    def test_add_column(self):
        """Testing DataGridColumnsHook registers column"""
        self.spy_on(DataGrid.add_column)

        DataGridColumnsHook(extension=self.extension,
                            datagrid_cls=DataGrid,
                            columns=[Column(id='sandbox')])

        self.assertTrue(DataGrid.add_column.called)

    def test_remove_column(self):
        """Testing DataGridColumnsHook unregisters column"""
        self.spy_on(DataGrid.remove_column)

        hook = DataGridColumnsHook(extension=self.extension,
                                   datagrid_cls=DataGrid,
                                   columns=[Column(id='sandbox2')])

        hook.disable_hook()

        self.assertTrue(DataGrid.remove_column.called)


class BaseRegistryHookTests(ExtensionTestsMixin, TestCase):
    """Tests for BaseRegistryHooks."""

    class DummyRegistry(Registry):
        lookup_attrs = ('foo_id',)

    class DummyItem(object):
        def __init__(self, foo_id):
            self.foo_id = foo_id

    def setUp(self):
        super(BaseRegistryHookTests, self).setUp()

        self.registry = self.DummyRegistry()

        @six.add_metaclass(ExtensionHookPoint)
        class DummyRegistryHook(BaseRegistryHook):
            registry = self.registry

        class TestExtension(Extension):
            pass

        self.hook_cls = DummyRegistryHook

        self.extension = self.setup_extension(TestExtension)

    def test_hook_register(self):
        """Testing BaseRegistryHook item registration"""
        self.assertEqual(list(self.registry), [])

        item = self.DummyItem(123)
        self.hook_cls(self.extension, item)

        self.assertIn(item, self.registry)

    def test_hook_unregister(self):
        """Testing BaseRegistryHook item unregistration"""
        self.assertEqual(list(self.registry), [])
        item = self.DummyItem(123)
        self.hook_cls(self.extension, item)

        self.extension.shutdown()
        self.assertEqual(list(self.registry), [])


class BaseRegistryMultiItemHookTests(ExtensionTestsMixin, TestCase):
    """Tests for BaseRegistryMultiItemHooks."""

    class DummyRegistry(Registry):
        lookup_attrs = ('foo_id',)

    class DummyItem(object):
        def __init__(self, foo_id):
            self.foo_id = foo_id

    def setUp(self):
        super(BaseRegistryMultiItemHookTests, self).setUp()

        self.registry = self.DummyRegistry()

        @six.add_metaclass(ExtensionHookPoint)
        class DummyRegistryHook(BaseRegistryMultiItemHook):
            registry = self.registry

        class TestExtension(Extension):
            pass

        self.hook_cls = DummyRegistryHook

        self.extension = self.setup_extension(TestExtension)

    def test_initialize(self):
        """Testing BaseRegistryMultiItemHook.initialize"""
        self.assertEqual(list(self.registry), [])

        item1 = self.DummyItem(123)
        item2 = self.DummyItem(456)
        self.hook_cls(self.extension, [item1, item2])

        self.assertIn(item1, self.registry)
        self.assertIn(item2, self.registry)

    def test_initialize_handles_errors(self):
        """Testing BaseRegistryMultiItemHook.initialize unregisters all items
        on registration error
        """
        self.assertEqual(list(self.registry), [])

        item1 = self.DummyItem(123)
        item2 = self.DummyItem(123)

        with self.assertRaises(AlreadyRegisteredError):
            self.hook_cls(self.extension, [item1, item2])

        self.assertEqual(list(self.registry), [])

    def test_shutdown(self):
        """Testing BaseRegistryMultiItemHook.shutdown"""
        self.assertEqual(list(self.registry), [])

        item1 = self.DummyItem(123)
        item2 = self.DummyItem(456)
        self.hook_cls(self.extension, [item1, item2])

        self.extension.shutdown()
        self.assertEqual(list(self.registry), [])


class ViewTests(SpyAgency, ExtensionTestsMixin, TestCase):
    """Unit tests for djblets.extensions.views."""

    def setUp(self):
        class TestExtension(Extension):
            admin_urlconf = []
            is_configurable = True

        super(ViewTests, self).setUp()

        self.extension = self.setup_extension(TestExtension)

    def test_configure_extension_saving(self):
        """Testing configure_extension with saving settings"""
        class TestSettingsForm(SettingsForm):
            mykey = forms.CharField(max_length=100)

        self.spy_on(self.manager.get_enabled_extension,
                    call_fake=lambda *args: self.extension)

        urlpatterns[:] = [
            url('^config/$', configure_extension,
                {
                    'ext_class': type(self.extension),
                    'form_class': TestSettingsForm,
                    'extension_manager': self.manager,
                }),
            url('', include(admin.site.urls)),
        ]

        User.objects.create_superuser(username='admin',
                                      password='admin',
                                      email='admin@example.com')

        with override_settings(ROOT_URLCONF='djblets.extensions.tests'):
            self.client.login(username='admin', password='admin')

            # Fetch once for the CSRF token.
            response = self.client.get('/config/')
            self.assertEqual(response.status_code, 200)

            # Save new settings in the form.
            response = self.client.post('/config/', data={
                'mykey': 'myvalue',
            })
            self.assertEqual(response.status_code, 302)

        self.assertEqual(self.extension.settings.get('mykey'), 'myvalue')


# A dummy function that acts as a View method
test_view_method = Mock()

# A placeholder for any urlpatterns that need to be set for tests.
urlpatterns = []
