"""Unit tests for djblets.extensions.manager.ExtensionManager."""

import errno
import logging
import os
import shutil
import tempfile
import threading
import time

import kgb
from django.conf import settings
from django.db import connection
from django.template import Context, Template, TemplateSyntaxError
from django.test.utils import override_settings
from django_evolution.evolve import Evolver
from pipeline.conf import settings as pipeline_settings

from djblets.extensions.errors import EnablingExtensionError
from djblets.extensions.extension import Extension
from djblets.extensions.hooks import URLHook
from djblets.extensions.manager import (ExtensionManager,
                                        get_extension_managers,
                                        logger as manager_logger)
from djblets.extensions.testing import ExtensionTestCaseMixin
from djblets.testing.testcases import TestCase


logger = logging.getLogger(__name__)


class MyTestExtension(Extension):
    # We set this to djblets.extensions to avoid an issue unique to tests
    # involving multiple ExtensionManagers. They'd both try wrapping
    # INSTALLED_APPS, and would try adding the same default app for the
    # extension upon load. While doing that, they'd assert that the extension
    # wasn't in INSTALLED_APPS, and that'd fail. The issue should only occur in
    # this test, or in a case of an app with multiple extension managers
    # loading the same list of apps.
    apps = [
        'djblets.extensions',
    ]


class HooksTestExtension(MyTestExtension):
    def initialize(self):
        self.url_hook = URLHook(self, ())


