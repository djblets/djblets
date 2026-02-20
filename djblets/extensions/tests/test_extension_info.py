"""Unit tests for djblets.extensions.extension.ExtensionInfo."""

from __future__ import annotations

import os
from typing import Any, TYPE_CHECKING

from django.conf import settings

import djblets
from djblets.extensions.extension import Extension, ExtensionInfo
from djblets.extensions.testing import ExtensionTestCaseMixin
from djblets.extensions.tests.base import FakeEntryPoint
from djblets.testing.testcases import TestCase

if TYPE_CHECKING:
    from collections.abc import Mapping

    from djblets.extensions.extension import ExtensionMetadata


class _DjbletsTestExtension(Extension):
    __module__ = 'djblets'
    id = 'djblets:TestExtension'


class ExtensionInfoTests(ExtensionTestCaseMixin, TestCase):
    """Unit tests for djblets.extensions.extension.ExtensionInfo."""

    def test_create_from_entrypoint(self) -> None:
        """Testing ExtensionInfo.create_from_entrypoint"""
        module_name = 'test_extension.dummy.submodule'
        package_name = 'DummyExtension'
        extension_id = f'{module_name}:DummyExtension'

        class TestExtension(Extension):
            __module__ = module_name
            id = extension_id

        entrypoint = FakeEntryPoint(TestExtension, project_name=package_name)
        extension_info = ExtensionInfo.create_from_entrypoint(entrypoint,
                                                              TestExtension)

        dist = entrypoint.dist
        assert dist is not None

        metadata = dist.metadata
        assert metadata is not None

        expected_metadata = {
            key: metadata[key]
            for key in metadata
        }

        self._check_extension_info(extension_info=extension_info,
                                   app_name='test_extension.dummy',
                                   package_name=package_name,
                                   extension_id=extension_id,
                                   metadata=expected_metadata)

    def test_create_from_entrypoint_with_custom_metadata(self) -> None:
        """Testing ExtensionInfo.create_from_entrypoint with custom
        Extension.metadata
        """
        package_name = 'DummyExtension'
        module_name = 'test_extension.dummy.submodule'
        extension_id = f'{module_name}:DummyExtension'

        class TestExtension(Extension):
            __module__ = module_name
            id = extension_id
            metadata: ExtensionMetadata = {
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

        dist = entrypoint.dist
        assert dist is not None

        metadata = dist.metadata
        assert metadata is not None

        expected_metadata = {
            key: metadata[key]
            for key in metadata
        }
        expected_metadata.update(TestExtension.metadata)

        self._check_extension_info(extension_info=extension_info,
                                   app_name='test_extension.dummy',
                                   package_name=package_name,
                                   extension_id=extension_id,
                                   metadata=expected_metadata)

    def test_create_from_entrypoint_with_broken_metadata(self) -> None:
        """Testing ExtensionInfo.create_from_entrypoint with broken
        Extension.metadata
        """
        package_name = 'DummyExtension'
        module_name = 'test_extension.dummy.submodule'
        extension_id = f'{module_name}:DummyExtension'

        class TestExtension(Extension):
            __module__ = module_name
            id = extension_id
            metadata: ExtensionMetadata = {
                'Author': 'Example Author',
                'Author-email': 'author@example.com',
                'Name': 'OverrideName',
                'Version': '3.14159',
                'Summary': 'Lorem ipsum dolor sit amet.',
                'Description': 'Tempus fugit.',
                'License': 'None',
                'Home-page': 'http://127.0.0.1/',
            }

        entrypoint = FakeEntryPoint(TestExtension,
                                    project_name=package_name,
                                    metadata={})
        extension_info = ExtensionInfo.create_from_entrypoint(entrypoint,
                                                              TestExtension)

        dist = entrypoint.dist
        assert dist is not None

        metadata = dist.metadata
        assert metadata is not None

        expected_metadata = {
            key: metadata[key]
            for key in metadata
        }
        expected_metadata.update(TestExtension.metadata)

        self._check_extension_info(extension_info=extension_info,
                                   app_name='test_extension.dummy',
                                   package_name=package_name,
                                   extension_id=extension_id,
                                   metadata=expected_metadata)

    def test_has_resource_with_file(self) -> None:
        """Testing ExtensionInfo.has_resource with file"""
        self.setup_extension(_DjbletsTestExtension, enable=False)
        assert self.extension_mgr is not None

        extension = _DjbletsTestExtension(self.extension_mgr)

        self.assertTrue(extension.info.has_resource('deprecation.py'))

    def test_has_resource_with_dir(self) -> None:
        """Testing ExtensionInfo.has_resource with directory"""
        self.setup_extension(_DjbletsTestExtension, enable=False)
        assert self.extension_mgr is not None

        extension = _DjbletsTestExtension(self.extension_mgr)

        self.assertTrue(extension.info.has_resource('extensions'))

    def test_has_resource_with_not_found(self) -> None:
        """Testing ExtensionInfo.has_resource with not found"""
        self.setup_extension(_DjbletsTestExtension, enable=False)
        assert self.extension_mgr is not None

        extension = _DjbletsTestExtension(self.extension_mgr)

        self.assertFalse(extension.info.has_resource('blarghy-blargh'))

    def test_extract_resource_with_file(self) -> None:
        """Testing ExtensionInfo.has_resource with file"""
        self.setup_extension(_DjbletsTestExtension, enable=False)
        assert self.extension_mgr is not None

        extension = _DjbletsTestExtension(self.extension_mgr)

        self.assertEqual(
            extension.info.extract_resource('deprecation.py'),
            os.path.abspath(os.path.join(djblets.__file__, '..',
                                         'deprecation.py')))

    def test_extract_resource_with_dir(self) -> None:
        """Testing ExtensionInfo.has_resource with directory"""
        self.setup_extension(_DjbletsTestExtension, enable=False)
        assert self.extension_mgr is not None

        extension = _DjbletsTestExtension(self.extension_mgr)

        self.assertEqual(
            extension.info.extract_resource('extensions'),
            os.path.abspath(os.path.join(djblets.__file__, '..',
                                         'extensions')))

    def test_extract_resource_with_not_found(self) -> None:
        """Testing ExtensionInfo.has_resource with not found"""
        self.setup_extension(_DjbletsTestExtension, enable=False)
        assert self.extension_mgr is not None

        extension = _DjbletsTestExtension(self.extension_mgr)

        self.assertIsNone(extension.info.extract_resource('blarghy-blargh'))

    def _check_extension_info(
        self,
        extension_info: ExtensionInfo,
        app_name: str,
        package_name: str,
        extension_id: str,
        metadata: Mapping[str, Any],
    ) -> None:
        """Check an ExtensionInfo result.

        Args:
            extension_info (djblets.extensions.extension.ExtensionInfo):
                The extension info result.

            app_name (str):
                The expected app name.

            package_name (str):
                The expected package name.

            extension_id (str):
                The expected extension ID.

            metadata (dict):
                The expected extension metadata.
        """
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
