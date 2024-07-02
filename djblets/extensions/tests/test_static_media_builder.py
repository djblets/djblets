"""Unit tests for StaticMediaBuilder.

Version Added:
    5.0
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

import djblets
from djblets.extensions.packaging.static_media import (StaticMediaBuildContext,
                                                       StaticMediaBuilder)
from djblets.testing.testcases import TestCase


class StaticMediaBuilderTests(TestCase):
    """Unit tests for StaticMediaBuilder.

    Version Added:
        5.0
    """

    base_dir: Optional[Path]
    build_context: Optional[StaticMediaBuildContext]
    builder: Optional[StaticMediaBuilder]

    def setUp(self) -> None:
        super().setUp()

        base_dir = Path(tempfile.mkdtemp())
        self.base_dir = base_dir

        self.build_context = StaticMediaBuildContext(
            package_id='my-package',
            css_bundles={},
            js_bundles={},
            source_root_dir=base_dir,
            static_dir=base_dir / 'static')

        self.builder = StaticMediaBuilder(build_context=self.build_context)

    def tearDown(self) -> None:
        base_dir = self.base_dir
        assert base_dir

        shutil.rmtree(base_dir)

        self.base_dir = None
        self.build_context = None
        self.builder = None

        super().tearDown()

    def test_ensure_build_files(self) -> None:
        """Testing StaticMediaBuilder.ensure_build_files"""
        base_dir = self.base_dir
        builder = self.builder

        assert base_dir is not None
        assert builder is not None

        builder.ensure_build_files()

        self.assertTrue((base_dir / 'build').is_dir())

        workspaces_path = base_dir / '.npm-workspaces'
        djblets_path = workspaces_path / 'djblets'
        self.assertTrue(djblets_path.is_symlink())
        self.assertEqual(Path(os.readlink(djblets_path)),
                         Path(djblets.__file__).parent)

        package_json_path = base_dir / 'package.json'
        self.assertTrue(package_json_path.exists())

        with package_json_path.open('r') as fp:
            self.assertEqual(
                json.load(fp),
                {
                    'name': 'my-package',
                    'private': True,
                    'workspaces': [
                        '.npm-workspaces/*',
                    ],
                })

    def test_build_lessc_args(self) -> None:
        """Testing StaticMediaBuilder._build_lessc_args"""
        builder = self.builder
        build_context = self.build_context
        assert builder is not None
        assert build_context is not None

        djblets_path = Path(djblets.__file__).parent

        self.assertEqual(builder._build_lessc_args(), [
            '--no-color',
            '--source-map',
            '--js',
            '--autoprefix',
            '--include-path=%s:%s:%s' % (djblets_path,
                                         djblets_path / 'static',
                                         build_context.node_modules_dir),
            '--global-var=DEBUG=false',
            '--global-var=STATIC_ROOT="/static/"',
        ])

    def test_serialize_lessc_value_with_str(self) -> None:
        """Testing StaticMediaBuilder._serialize_lessc_value with string"""
        builder = self.builder
        assert builder is not None

        self.assertEqual(builder._serialize_lessc_value('hi\'there"!"'),
                         '"hi\'there\\"!\\""')

    def test_serialize_lessc_value_with_bool_true(self) -> None:
        """Testing StaticMediaBuilder._serialize_lessc_value with True bool"""
        builder = self.builder
        assert builder is not None

        self.assertEqual(builder._serialize_lessc_value(True), 'true')

    def test_serialize_lessc_value_with_bool_false(self) -> None:
        """Testing StaticMediaBuilder._serialize_lessc_value with False bool
        """
        builder = self.builder
        assert builder is not None

        self.assertEqual(builder._serialize_lessc_value(False), 'false')

    def test_serialize_lessc_value_with_int(self) -> None:
        """Testing StaticMediaBuilder._serialize_lessc_value with int"""
        builder = self.builder
        assert builder is not None

        self.assertEqual(builder._serialize_lessc_value(123), '123')

    def test_serialize_lessc_value_with_invalid_type(self) -> None:
        """Testing StaticMediaBuilder._serialize_lessc_value with invalid
        type
        """
        builder = self.builder
        assert builder is not None

        message = '[123] is not a valid LessCSS global variable value.'

        with self.assertRaisesMessage(TypeError, message):
            builder._serialize_lessc_value([123])  # type: ignore
