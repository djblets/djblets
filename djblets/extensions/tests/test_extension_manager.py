"""Unit tests for djblets.extensions.manager.ExtensionManager."""

from __future__ import unicode_literals

import logging
import os
import shutil
import threading
import time

import django
import nose
from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.template import Context, Template, TemplateSyntaxError
from django.test.utils import override_settings
from django.utils.six.moves import cPickle as pickle
from kgb import SpyAgency
from pipeline.conf import settings as pipeline_settings

try:
    # Django >= 1.6, <= 1.8
    from django.template.base import get_templatetags_modules
except ImportError:
    # Django >= 1.9
    get_templatetags_modules = None

try:
    import django_evolution
except ImportError:
    django_evolution = None

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


class ExtensionManagerTests(SpyAgency, ExtensionTestsMixin, TestCase):
    """Unit tests for djblets.extensions.manager.ExtensionManager."""

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

        # Re-create the directories.
        shutil.rmtree(extension.info.installed_static_path)
        os.mkdir(extension.info.installed_static_path, 0o755)

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

        # Re-create the directories.
        shutil.rmtree(extension.info.installed_static_path)
        os.mkdir(extension.info.installed_static_path, 0o755)

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

        # Re-create the directories.
        shutil.rmtree(extension.info.installed_static_path)
        os.mkdir(extension.info.installed_static_path, 0o755)

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
        extension = self.setup_extension(TestExtension, enable=False)
        extension.registration.installed = True
        extension.registration.enabled = True
        extension.registration.save()
        TestExtension.instance = extension

        # Re-create the directories.
        shutil.rmtree(extension.info.installed_static_path)
        os.mkdir(extension.info.installed_static_path, 0o755)

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

    def test_enable_extension_syncdb_with_models(self):
        """Testing ExtensionManager.enable_extension synchronizes database
        models
        """
        self.spy_on(call_command)

        class TestExtensionWithApps(Extension):
            apps = [
                'djblets.extensions.tests.apps.model_tests',
            ]

        extension = self.setup_extension(TestExtensionWithApps)

        # There should be a call to call_command for either syncdb or
        # migrate (depending on Django version). Note that syncdb at least
        # will perform its own calls, so we don't want to expect a certain
        # number of calls.
        if django.VERSION[:2] >= (1, 7):
            self.assertTrue(call_command.called_with('migrate'))
        else:
            self.assertTrue(call_command.called_with('syncdb'))

        from djblets.extensions.tests.apps.model_tests.models import \
            TestExtensionModel

        # We should be able to create entries and query them.
        TestExtensionModel.objects.create(test_field='test')
        self.assertEqual(TestExtensionModel.objects.count(), 1)

        # Re-enabling shouldn't break anything.
        self.manager.disable_extension(extension.id)
        self.manager.enable_extension(extension.id)
        self.assertEqual(TestExtensionModel.objects.count(), 1)

    def test_enable_extension_syncdb_without_models(self):
        """Testing ExtensionManager.enable_extension does not synchronize
        database models if extension does not have any
        """
        self.spy_on(call_command)

        class TestExtensionWithApps(Extension):
            apps = [
                'djblets.extensions.tests.apps',
            ]

        self.setup_extension(TestExtensionWithApps)

        self.assertFalse(call_command.called)

    def test_enable_extension_evolve_with_pending_evolutions(self):
        """Testing ExtensionManager.enable_extension evolves database models
        when pending evolutions found
        """
        if django_evolution is None:
            raise nose.SkipTest()

        from django_evolution.models import Version
        from django_evolution.signature import create_model_sig

        self.spy_on(call_command)

        class TestExtensionWithApps(Extension):
            apps = [
                'djblets.extensions.tests.apps.evolve_tests',
            ]

        # We need to set some initial state in the database for the model and
        # for the evolution history.
        connection.cursor().execute(
            'CREATE TABLE evolve_tests_testextensionmodel ('
            '    id INTEGER PRIMARY KEY AUTOINCREMENT,'
            '    test_field VARCHAR(16) NOT NULL'
            ')')

        from djblets.extensions.tests.apps.model_tests.models import \
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
        extension = self.setup_extension(TestExtensionWithApps)

        self.assertTrue(call_command.called_with('evolve'))

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

    def test_enable_extension_evolve_with_applied_evolutions(self):
        """Testing ExtensionManager.enable_extension evolves database models
        when all evolutions are already applied
        """
        if django_evolution is None:
            raise nose.SkipTest()

        from django_evolution.models import Evolution, Version
        from django_evolution.signature import create_model_sig

        self.spy_on(call_command)

        class TestExtensionWithApps(Extension):
            apps = [
                'djblets.extensions.tests.apps.evolve_tests',
            ]

        # We need to set some initial state in the database for the model and
        # for the evolution history.
        connection.cursor().execute(
            'CREATE TABLE evolve_tests_testextensionmodel ('
            '    id INTEGER PRIMARY KEY AUTOINCREMENT,'
            '    test_field VARCHAR(16) NOT NULL'
            ')')

        from djblets.extensions.tests.apps.model_tests.models import \
            TestExtensionModel

        latest_version = Version.objects.current_version()
        sig = pickle.loads(bytes(latest_version.signature))

        model_sig = create_model_sig(TestExtensionModel)
        model_sig['meta']['db_table'] = 'evolve_tests_testevolveextensionmodel'

        sig['evolve_tests'] = {
            'TestEvolveExtensionModel': model_sig,
        }

        version = Version.objects.create(signature=pickle.dumps(sig))
        Evolution.objects.create(version=version,
                                 app_label='evolve_tests',
                                 label='add_new_field')

        # We can now enable the extension, which will perform an evolution.
        self.setup_extension(TestExtensionWithApps)

        self.assertFalse(call_command.called_with('evolve'))

    def test_enable_extension_evolve_without_evolutions(self):
        """Testing ExtensionManager.enable_extension does not evolve database
        models if extension does not have evolutions
        """
        if django_evolution is None:
            raise nose.SkipTest()

        self.spy_on(call_command)

        class TestExtension(Extension):
            apps = [
                'djblets.extensions.test.model_tests',
            ]

        self.setup_extension(TestExtension)

        self.assertFalse(call_command.called_with('evolve'))

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
