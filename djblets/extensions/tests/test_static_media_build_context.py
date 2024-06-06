"""Unit tests for StaticMediaBuildContext.

Version Added:
    5.0
"""

from __future__ import annotations

from pathlib import Path

from django.test.utils import override_settings

from djblets.extensions.extension import Extension
from djblets.extensions.packaging.static_media import StaticMediaBuildContext
from djblets.testing.testcases import TestCase


class MyExtension(Extension):
    css_bundles = {
        'css-bundle1': {
            'source_filenames': ('file1.css',),
            'output_filename': 'my-css-bundle1.css',
            'extra_context': {
                'abc': 'def',
            },
        },
        'css-bundle2': {
            'source_filenames': [
                'file2.css',
                'file3.css',
            ],
            'compiler_options': {
                'foo': 'bar',
            },
            'variant': 'data-uri',
        },
    }

    js_bundles = {
        'js-bundle1': {
            'source_filenames': ('file1.js',),
            'output_filename': 'my-js-bundle1.js',
            'extra_context': {
                'abc': 'def',
            },
        },
        'js-bundle2': {
            'source_filenames': [
                'file2.js',
                'file3.js',
            ],
            'compiler_options': {
                'foo': 'bar',
            },
        },
    }


class StaticMediaBuildContextTests(TestCase):
    """Unit tests for StaticMediaBuildContext.

    Version Added:
        5.0
    """

    def test_init(self) -> None:
        """Testing StaticMediaBuildContext.__init__"""
        build_context = StaticMediaBuildContext(
            package_id='my-package',
            css_bundles={
                'css-bundle1': {
                    'source_filenames': ('file1.css',),
                    'output_filename': 'my-css-bundle1.css',
                    'extra_context': {
                        'abc': 'def',
                    },
                },
                'css-bundle2': {
                    'source_filenames': [
                        'file2.css',
                        'file3.css',
                    ],
                    'compiler_options': {
                        'foo': 'bar',
                    },
                    'variant': 'data-uri',
                },
            },
            js_bundles={
                'js-bundle1': {
                    'source_filenames': ('file1.js',),
                    'output_filename': 'my-js-bundle1.js',
                    'extra_context': {
                        'abc': 'def',
                    },
                },
                'js-bundle2': {
                    'source_filenames': [
                        'file2.js',
                        'file3.js',
                    ],
                    'compiler_options': {
                        'foo': 'bar',
                    },
                },
            },
            source_root_dir=Path('/path/to/src'),
            static_dir=Path('/path/to/static'))

        self.assertEqual(build_context.package_id, 'my-package')
        self.assertEqual(str(build_context.build_dir), '/path/to/src/build')
        self.assertEqual(str(build_context.source_root_dir), '/path/to/src')
        self.assertEqual(str(build_context.workspaces_dir),
                         '/path/to/src/.npm-workspaces')
        self.assertEqual(str(build_context.node_modules_dir),
                         '/path/to/src/node_modules')
        self.assertEqual(str(build_context.static_dir), '/path/to/static')
        self.assertEqual(build_context.pipeline_css_bundles, {
            'css-bundle1': {
                'source_filenames': ['file1.css'],
                'output_filename': 'my-css-bundle1.css',
                'extra_context': {
                    'abc': 'def',
                },
            },
            'css-bundle2': {
                'source_filenames': [
                    'file2.css',
                    'file3.css',
                ],
                'output_filename': 'css/css-bundle2.min.css',
                'compiler_options': {
                    'foo': 'bar',
                },
                'variant': 'data-uri',
            },
        })
        self.assertEqual(build_context.pipeline_js_bundles, {
            'js-bundle1': {
                'source_filenames': ['file1.js'],
                'output_filename': 'my-js-bundle1.js',
                'extra_context': {
                    'abc': 'def',
                },
            },
            'js-bundle2': {
                'source_filenames': [
                    'file2.js',
                    'file3.js',
                ],
                'output_filename': 'js/js-bundle2.min.js',
                'compiler_options': {
                    'foo': 'bar',
                },
            },
        })

    def test_create_for_extension(self) -> None:
        """Testing StaticMediaBuildContext.create_for_extension"""
        build_context = StaticMediaBuildContext.create_for_extension(
            extension_cls=MyExtension,
            source_root_dir=Path('/path/to/src'))

        self.assertEqual(build_context.package_id, 'MyExtension')
        self.assertEqual(str(build_context.build_dir), '/path/to/src/build')
        self.assertEqual(str(build_context.source_root_dir), '/path/to/src')
        self.assertEqual(str(build_context.workspaces_dir),
                         '/path/to/src/.npm-workspaces')
        self.assertEqual(str(build_context.node_modules_dir),
                         '/path/to/src/node_modules')
        self.assertEqual(build_context.static_dir,
                         Path(__file__).parent / 'static')
        self.assertEqual(build_context.pipeline_css_bundles, {
            'css-bundle1': {
                'source_filenames': ['file1.css'],
                'output_filename': 'my-css-bundle1.css',
                'extra_context': {
                    'abc': 'def',
                },
            },
            'css-bundle2': {
                'source_filenames': [
                    'file2.css',
                    'file3.css',
                ],
                'output_filename': 'css/css-bundle2.min.css',
                'compiler_options': {
                    'foo': 'bar',
                },
                'variant': 'data-uri',
            },
        })
        self.assertEqual(build_context.pipeline_js_bundles, {
            'js-bundle1': {
                'source_filenames': ['file1.js'],
                'output_filename': 'my-js-bundle1.js',
                'extra_context': {
                    'abc': 'def',
                },
            },
            'js-bundle2': {
                'source_filenames': [
                    'file2.js',
                    'file3.js',
                ],
                'output_filename': 'js/js-bundle2.min.js',
                'compiler_options': {
                    'foo': 'bar',
                },
            },
        })

    def test_create_for_extension_with_overrides(self) -> None:
        """Testing StaticMediaBuildContext.create_for_extension with overrides
        """
        build_context = StaticMediaBuildContext.create_for_extension(
            extension_cls=MyExtension,
            source_root_dir=Path('/path/to/src'),
            build_dir=Path('/path/to/build'),
            package_id='my-package')

        self.assertEqual(build_context.package_id, 'my-package')
        self.assertEqual(str(build_context.build_dir), '/path/to/build')
        self.assertEqual(str(build_context.source_root_dir), '/path/to/src')
        self.assertEqual(str(build_context.workspaces_dir),
                         '/path/to/src/.npm-workspaces')
        self.assertEqual(str(build_context.node_modules_dir),
                         '/path/to/src/node_modules')
        self.assertEqual(build_context.static_dir,
                         Path(__file__).parent / 'static')
        self.assertEqual(build_context.pipeline_css_bundles, {
            'css-bundle1': {
                'source_filenames': ['file1.css'],
                'output_filename': 'my-css-bundle1.css',
                'extra_context': {
                    'abc': 'def',
                },
            },
            'css-bundle2': {
                'source_filenames': [
                    'file2.css',
                    'file3.css',
                ],
                'output_filename': 'css/css-bundle2.min.css',
                'compiler_options': {
                    'foo': 'bar',
                },
                'variant': 'data-uri',
            },
        })
        self.assertEqual(build_context.pipeline_js_bundles, {
            'js-bundle1': {
                'source_filenames': ['file1.js'],
                'output_filename': 'my-js-bundle1.js',
                'extra_context': {
                    'abc': 'def',
                },
            },
            'js-bundle2': {
                'source_filenames': [
                    'file2.js',
                    'file3.js',
                ],
                'output_filename': 'js/js-bundle2.min.js',
                'compiler_options': {
                    'foo': 'bar',
                },
            },
        })

    @override_settings(STATICFILES_DIRS=[
        '/path/to/extension1/something',
        '/path/to/extension2/static',
        '/path/to/extension3/static/subdir',
        ('test', '/path/to/extension4/test'),
    ])
    def test_get_lessc_include_path(self) -> None:
        """Testing StaticMediaBuildContext.get_lessc_include_path"""
        build_context = StaticMediaBuildContext.create_for_extension(
            extension_cls=MyExtension,
            source_root_dir=Path('/path/to/src'))

        self.assertEqual(build_context.get_lessc_include_path(), {
            '/path/to/extension1',
            '/path/to/extension2',
            '/path/to/extension3',
            '/path/to/extension3/static',
            '/path/to/extension4',
            '/path/to/src/node_modules',
        })
