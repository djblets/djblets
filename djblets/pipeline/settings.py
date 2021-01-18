"""Utilities and constants for configuring Pipeline.

Note:
    This is safe to import from a project's :file:`settings.py` without
    side effects (for instance, it will not load any Django models or apps).

Version Added:
    2.1
"""

from __future__ import unicode_literals

import os

from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import force_str


#: Default list of compilers used by Djblets.
DEFAULT_PIPELINE_COMPILERS = [
    'djblets.pipeline.compilers.es6.ES6Compiler',
    'djblets.pipeline.compilers.less.LessCompiler',
]


def build_pipeline_settings(pipeline_enabled,
                            node_modules_path,
                            static_root,
                            javascript_bundles=[],
                            stylesheet_bundles=[],
                            compilers=DEFAULT_PIPELINE_COMPILERS,
                            babel_extra_plugins=[],
                            babel_extra_args=[],
                            less_extra_args=[],
                            validate_paths=True):
    """Build a standard set of Pipeline settings.

    This can be used to create a ``PIPELINE`` settings dictionary in a
    :file:`settings.py` file based on the standard Djblets Pipeline settings,
    which makes use of Babel, LessCSS, and UglifyJS, along with a preset
    list of plugins.

    The following base set of Babel plugins are used:

    * `dedent <https://www.npmjs.com/package/babel-plugin-dedent>`_
    * `django-gettext
      <https://www.npmjs.com/package/babel-plugin-django-gettext>`_

    The following LessCSS plugin is used:

    * `autoprefix
      <https://www.npmjs.com/package/@beanbag/less-plugin-autoprefix>`_

    This will also set the value of ``node_modules_path`` in the
    :envvar:`NODE_PATH` environment variable.

    Args:
        pipeline_enabled (bool):
            Whether Pipelining of static media should be enabled.

            This must be provided by a caller. It's recommended to enable
            this if ``DEBUG`` is ``False`` (or, better, use another variable
            indicating a production vs. development environment).

        node_modules_path (unicode):
            The path to the loal :file:`node_modules` directory for the
            project.

        static_root (unicode):
            The value of the ``settings.STATIC_ROOT``. This must be provided
            explicitly, since :file:`settings.py` is likely the module
            calling this.

        javascript_bundles (list of dict, optional):
            A list of JavaScript bundle packages for Pipeline to handle.

        stylesheet_bundles (list of dict, optional):
            A list of stylesheet bundle packages for Pipeline to handle.

        compilers (list of unicode, optional):
            A list of compilers to use for static media.

        babel_extra_plugins (list of unicode, optional):
            A list of additional Babel plugins to enable.

        babel_extra_args (list of unicode, optional):
            Extra command line arguments to pass to Babel.

        less_extra_args (list of unicode, optional):
            Extra command line arguments to pass to LessCSS.

        validate_paths (bool, optional):
            Whether to validate any expected paths to binary files.

            It's recommended to set this based on ``DEBUG``, or another
            variable indicating a production vs. development environment.
    """
    babel_bin_path = os.path.join(node_modules_path, 'babel-cli', 'bin',
                                  'babel.js')
    lessc_bin_path = os.path.join(node_modules_path, 'less', 'bin', 'lessc')
    uglifyjs_bin_path = os.path.join(node_modules_path, 'uglify-js', 'bin',
                                     'uglifyjs')

    if validate_paths:
        if not os.path.exists(node_modules_path):
            raise ImproperlyConfigured(
                'node_modules could not be found at %s'
                % node_modules_path)

        if not os.path.exists(babel_bin_path):
            raise ImproperlyConfigured(
                'The babel binary could not be found at %s'
                % babel_bin_path)

        if not os.path.exists(lessc_bin_path):
            raise ImproperlyConfigured(
                'The lessc binary could not be found at %s'
                % lessc_bin_path)

        if not os.path.exists(uglifyjs_bin_path):
            raise ImproperlyConfigured(
                'The uglifyjs binary could not be found at %s'
                % uglifyjs_bin_path)

    os.environ[str('NODE_PATH')] = force_str(node_modules_path)

    babel_plugins = [
        'dedent',
        'django-gettext',
    ] + babel_extra_plugins

    return {
        'PIPELINE_ENABLED': bool(pipeline_enabled),
        'COMPILERS': compilers,
        'CSS_COMPRESSOR': None,
        'JS_COMPRESSOR': 'pipeline.compressors.uglifyjs.UglifyJSCompressor',
        'JAVASCRIPT': javascript_bundles,
        'STYLESHEETS': stylesheet_bundles,
        'BABEL_BINARY': babel_bin_path,
        'BABEL_ARGUMENTS': [
            '--presets', 'env',
            '--plugins', ','.join(babel_plugins),
            '-s', 'true',
        ] + babel_extra_args,
        'LESS_BINARY': lessc_bin_path,
        'LESS_ARGUMENTS': [
            '--include-path=%s' % static_root,
            '--no-color',
            '--source-map',
            '--js',
            '--plugin=@beanbag/less-plugin-autoprefix',
        ] + less_extra_args,
        'UGLIFYJS_BINARY': uglifyjs_bin_path,
    }
