"""Unit tests for djblets.extensions.settings.ExtensionSettings."""

from __future__ import unicode_literals

from mock import Mock

from djblets.extensions.settings import ExtensionSettings
from djblets.extensions.signals import settings_saved
from djblets.testing.testcases import TestCase


class ExtensionSettingsTest(TestCase):
    """Unit tests for djblets.extensions.settings.ExtensionSettings."""

    def setUp(self):
        # Build up a mocked extension
        self.extension = Mock()
        self.extension.registration = Mock()
        self.test_dict = {
            'test_key1': 'test_value1',
            'test_key2': 'test_value2',
        }
        self.extension.registration.settings = self.test_dict
        self.settings = ExtensionSettings(self.extension)

    def test_constructor(self):
        """Testing ExtensionSettings construction"""
        self.assertEqual(self.extension, self.settings.extension)

        # Ensure that the registration settings dict got added.
        self.assertEqual(self.test_dict['test_key1'],
                         self.settings['test_key1'])

    def test_load_updates_dict(self):
        """Testing ExtensionSettings.load correctly updates core dict"""
        new_dict = {
            'test_new_key': 'test_new_value',
            'test_key1': 'new_value',
        }
        self.extension.registration.settings = new_dict
        self.settings.load()

        # Should have added test_new_key, and modified test_key1.
        self.assertEqual(new_dict['test_new_key'],
                         self.settings['test_new_key'])
        self.assertEqual(new_dict['test_key1'], self.settings['test_key1'])

        # Should have left test_key2 alone.
        self.assertEqual(self.test_dict['test_key2'],
                         self.settings['test_key2'])

    def test_load_silently_discards(self):
        """Testing ExtensionSettings.load silently ignores invalid settings"""
        some_string = 'This is a string'
        self.extension.registration.settings = some_string

        try:
            self.settings.load()
        except Exception:
            self.fail("Shouldn't have raised an exception")

    def test_save_updates_database(self):
        """Testing ExtensionSettings.save will correctly update registration"""
        registration = self.extension.registration
        self.settings['test_new_key'] = 'Test new value'
        generated_dict = dict(self.settings)
        self.settings.save()

        self.assertTrue(registration.save.called)
        self.assertEqual(generated_dict, registration.settings)

    def test_save_emits_settings_saved_signal(self):
        """Testing ExtensionSettings.save emits the settings_saved signal"""
        saw = {}

        def on_settings_saved(*args, **kwargs):
            saw['signal'] = True

        settings_saved.connect(on_settings_saved, sender=self.extension)

        self.settings['test_new_key'] = 'Test new value'
        self.settings.save()

        self.assertIn('signal', saw)
