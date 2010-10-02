import os


from django.conf import settings
from django.core import urlresolvers
from django.core.exceptions import ImproperlyConfigured
from djblets.extensions.base import Extension, ExtensionInfo, Settings
from djblets.testing.testcases import TestCase
from mock import Mock, patch_object


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


class TestExtension(Extension):
    """A dummy extension to test with"""
    registration = Mock()
    registration.settings = dict()


class ExtensionTest(TestCase):
    def setUp(self):
        self.extension = TestExtension()

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


class TestExtensionInfo(TestCase):
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

        self.test_htdocs_path = os.path.join(settings.EXTENSIONS_MEDIA_ROOT,
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
