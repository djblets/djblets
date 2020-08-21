"""Unit tests for djblets.extensions.manager.ExtensionManager."""

from __future__ import unicode_literals

import errno
import logging
import os
import shutil
import tempfile
import threading
import time

from django.conf import settings
from django.db import connection
from django.template import Context, Template, TemplateSyntaxError
from django.test.utils import override_settings
from django_evolution.evolve import Evolver
from kgb import SpyAgency
from pipeline.conf import settings as pipeline_settings

try:
    # Django >= 1.6, <= 1.8
    from django.template.base import get_templatetags_modules
except ImportError:
    # Django >= 1.9
    get_templatetags_modules = None

from djblets.extensions.errors import EnablingExtensionError
from djblets.extensions.extension import Extension
from djblets.extensions.hooks import URLHook
from djblets.extensions.manager import (get_extension_managers,
                                        logger as manager_logger)
from djblets.extensions.tests.base import (ExtensionTestsMixin,
                                           FakeEntryPoint,
                                           TestExtensionManager)
from djblets.testing.testcases import TestCase


class TestExtension(Extension):
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


class HooksTestExtension(TestExtension):
    def initialize(self):
        self.url_hook = URLHook(self, ())


class ExtensionManagerTests(SpyAgency, ExtensionTestsMixin, TestCase):
    """Unit tests for djblets.extensions.manager.ExtensionManager."""

    def tearDown(self):
        super(ExtensionManagerTests, self).tearDown()

        self.assertEqual(len(URLHook.hooks), 0)

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
        # NOTE: We're not using HooksTestExtension here, because we want to
        #       manually set up a hook and not have to return once we
        #       perform a reload.
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
        'djblets.extensions.tests.test_extension_manager.TestExtension',
    ])
    def test_load_with_enabled_by_default(self):
        """Testing ExtensionManager.load with
        settings.EXTENSIONS_ENABLED_BY_DEFAULT
        """
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

    def test_load_with_admin_site_failure(self):
        """Testing ExtensionManager.load with extension error setting up
        admin site
        """
        class AdminSiteTestExtension(HooksTestExtension):
            has_admin_site = True

        def _init_admin_site(*args, **kwargs):
            raise Exception('admin site failed!')

        extension = self.setup_extension(AdminSiteTestExtension)
        manager = self.manager

        self.assertEqual(manager.get_installed_extensions(),
                         [AdminSiteTestExtension])
        self.assertEqual(manager.get_enabled_extensions(), [extension])
        self.assertIs(AdminSiteTestExtension.instance, extension)
        self.assertEqual(len(URLHook.hooks), 1)

        self.spy_on(TestExtensionManager._init_admin_site,
                    owner=TestExtensionManager,
                    call_fake=_init_admin_site)

        self.manager.load(full_reload=True)

        self.assertEqual(manager.get_installed_extensions(),
                         [AdminSiteTestExtension])
        self.assertEqual(manager.get_enabled_extensions(), [])
        self.assertIsNone(AdminSiteTestExtension.instance)
        self.assertEqual(len(URLHook.hooks), 0)
        self.assertTrue(manager._load_errors[extension.id].startswith(
            'admin site failed!\n\nTraceback'))

    def test_load_with_admin_urls_failure(self):
        """Testing ExtensionManager.load with extension error setting up
        admin URLs
        """
        def _install_admin_urls(*args, **kwargs):
            raise Exception('admin URLs failed!')

        extension = self.setup_extension(HooksTestExtension)
        manager = self.manager

        self.assertEqual(manager.get_installed_extensions(),
                         [HooksTestExtension])
        self.assertEqual(manager.get_enabled_extensions(), [extension])
        self.assertIs(HooksTestExtension.instance, extension)
        self.assertEqual(len(URLHook.hooks), 1)
        self.assertEqual(manager._load_errors, {})

        self.spy_on(TestExtensionManager._install_admin_urls,
                    owner=TestExtensionManager,
                    call_fake=_install_admin_urls)

        self.manager.load(full_reload=True)

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
        extension = self.setup_extension(TestExtension, enable=False)
        extension.registration.installed = True
        extension.registration.save()

        self.assertNotIn(self.manager.VERSION_SETTINGS_KEY, extension.settings)
        extension.settings.set(self.manager.VERSION_SETTINGS_KEY, '100.0')
        extension.settings.save()

        self.spy_on(self.manager._sync_database, call_original=False)
        self.spy_on(manager_logger.warning)

        extension = self.manager.enable_extension(TestExtension.id)

        self.assertTrue(extension.registration.installed)
        self.assertFalse(self.manager._sync_database.called)
        self.assertIn(self.manager.VERSION_SETTINGS_KEY, extension.settings)
        self.assertEqual(extension.settings[self.manager.VERSION_SETTINGS_KEY],
                         '100.0')
        self.assertIn('is older than the version recorded',
                      manager_logger.warning.spy.calls[-1].args[0])

    def test_install_extension_media_with_no_version_file(self):
        """Testing ExtensionManager installs media when no version file exists
        in the media directory (new install or upgrade from pre-version file)
        """
        extension = self.setup_extension(TestExtension, enable=False)
        extension.registration.installed = True
        extension.registration.enabled = True
        extension.registration.save()
        TestExtension.instance = extension

        self._rebuild_media_dirs(extension)

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
        extension = self.setup_extension(TestExtension, enable=False)
        extension.registration.installed = True
        extension.registration.enabled = True
        extension.registration.save()
        TestExtension.instance = extension

        self._rebuild_media_dirs(extension)

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
        extension = self.setup_extension(TestExtension, enable=False)
        extension.registration.installed = True
        extension.registration.enabled = True
        extension.registration.save()
        TestExtension.instance = extension

        self._rebuild_media_dirs(extension)

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

    def test_install_extension_media_with_permission_error(self):
        """Testing ExtensionManager media installation with permission error
        when copying media files
        """
        self.assertEqual(len(URLHook.hooks), 0)
        extension = self.setup_extension(HooksTestExtension, enable=False)
        extension.shutdown()

        manager = self.manager

        self.assertEqual(len(URLHook.hooks), 0)

        self._rebuild_media_dirs(extension)

        manager.should_install_static_media = True

        def _copytree(*args, **kwargs):
            raise shutil.Error()

        self.spy_on(manager.install_extension_media)
        self.spy_on(extension.info.has_resource,
                    call_fake=lambda *args, **kwargs: True)
        self.spy_on(shutil.copytree, call_fake=_copytree)

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
            manager.enable_extension(HooksTestExtension.id)

        self.assertFalse(extension.registration.installed)
        self.assertEqual(len(manager.install_extension_media.calls), 1)
        self.assertFalse(os.path.exists(
            os.path.join(extension.info.installed_static_path, '.version')))
        self.assertEqual(manager.get_installed_extensions(),
                         [HooksTestExtension])
        self.assertEqual(manager.get_enabled_extensions(), [])
        self.assertIsNone(HooksTestExtension.instance)
        self.assertEqual(len(URLHook.hooks), 0)

    def test_install_extension_media_with_lock_error(self):
        """Testing ExtensionManager media installation with error when locking
        static directory
        """
        extension = self.setup_extension(HooksTestExtension, enable=False)
        extension.shutdown()

        manager = self.manager

        self._rebuild_media_dirs(extension)

        manager.should_install_static_media = True
        manager._MEDIA_LOCK_SLEEP_TIME_SECS = 0

        def _open_lock_file(*args, **kwargs):
            raise IOError(errno.EAGAIN, 'Try again')

        self.spy_on(manager.install_extension_media)
        self.spy_on(manager._install_extension_media_internal,
                    call_original=False)
        self.spy_on(manager._open_lock_file,
                    call_fake=_open_lock_file)

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
            manager.enable_extension(HooksTestExtension.id)

        self.assertFalse(extension.registration.installed)

        self.assertEqual(len(manager.install_extension_media.calls), 1)
        self.assertFalse(manager._install_extension_media_internal.called)

        self.assertFalse(os.path.exists(
            os.path.join(extension.info.installed_static_path, '.version')))

        self.assertEqual(manager.get_installed_extensions(),
                         [HooksTestExtension])
        self.assertEqual(manager.get_enabled_extensions(), [])
        self.assertIsNone(HooksTestExtension.instance)
        self.assertEqual(len(URLHook.hooks), 0)

    def test_install_media_concurrent_threads(self):
        """Testing ExtensionManager installs media safely with multiple
        threads
        """
        # Manually mark the extension as installed and enabled without going
        # through the enable process, since we don't want to trigger any
        # static media saving yet.
        extension = self.setup_extension(TestExtension, enable=False)
        extension.registration.installed = True
        extension.registration.enabled = True
        extension.registration.save()
        TestExtension.instance = extension

        self._rebuild_media_dirs(extension)

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
        extension = self.setup_extension(TestExtension, enable=False)
        extension.registration.installed = True
        extension.registration.enabled = True
        extension.registration.save()
        TestExtension.instance = extension

        self._rebuild_media_dirs(extension)

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
        class TestExtensionWithBundles(Extension):
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

        extension = self.setup_extension(TestExtensionWithBundles)

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
        class TestExtensionWithContextProcessors(Extension):
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
                TestExtensionWithContextProcessors)

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
        class TestExtensionWithModule(Extension):
            __module__ = ('djblets.extensions.tests.apps'
                          '.templatetag_tests.__init__')

        templatetags_module = \
            'djblets.extensions.tests.apps.templatetag_tests.templatetags'

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
        extension = self.setup_extension(TestExtensionWithModule)

        _check_state(enabled=True)

        # Shutting down the extension should remove the template tags module
        # and clear the cache.
        self.manager.disable_extension(extension.id)

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

        class TestExtensionWithApps(Extension):
            apps = [
                'djblets.extensions.tests.apps.model_tests',
            ]

        extension = self.setup_extension(TestExtensionWithApps)

        self.assertTrue(Evolver.evolve.called)

        from djblets.extensions.tests.apps.model_tests.models import \
            TestExtensionModel

        # We should be able to create entries and query them.
        TestExtensionModel.objects.create(test_field='test')
        self.assertEqual(TestExtensionModel.objects.count(), 1)

        # Re-enabling shouldn't break anything.
        self.manager.disable_extension(extension.id)
        self.manager.enable_extension(extension.id)
        self.assertEqual(TestExtensionModel.objects.count(), 1)

    def test_enable_extension_evolve_without_models(self):
        """Testing ExtensionManager.enable_extension does not synchronize
        database models if extension does not have any
        """
        self.spy_on(Evolver.evolve,
                    owner=Evolver)

        class TestExtensionWithApps(Extension):
            apps = [
                'djblets.extensions.tests.apps',
            ]

        self.setup_extension(TestExtensionWithApps)

        self.assertFalse(Evolver.evolve.called)

    def test_enable_extension_evolve_with_pending_evolutions(self):
        """Testing ExtensionManager.enable_extension evolves database models
        when pending evolutions found
        """
        from django_evolution.models import Version
        from django_evolution.signature import AppSignature, ModelSignature

        self.spy_on(Evolver.evolve,
                    owner=Evolver)

        class TestExtensionWithApps(Extension):
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
        extension = self.setup_extension(TestExtensionWithApps)

        self.assertTrue(Evolver.evolve.called)

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

    def test_enable_extension_evolve_with_applied_evolutions(self):
        """Testing ExtensionManager.enable_extension evolves database models
        when all evolutions are already applied
        """
        from django_evolution.models import Evolution, Version
        from django_evolution.signature import AppSignature, ModelSignature

        self.spy_on(Evolver.evolve,
                    owner=Evolver)

        class TestExtensionWithApps(Extension):
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
            TestExtensionModel

        latest_version = Version.objects.current_version()
        signature = latest_version.signature.clone()

        model_sig = ModelSignature.from_model(TestExtensionModel)
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
        self.setup_extension(TestExtensionWithApps)

        self.assertFalse(Evolver.evolve.called)

    def test_disable_unregisters_static_bundles(self):
        """Testing ExtensionManager unregisters static bundles when disabling
        extension
        """
        class TestExtensionWithBundles(Extension):
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

        extension = self.setup_extension(TestExtensionWithBundles)

        self.assertEqual(len(pipeline_settings.STYLESHEETS), 1)
        self.assertEqual(len(pipeline_settings.JAVASCRIPT), 1)

        self.manager.disable_extension(extension.id)

        self.assertEqual(len(pipeline_settings.STYLESHEETS), 0)
        self.assertEqual(len(pipeline_settings.JAVASCRIPT), 0)

    def test_extension_list_sync(self):
        """Testing ExtensionManager extension list synchronization
        cross-process
        """
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

        print('*** Reloading')
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

        os.mkdir(extension.info.installed_static_path, 0o755)

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