class ExtensionManagerTests(kgb.SpyAgency, ExtensionTestCaseMixin, TestCase):
    """Unit tests for djblets.extensions.manager.ExtensionManager."""

    @classmethod
    def setUpClass(cls):
        connection.disable_constraint_checking()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        connection.enable_constraint_checking()

    def tearDown(self):
        super(ExtensionManagerTests, self).tearDown()

        self.assertEqual(len(URLHook.hooks), 0)

    def test_added_to_extension_managers(self):
        """Testing ExtensionManager registration"""
        manager = ExtensionManager('unit-tests')
        self.assertIn(manager, get_extension_managers())

    def test_get_enabled_extensions_returns_empty(self):
        """Testing ExtensionManager.get_enabled_extensions with no
        extensions
        """
        manager = ExtensionManager('unit-tests')
        manager.load()

        self.assertEqual(len(manager.get_enabled_extensions()), 0)

    def test_load(self):
        """Testing ExtensionManager.get_installed_extensions with loaded
        extensions
        """
        self.setup_extension(MyTestExtension, enable=False)

        self.assertEqual(self.extension_mgr.get_installed_extensions(),
                         [MyTestExtension])
        self.assertEqual(len(self.extension_mgr.get_enabled_extensions()), 0)
        self.assertTrue(hasattr(MyTestExtension, 'info'))
        self.assertEqual(MyTestExtension.info.name,
                         self.extension_package_name)
        self.assertTrue(hasattr(MyTestExtension, 'registration'))
        self.assertEqual(MyTestExtension.registration.name,
                         self.extension_package_name)

    def test_load_full_reload_hooks(self):
        """Testing ExtensionManager.load with full_reload=True"""
        # NOTE: We're not using HooksTestExtension here, because we want to
        #       manually set up a hook and not have to return once we
        #       perform a reload.
        extension = self.setup_extension(MyTestExtension)

        self.assertEqual(len(self.extension_mgr.get_installed_extensions()), 1)
        self.assertEqual(len(self.extension_mgr.get_enabled_extensions()), 1)

        URLHook(extension, ())
        self.assertEqual(len(URLHook.hooks), 1)
        self.assertEqual(URLHook.hooks[0].extension, extension)

        with self.scanned_extensions([MyTestExtension]):
            self.extension_mgr.load(full_reload=True)

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
        extension_mgr = self.extension_mgr

        # Enable one extension. This extension's state will get a bit messed
        # up if the thread locking fails. We only need one to trigger this.
        self.setup_extension(MyTestExtension)

        self.spy_on(extension_mgr._load_extensions)
        self._spy_sleep_and_call(extension_mgr._init_extension)
        self._spy_sleep_and_call(extension_mgr._uninit_extension)

        with self.scanned_extensions([MyTestExtension]):
            self._run_thread_test(lambda: extension_mgr.load(full_reload=True))

        self.assertSpyCallCount(extension_mgr._load_extensions, 2)
        self.assertSpyCallCount(extension_mgr._uninit_extension, 2)
        self.assertSpyCallCount(extension_mgr._init_extension, 2)
        self.assertEqual(self.exceptions, [])

    @override_settings(EXTENSIONS_ENABLED_BY_DEFAULT=[
        'djblets.extensions.tests.test_extension_manager.MyTestExtension',
    ])
    def test_load_with_enabled_by_default(self):
        """Testing ExtensionManager.load with
        settings.EXTENSIONS_ENABLED_BY_DEFAULT
        """
        extension_mgr = self.extension_mgr

        self.setup_extension(MyTestExtension, enable=False)

        with self.scanned_extensions([MyTestExtension]):
            extension_mgr.load()

        self.assertEqual(extension_mgr.get_installed_extensions(),
                         [MyTestExtension])

        enabled_extensions = extension_mgr.get_enabled_extensions()
        self.assertEqual(len(enabled_extensions), 1)
        self.assertIsInstance(enabled_extensions[0], MyTestExtension)

        self.assertTrue(hasattr(MyTestExtension, 'info'))
        self.assertEqual(MyTestExtension.info.name,
                         self.extension_package_name)
        self.assertIsNotNone(MyTestExtension.instance)
        self.assertTrue(hasattr(MyTestExtension, 'registration'))
        self.assertEqual(MyTestExtension.registration.name,
                         self.extension_package_name)
        self.assertTrue(MyTestExtension.registration.enabled)

    def test_load_with_admin_site(self):
        """Testing ExtensionManager.load with has_admin_site=True"""
        class AdminSiteMyTestExtension(HooksTestExtension):
            has_admin_site = True

        manager = self.extension_mgr

        @self.spy_for(manager._init_admin_site)
        def _init_admin_site(_self, *args, **kwargs):
            self.assertIsNotNone(AdminSiteMyTestExtension.instance)
            self.assertIsInstance(AdminSiteMyTestExtension.instance,
                                  AdminSiteMyTestExtension)

            return manager._init_admin_site.call_original(*args, **kwargs)

        extension = self.setup_extension(AdminSiteMyTestExtension)

        self.assertEqual(manager.get_installed_extensions(),
                         [AdminSiteMyTestExtension])
        self.assertEqual(manager.get_enabled_extensions(), [extension])
        self.assertIs(AdminSiteMyTestExtension.instance, extension)

        self.assertIsNotNone(extension.admin_site)
        self.assertEqual(extension.admin_site.name, 'djblets.extensions.tests')

    def test_load_with_admin_site_failure(self):
        """Testing ExtensionManager.load with extension error setting up
        admin site
        """
        class AdminSiteMyTestExtension(HooksTestExtension):
            has_admin_site = True

        extension = self.setup_extension(AdminSiteMyTestExtension)
        manager = self.extension_mgr

        self.assertEqual(manager.get_installed_extensions(),
                         [AdminSiteMyTestExtension])
        self.assertEqual(manager.get_enabled_extensions(), [extension])
        self.assertIs(AdminSiteMyTestExtension.instance, extension)
        self.assertEqual(len(URLHook.hooks), 1)

        @self.spy_for(manager._init_admin_site)
        def _init_admin_site(*args, **kwargs):
            raise Exception('admin site failed!')

        with self.scanned_extensions([AdminSiteMyTestExtension]):
            self.extension_mgr.load(full_reload=True)

        self.assertEqual(manager.get_installed_extensions(),
                         [AdminSiteMyTestExtension])
        self.assertEqual(manager.get_enabled_extensions(), [])
        self.assertIsNone(AdminSiteMyTestExtension.instance)
        self.assertEqual(len(URLHook.hooks), 0)
        self.assertTrue(manager._load_errors[extension.id].startswith(
            'admin site failed!\n\nTraceback'))

    def test_load_with_admin_urls_failure(self):
        """Testing ExtensionManager.load with extension error setting up
        admin URLs
        """
        extension = self.setup_extension(HooksTestExtension)
        manager = self.extension_mgr

        self.assertEqual(manager.get_installed_extensions(),
                         [HooksTestExtension])
        self.assertEqual(manager.get_enabled_extensions(), [extension])
        self.assertIs(HooksTestExtension.instance, extension)
        self.assertEqual(len(URLHook.hooks), 1)
        self.assertEqual(manager._load_errors, {})

        @self.spy_for(manager._install_admin_urls)
        def _install_admin_urls(*args, **kwargs):
            raise Exception('admin URLs failed!')

        with self.scanned_extensions([HooksTestExtension]):
            self.extension_mgr.load(full_reload=True)

        self.assertEqual(manager.get_installed_extensions(),
                         [HooksTestExtension])
        self.assertEqual(manager.get_enabled_extensions(), [])
        self.assertIsNone(HooksTestExtension.instance)
        self.assertEqual(len(URLHook.hooks), 0)
        self.assertIn(extension.id, manager._load_errors)
        self.assertTrue(manager._load_errors[extension.id].startswith(
            'admin URLs failed!\n\nTraceback'))

    def test_sync_database_with_no_settings_version(self):
        """Testing ExtensionManager synchronizes database when no version
        found in settings (new install)
        """
        extension_mgr = self.extension_mgr

        self.setup_extension(MyTestExtension, enable=False)
        extension = MyTestExtension(extension_mgr)
        extension.registration.installed = True
        extension.registration.save()

        self.assertNotIn(extension_mgr.VERSION_SETTINGS_KEY,
                         extension.settings)

        self.spy_on(extension_mgr._sync_database, call_original=False)

        extension = extension_mgr.enable_extension(MyTestExtension.id)

        self.assertTrue(extension.registration.installed)
        self.assertSpyCalled(extension_mgr._sync_database)
        self.assertIn(extension_mgr.VERSION_SETTINGS_KEY, extension.settings)
        self.assertEqual(
            extension.settings[extension_mgr.VERSION_SETTINGS_KEY],
            extension.info.version)

    def test_sync_database_with_old_settings_version(self):
        """Testing ExtensionManager synchronizes database when old version
        found in settings (upgrade)
        """
        extension_mgr = self.extension_mgr

        self.setup_extension(MyTestExtension, enable=False)
        extension = MyTestExtension(extension_mgr)
        extension.registration.installed = True
        extension.registration.save()

        self.assertNotIn(extension_mgr.VERSION_SETTINGS_KEY,
                         extension.settings)
        extension.settings.set(extension_mgr.VERSION_SETTINGS_KEY, '0.5')
        extension.settings.save()

        self.spy_on(extension_mgr._sync_database, call_original=False)

        extension = extension_mgr.enable_extension(MyTestExtension.id)

        self.assertTrue(extension.registration.installed)
        self.assertSpyCalled(extension_mgr._sync_database)
        self.assertIn(extension_mgr.VERSION_SETTINGS_KEY, extension.settings)
        self.assertEqual(
            extension.settings[extension_mgr.VERSION_SETTINGS_KEY],
            extension.info.version)

    def test_sync_database_with_current_settings_version(self):
        """Testing ExtensionManager doesn't synchronize database when current
        version found in settings
        """
        extension_mgr = self.extension_mgr

        self.setup_extension(MyTestExtension, enable=False)
        extension = MyTestExtension(extension_mgr)
        extension.registration.installed = True
        extension.registration.save()

        self.assertNotIn(extension_mgr.VERSION_SETTINGS_KEY,
                         extension.settings)
        extension.settings.set(extension_mgr.VERSION_SETTINGS_KEY,
                               extension.info.version)
        extension.settings.save()

        self.spy_on(extension_mgr._sync_database, call_original=False)

        extension = extension_mgr.enable_extension(MyTestExtension.id)

        self.assertTrue(extension.registration.installed)
        self.assertSpyNotCalled(extension_mgr._sync_database)
        self.assertIn(extension_mgr.VERSION_SETTINGS_KEY, extension.settings)
        self.assertEqual(
            extension.settings[extension_mgr.VERSION_SETTINGS_KEY],
            extension.info.version)

    def test_sync_database_with_newer_settings_version(self):
        """Testing ExtensionManager doesn't synchronize database when newer
        version found in settings (downgrade)
        """
        extension_mgr = self.extension_mgr

        self.setup_extension(MyTestExtension, enable=False)
        extension = MyTestExtension(extension_mgr)
        extension.registration.installed = True
        extension.registration.save()

        self.assertNotIn(extension_mgr.VERSION_SETTINGS_KEY,
                         extension.settings)
        extension.settings.set(extension_mgr.VERSION_SETTINGS_KEY, '100.0')
        extension.settings.save()

        self.spy_on(extension_mgr._sync_database, call_original=False)
        self.spy_on(manager_logger.warning)

        extension = extension_mgr.enable_extension(MyTestExtension.id)

        self.assertTrue(extension.registration.installed)
        self.assertSpyNotCalled(extension_mgr._sync_database)
        self.assertIn(extension_mgr.VERSION_SETTINGS_KEY, extension.settings)
        self.assertEqual(
            extension.settings[extension_mgr.VERSION_SETTINGS_KEY],
            '100.0')
        self.assertIn('is older than the version recorded',
                      manager_logger.warning.spy.calls[-1].args[0])

    def test_install_extension_media_with_no_version_file(self):
        """Testing ExtensionManager installs media when no version file exists
        in the media directory (new install or upgrade from pre-version file)
        """
        extension_mgr = self.extension_mgr

        self.setup_extension(MyTestExtension, enable=False)
        extension = MyTestExtension(extension_mgr)
        extension.registration.installed = True
        extension.registration.enabled = True
        extension.registration.save()
        MyTestExtension.instance = extension

        self._rebuild_media_dirs(extension)

        extension_mgr.should_install_static_media = True

        self.spy_on(extension_mgr.install_extension_media)
        self.spy_on(extension_mgr._install_extension_media_internal,
                    call_original=False)

        # Fake the current version being installed.
        version_filename = os.path.join(extension.info.installed_static_path,
                                        '.version')
        self.assertFalse(os.path.exists(version_filename))

        # Enable the extension. We shouldn't install anything.
        extension = extension_mgr.enable_extension(MyTestExtension.id)
        self.assertTrue(extension.registration.installed)

        self.assertSpyCallCount(extension_mgr.install_extension_media, 1)
        self.assertSpyCallCount(
            extension_mgr._install_extension_media_internal, 1)

        with open(version_filename, 'r') as fp:
            self.assertEqual(fp.read().strip(), extension.info.version)

    def test_install_extension_media_with_outdated_version(self):
        """Testing ExtensionManager installs media when version file is
        older than the current version (upgrade)
        """
        extension_mgr = self.extension_mgr

        self.setup_extension(MyTestExtension, enable=False)
        extension = MyTestExtension(extension_mgr)
        extension.registration.installed = True
        extension.registration.enabled = True
        extension.registration.save()
        MyTestExtension.instance = extension

        self._rebuild_media_dirs(extension)

        extension_mgr.should_install_static_media = True

        self.spy_on(extension_mgr.install_extension_media)
        self.spy_on(extension_mgr._install_extension_media_internal,
                    call_original=False)

        # Fake the current version being installed.
        version_filename = os.path.join(extension.info.installed_static_path,
                                        '.version')

        with open(version_filename, 'w') as fp:
            fp.write('0.5\n')

        # Enable the extension. We shouldn't install anything.
        extension = extension_mgr.enable_extension(MyTestExtension.id)
        self.assertTrue(extension.registration.installed)

        self.assertSpyCallCount(extension_mgr.install_extension_media, 1)
        self.assertSpyCallCount(
            extension_mgr._install_extension_media_internal, 1)

        with open(version_filename, 'r') as fp:
            self.assertEqual(fp.read().strip(), extension.info.version)

    def test_install_extension_media_with_newer_version(self):
        """Testing ExtensionManager installs media when version file is
        newer than the current version (downgrade)
        """
        extension_mgr = self.extension_mgr

        self.setup_extension(MyTestExtension, enable=False)
        extension = MyTestExtension(extension_mgr)
        extension.registration.installed = True
        extension.registration.enabled = True
        extension.registration.save()
        MyTestExtension.instance = extension

        self._rebuild_media_dirs(extension)

        extension_mgr.should_install_static_media = True

        self.spy_on(extension_mgr.install_extension_media)
        self.spy_on(extension_mgr._install_extension_media_internal,
                    call_original=False)

        # Fake the current version being installed.
        version_filename = os.path.join(extension.info.installed_static_path,
                                        '.version')

        with open(version_filename, 'w') as fp:
            fp.write('100.0\n')

        # Enable the extension. We shouldn't install anything.
        extension = extension_mgr.enable_extension(MyTestExtension.id)
        self.assertTrue(extension.registration.installed)

        self.assertSpyCallCount(extension_mgr.install_extension_media, 1)
        self.assertSpyCallCount(
            extension_mgr._install_extension_media_internal, 1)

        with open(version_filename, 'r') as fp:
            self.assertEqual(fp.read().strip(), extension.info.version)

    def test_install_extension_media_with_permission_error(self):
        """Testing ExtensionManager media installation with permission error
        when copying media files
        """
        extension_mgr = self.extension_mgr

        self.setup_extension(HooksTestExtension, enable=False)
        extension = HooksTestExtension(extension_mgr)
        extension.shutdown()

        self.assertEqual(len(URLHook.hooks), 0)

        self._rebuild_media_dirs(extension)

        extension_mgr.should_install_static_media = True

        @self.spy_for(shutil.copytree)
        def _copytree(*args, **kwargs):
            raise shutil.Error()

        self.spy_on(extension_mgr.install_extension_media)
        self.spy_on(extension.info.has_resource,
                    op=kgb.SpyOpReturn(True))

        message = (
            'Unable to install static media files for this extension. '
            'The extension will not work correctly without them. Please '
            'make sure that "%s", its contents, and its parent directory '
            'are owned by the web server.'
        ) % os.path.join(
            settings.STATIC_ROOT, 'ext',
            'djblets.extensions.tests.test_extension_manager.'
            'HooksTestExtension'
        )

        with self.assertRaisesMessage(EnablingExtensionError, message):
            extension_mgr.enable_extension(HooksTestExtension.id)

        self.assertSpyCallCount(extension_mgr.install_extension_media, 1)
        self.assertFalse(os.path.exists(
            os.path.join(extension.info.installed_static_path, '.version')))
        self.assertEqual(extension_mgr.get_installed_extensions(),
                         [HooksTestExtension])
        self.assertEqual(extension_mgr.get_enabled_extensions(), [])
        self.assertIsNone(HooksTestExtension.instance)
        self.assertEqual(len(URLHook.hooks), 0)

    def test_install_extension_media_with_lock_error(self):
        """Testing ExtensionManager media installation with error when locking
        static directory
        """
        extension_mgr = self.extension_mgr

        self.setup_extension(HooksTestExtension, enable=False)
        extension = HooksTestExtension(extension_mgr)
        extension.shutdown()

        self._rebuild_media_dirs(extension)

        extension_mgr.should_install_static_media = True
        extension_mgr._MEDIA_LOCK_SLEEP_TIME_SECS = 0

        @self.spy_for(extension_mgr._open_lock_file)
        def _open_lock_file(*args, **kwargs):
            raise IOError(errno.EAGAIN, 'Try again')

        self.spy_on(extension_mgr.install_extension_media)
        self.spy_on(extension_mgr._install_extension_media_internal,
                    call_original=False)

        message = (
            'Unable to install static media files for this extension. There '
            'have been 10 attempts to install the media files. Please make '
            'sure that "%s", its contents, its parent directory, and "%s" are '
            'writable by the web server.'
        ) % (
            os.path.join(
                settings.STATIC_ROOT, 'ext',
                'djblets.extensions.tests.test_extension_manager'
                '.HooksTestExtension'
            ),
            tempfile.gettempdir()
        )

        with self.assertRaisesMessage(EnablingExtensionError, message):
            extension_mgr.enable_extension(HooksTestExtension.id)

        self.assertSpyCallCount(extension_mgr.install_extension_media, 1)
        self.assertSpyNotCalled(
            extension_mgr._install_extension_media_internal)

        self.assertFalse(os.path.exists(
            os.path.join(extension.info.installed_static_path, '.version')))

        self.assertEqual(extension_mgr.get_installed_extensions(),
                         [HooksTestExtension])
        self.assertEqual(extension_mgr.get_enabled_extensions(), [])
        self.assertIsNone(HooksTestExtension.instance)
        self.assertEqual(len(URLHook.hooks), 0)

    def test_install_media_concurrent_threads(self):
        """Testing ExtensionManager installs media safely with multiple
        threads
        """
        extension_mgr = self.extension_mgr

        # Manually mark the extension as installed and enabled without going
        # through the enable process, since we don't want to trigger any
        # static media saving yet.
        self.setup_extension(MyTestExtension, enable=False)
        extension = MyTestExtension(extension_mgr)
        extension.registration.installed = True
        extension.registration.enabled = True
        extension.registration.save()
        MyTestExtension.instance = extension

        self._rebuild_media_dirs(extension)

        extension_mgr.should_install_static_media = True

        self.assertEqual(len(extension_mgr.get_installed_extensions()), 1)

        self.spy_on(extension_mgr.install_extension_media)
        self.spy_on(extension_mgr._install_extension_media_internal,
                    call_original=False)

        # Simulate numerous simultaneous attempts at installing static media.
        self._run_thread_test(
            lambda: extension_mgr.install_extension_media(extension.__class__))

        self.assertEqual(
            len(extension_mgr.install_extension_media.calls), 2)
        self.assertEqual(
            len(extension_mgr._install_extension_media_internal.calls), 1)
        self.assertEqual(self.exceptions, [])

        version_filename = os.path.join(extension.info.installed_static_path,
                                        '.version')

        with open(version_filename, 'r') as fp:
            self.assertEqual(fp.read().strip(), extension.info.version)

    def test_install_extension_media_with_current_version(self):
        """Testing ExtensionManager doesn't install media when version file
        matches current version
        """
        extension_mgr = self.extension_mgr

        self.setup_extension(MyTestExtension, enable=False)
        extension = MyTestExtension(extension_mgr)
        MyTestExtension.registration.installed = True
        MyTestExtension.registration.enabled = True
        MyTestExtension.registration.save()
        MyTestExtension.instance = extension

        self._rebuild_media_dirs(extension)

        extension_mgr.should_install_static_media = True

        self.spy_on(extension_mgr.install_extension_media)
        self.spy_on(extension_mgr._install_extension_media_internal,
                    call_original=False)

        # Fake the current version being installed.
        version_filename = os.path.join(extension.info.installed_static_path,
                                        '.version')

        with open(version_filename, 'w') as fp:
            fp.write('%s\n' % extension.info.version)

        # Enable the extension. We shouldn't install anything.
        extension = extension_mgr.enable_extension(MyTestExtension.id)
        self.assertTrue(extension.registration.installed)

        self.assertEqual(len(extension_mgr.install_extension_media.calls), 1)
        self.assertEqual(
            len(extension_mgr._install_extension_media_internal.calls), 0)

        with open(version_filename, 'r') as fp:
            self.assertEqual(fp.read().strip(), extension.info.version)

    def test_enable_extension_registers_static_bundles(self):
        """Testing ExtensionManager.enable_extension registers static bundles
        """
        class MyTestExtensionWithBundles(Extension):
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

        extension = self.setup_extension(MyTestExtensionWithBundles)

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
        class MyTestExtensionWithContextProcessors(Extension):
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
            extension = self.setup_extension(
                MyTestExtensionWithContextProcessors)

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
            self.extension_mgr.disable_extension(extension.id)
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
        class MyTestExtensionWithModule(Extension):
            __module__ = ('djblets.extensions.tests.apps'
                          '.templatetag_tests.__init__')

        templatetags_module = \
            'djblets.extensions.tests.apps.templatetag_tests.templatetags'

        def _check_state(enabled):
            if enabled:
                self.assertEqual(
                    Template(template_str).render(Context({})),
                    'Hello, world!')
            else:
                with self.assertRaisesRegex(TemplateSyntaxError,
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
        extension = self.setup_extension(MyTestExtensionWithModule)

        _check_state(enabled=True)

        # Shutting down the extension should remove the template tags module
        # and clear the cache.
        self.extension_mgr.disable_extension(extension.id)

        _check_state(enabled=False)

        # Other libraries should still work.
        Template('{% load djblets_js djblets_extensions %}').render(
            Context({}))

    def test_enable_extension_evolve_with_models(self):
        """Testing ExtensionManager.enable_extension synchronizes database
        models
        """
        self.spy_on(Evolver.evolve,
                    owner=Evolver)

        class MyTestExtensionWithApps(Extension):
            apps = [
                'djblets.extensions.tests.apps.model_tests',
            ]

        extension = self.setup_extension(MyTestExtensionWithApps)

        self.assertTrue(Evolver.evolve.called)

        from djblets.extensions.tests.apps.model_tests.models import \
            MyTestExtensionModel

        # We should be able to create entries and query them.
        MyTestExtensionModel.objects.create(test_field='test')
        self.assertEqual(MyTestExtensionModel.objects.count(), 1)

        # Re-enabling shouldn't break anything.
        self.extension_mgr.disable_extension(extension.id)
        self.extension_mgr.enable_extension(extension.id)
        self.assertEqual(MyTestExtensionModel.objects.count(), 1)

    def test_enable_extension_evolve_without_models(self):
        """Testing ExtensionManager.enable_extension does not synchronize
        database models if extension does not have any
        """
        self.spy_on(Evolver.evolve,
                    owner=Evolver)

        class MyTestExtensionWithApps(Extension):
            apps = [
                'djblets.extensions.tests.apps',
            ]

        self.setup_extension(MyTestExtensionWithApps)

        self.assertFalse(Evolver.evolve.called)

    def test_enable_extension_evolve_with_pending_evolutions(self):
        """Testing ExtensionManager.enable_extension evolves database models
        when pending evolutions found
        """
        from django_evolution.models import Version
        from django_evolution.signature import AppSignature, ModelSignature

        self.spy_on(Evolver.evolve,
                    owner=Evolver)

        class MyTestExtensionWithApps(Extension):
            apps = [
                'djblets.extensions.tests.apps.evolve_tests',
            ]

        # We need to set some initial state in the database for the model and
        # for the evolution history.
        connection.cursor().execute(
            'CREATE TABLE evolve_tests_testevolveextensionmodel ('
            '    id INTEGER PRIMARY KEY AUTOINCREMENT,'
            '    test_field VARCHAR(16) NOT NULL'
            ')')

        from djblets.extensions.tests.apps.evolve_tests.models import \
            TestEvolveExtensionModel

        latest_version = Version.objects.current_version()

        model_sig = ModelSignature.from_model(TestEvolveExtensionModel)
        model_sig.remove_field_sig('new_field')

        app_sig = AppSignature(app_id='evolve_tests')
        app_sig.add_model_sig(model_sig)

        latest_version.signature.add_app_sig(app_sig)
        latest_version.save()

        # We can now enable the extension, which will perform an evolution.
        extension = self.setup_extension(MyTestExtensionWithApps)

        self.assertTrue(Evolver.evolve.called)

        # We should be able to create entries and query them.
        TestEvolveExtensionModel.objects.create(test_field='test')
        self.assertEqual(TestEvolveExtensionModel.objects.count(), 1)

        # We're now going to shut down and re-enable, but with a different
        # version of the model. This should trigger an evolution sequence.
        self.extension_mgr.disable_extension(extension.id)

        self.extension_mgr.enable_extension(extension.id)

        TestEvolveExtensionModel.objects.create(test_field='test',
                                                new_field=100)
        self.assertEqual(TestEvolveExtensionModel.objects.count(), 2)

        obj = TestEvolveExtensionModel.objects.get(pk=2)
        self.assertEqual(obj.new_field, 100)

    def test_enable_extension_evolve_with_applied_evolutions(self):
        """Testing ExtensionManager.enable_extension evolves database models
        when all evolutions are already applied
        """
        from django_evolution.models import Evolution, Version
        from django_evolution.signature import AppSignature, ModelSignature

        self.spy_on(Evolver.evolve,
                    owner=Evolver)

        class MyTestExtensionWithApps(Extension):
            apps = [
                'djblets.extensions.tests.apps.evolve_tests',
            ]

        # We need to set some initial state in the database for the model and
        # for the evolution history.
        connection.cursor().execute(
            'CREATE TABLE evolve_tests_testevolveextensionmodel ('
            '    id INTEGER PRIMARY KEY AUTOINCREMENT,'
            '    test_field VARCHAR(16) NOT NULL'
            ')')

        from djblets.extensions.tests.apps.model_tests.models import \
            MyTestExtensionModel

        latest_version = Version.objects.current_version()
        signature = latest_version.signature.clone()

        model_sig = ModelSignature.from_model(MyTestExtensionModel)
        model_sig.model_name = 'TestEvolveExtensionModel'
        model_sig.table_name = 'evolve_tests_testevolveextensionmodel'

        app_sig = AppSignature(app_id='evolve_tests')
        app_sig.add_model_sig(model_sig)
        signature.add_app_sig(app_sig)

        version = Version.objects.create(signature=signature)
        Evolution.objects.create(version=version,
                                 app_label='evolve_tests',
                                 label='add_new_field')

        # We can now enable the extension, which will perform an evolution.
        self.setup_extension(MyTestExtensionWithApps)

        self.assertFalse(Evolver.evolve.called)

    def test_disable_unregisters_static_bundles(self):
        """Testing ExtensionManager unregisters static bundles when disabling
        extension
        """
        class MyTestExtensionWithBundles(Extension):
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

        extension = self.setup_extension(MyTestExtensionWithBundles)

        self.assertEqual(len(pipeline_settings.STYLESHEETS), 1)
        self.assertEqual(len(pipeline_settings.JAVASCRIPT), 1)

        self.extension_mgr.disable_extension(extension.id)

        self.assertEqual(len(pipeline_settings.STYLESHEETS), 0)
        self.assertEqual(len(pipeline_settings.JAVASCRIPT), 0)

    def test_extension_list_sync(self):
        """Testing ExtensionManager extension list synchronization
        cross-process
        """
        key = 'extension-list-sync'

        manager1 = ExtensionManager(key)
        manager2 = ExtensionManager(key)

        with self.scanned_extensions([MyTestExtension],
                                     extension_mgr=manager1):
            manager1.load()

        with self.scanned_extensions([MyTestExtension],
                                     extension_mgr=manager2):
            manager2.load()

        self.assertEqual(len(manager1.get_installed_extensions()), 1)
        self.assertEqual(len(manager2.get_installed_extensions()), 1)
        self.assertEqual(len(manager1.get_enabled_extensions()), 0)
        self.assertEqual(len(manager2.get_enabled_extensions()), 0)

        manager1.enable_extension(MyTestExtension.id)
        self.assertEqual(len(manager1.get_enabled_extensions()), 1)
        self.assertEqual(len(manager2.get_enabled_extensions()), 0)

        self.assertFalse(manager1.is_expired())
        self.assertTrue(manager2.is_expired())

        with self.scanned_extensions([MyTestExtension],
                                     extension_mgr=manager2):
            manager2.load(full_reload=True)

        self.assertEqual(len(manager1.get_enabled_extensions()), 1)
        self.assertEqual(len(manager2.get_enabled_extensions()), 1)
        self.assertFalse(manager1.is_expired())
        self.assertFalse(manager2.is_expired())

    def test_extension_settings_sync(self):
        """Testing ExtensionManager extension settings synchronization
        cross-process
        """
        key = 'extension-settings-sync'
        setting_key = 'foo'
        setting_val = 'abc123'

        manager1 = ExtensionManager(key)
        manager2 = ExtensionManager(key)

        with self.scanned_extensions([MyTestExtension],
                                     extension_mgr=manager1):
            manager1.load()

        extension1 = manager1.enable_extension(MyTestExtension.id)

        with self.scanned_extensions([MyTestExtension],
                                     extension_mgr=manager2):
            manager2.load()

        self.assertFalse(manager1.is_expired())
        self.assertFalse(manager2.is_expired())

        extension2 = manager2.get_enabled_extension(MyTestExtension.id)
        self.assertNotEqual(extension2, None)

        self.assertNotIn(setting_key, extension1.settings)
        self.assertNotIn(setting_key, extension2.settings)
        extension1.settings[setting_key] = setting_val
        extension1.settings.save()

        self.assertNotIn(setting_key, extension2.settings)

        self.assertFalse(manager1.is_expired())
        self.assertTrue(manager2.is_expired())

        with self.scanned_extensions([MyTestExtension],
                                     extension_mgr=manager2):
            manager2.load(full_reload=True)

        extension2 = manager2.get_enabled_extension(MyTestExtension.id)

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
        key = 'check-expired-test'
        manager1 = ExtensionManager(key)
        manager2 = ExtensionManager(key)

        with self.scanned_extensions([MyTestExtension],
                                     extension_mgr=manager1):
            manager1.load()

        manager1.enable_extension(MyTestExtension.id)

        with self.scanned_extensions([MyTestExtension],
                                     extension_mgr=manager2):
            manager2.load()

        self.assertEqual(manager1._gen_sync.sync_gen,
                         manager2._gen_sync.sync_gen)

        # Trigger a save whenever the extension initializes.
        MyTestExtension.initialize = lambda ext: ext.settings.save()

        # Bump the generation number.
        extension = manager2.get_enabled_extension(MyTestExtension.id)
        extension.settings.save()
        self.assertNotEqual(manager1._gen_sync.sync_gen,
                            manager2._gen_sync.sync_gen)

        # Loading now should retain the new sync generation number, instead
        # of bumping it.
        with self.scanned_extensions([MyTestExtension],
                                     extension_mgr=manager1):
            manager1.load(full_reload=True)

        self.assertEqual(manager1._gen_sync.sync_gen,
                         manager2._gen_sync.sync_gen)

    def _rebuild_media_dirs(self, extension):
        """Rebuild the static media directories for an extension.

        This will erase the existing directories, if they exist, and then
        create a new directory for the tests.

        Args:
            extension (djblets.extensions.extension.Extension):
                The extension being tested.
        """
        path = extension.info.installed_static_path

        self.assertTrue(os.path.isabs(path))

        if os.path.exists(path):
            shutil.rmtree(path)

        os.makedirs(extension.info.installed_static_path, 0o755)

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

        try:
            main_connection.inc_thread_sharing()

            self.exceptions = []

            t1 = threading.Thread(target=_thread_main,
                                  args=[main_connection, main_func, 0.2])
            t2 = threading.Thread(target=_thread_main,
                                  args=[main_connection, main_func, 0.1])
            t1.start()
            t2.start()
            t1.join()
            t2.join()
        finally:
            main_connection.dec_thread_sharing()

    def _sleep_and_call(self, manager, orig_func, *args, **kwargs):
        # This works well enough to throw a monkey wrench into things.
        # One thread will be slightly ahead of the other.
        time.sleep(0.2)

        try:
            orig_func(*args, **kwargs)
        except Exception as e:
            logger.error('%s\n', e, exc_info=True)
            self.exceptions.append(e)

    def _spy_sleep_and_call(self, func):
        def _call(manager, *args, **kwargs):
            self._sleep_and_call(manager, orig_func, *args, **kwargs)

        orig_func = func

        self.spy_on(func, call_fake=_call)
