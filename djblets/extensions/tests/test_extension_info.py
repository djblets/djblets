"""Unit tests for djblets.extensions.extension.ExtensionInfo."""

from __future__ import unicode_literals

import os

from django.conf import settings

from djblets.extensions.extension import Extension, ExtensionInfo
from djblets.extensions.tests.base import FakeEntryPoint
from djblets.testing.testcases import TestCase


class ExtensionInfoTests(TestCase):
    """Unit tests for djblets.extensions.extension.ExtensionInfo."""

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
