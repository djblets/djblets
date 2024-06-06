"""Utilities and constants for configuring Pipeline.

Note:
    This is safe to import from a project's :file:`settings.py` without
    side effects (for instance, it will not load any Django models or apps).

Version Added:
    2.1
"""

import os
from typing import Dict, List

from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import force_str


#: Default list of compilers used by Djblets.
DEFAULT_PIPELINE_COMPILERS: List[str] = [
    'djblets.pipeline.compilers.es6.ES6Compiler',
    'djblets.pipeline.compilers.typescript.TypeScriptCompiler',
    'djblets.pipeline.compilers.less.LessCompiler',
]


def build_pipeline_settings(
    *,
    pipeline_enabled: bool,
    node_modules_path: str,
    static_root: str,
    javascript_bundles: Dict = {},
    stylesheet_bundles: Dict = {},
    compilers: List[str] = DEFAULT_PIPELINE_COMPILERS,
    babel_extra_plugins: List[str] = [],
    babel_extra_args: List[str] = [],
    less_extra_args: List[str] = [],
    validate_paths: bool = True,
    use_rollup: bool = True,
    rollup_extra_args: List[str] = [],
    extra_config: Dict = {},
) -> Dict:
    """Build a standard set of Pipeline settings.

    This can be used to create a ``PIPELINE`` settings dictionary in a
    :file:`settings.py` file based on the standard Djblets Pipeline settings.

    By default, this makes use of Babel, LessCSS, and UglifyJS, along with a
    preset list of plugins.

    The following base set of Babel plugins are used:

    * `dedent <https://www.npmjs.com/package/babel-plugin-dedent>`_
    * `django-gettext
      <https://www.npmjs.com/package/babel-plugin-django-gettext>`_

    The following LessCSS plugin is used:

    * `autoprefix
      <https://www.npmjs.com/package/@beanbag/less-plugin-autoprefix>`_

    Optionally, `rollup.js <https://www.rollupjs.org>` can be used by
    setting ``use_rollup=True``. This will make use of
    :py:class:`djblets.pipeline.rollup.RollupCompiler`, configuring it to
    automatically compile any of the following files:

    * :file:`index.js`
    * :file:`index.es6`,
    * :file:`index.es6.js`
    * :file:`index.ts`

    These modules can make use of modern JavaScript ``import``/``export``
    statements. Any relatively-imported modules will be rolled up during
    compilation for the ``index`` file.

    Note:
        These files should **not** be specified as part of the Pipeline
        bundle! Rollup will instead bundle them into the compiled index file.

    As a convenience, this function will also set the value of
    ``node_modules_path`` in the :envvar:`NODE_PATH` environment variable.

    Version Changed:
        4.0:
        * Added support for `rollup.js <https://www.rollupjs.org>`.
        * Added ``extra_config``, ``use_rollup`, and ``rollup_extra_args``
          parameters.

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

            If the :envvar:`DJBLETS_SKIP_PIPELINE_VALIDATION` environment
            variable is set to ``1``, then this will be forced to ``False``.
            This is primarily used for packaging building.
    """
    bin_path = os.path.join(node_modules_path, '.bin')
    babel_bin_path = os.path.join(bin_path, 'babel')
    lessc_bin_path = os.path.join(bin_path, 'lessc')
    rollup_bin_path = os.path.join(bin_path, 'rollup')
    uglifyjs_bin_path = os.path.join(bin_path, 'uglifyjs')

    use_lessc = (
        'djblets.pipeline.compilers.less.LessCompiler' in compilers or
        'pipeline.compilers.less.LessCompiler' in compilers
    )

    if use_rollup:
        # Make sure that rollup is before any other JavaScript compilers.
        compilers = [
            'djblets.pipeline.compilers.rollup.RollupCompiler',
        ] + compilers

    if (validate_paths and
        os.environ.get('DJBLETS_SKIP_PIPELINE_VALIDATION') != '1'):
        # Validate that the necessary dependencies exist for Pipeline.
        if not os.path.exists(node_modules_path):
            raise ImproperlyConfigured(
                'node_modules could not be found at %s'
                % node_modules_path)

        for binary_path, check in ((babel_bin_path, True),
                                   (uglifyjs_bin_path, True),
                                   (lessc_bin_path, use_lessc),
                                   (rollup_bin_path, use_rollup)):
            if not os.path.exists(binary_path):
                raise ImproperlyConfigured(
                    'The "%s" binary could not be found at %s'
                    % (os.path.basename(binary_path), binary_path))

    os.environ[str('NODE_PATH')] = force_str(node_modules_path)

    babel_plugins = [
        'dedent',
        'django-gettext',
    ] + babel_extra_plugins

    config = {
        'PIPELINE_ENABLED': bool(pipeline_enabled),
        'COMPILERS': compilers,
        'CSS_COMPRESSOR': None,
        'JS_COMPRESSOR': 'pipeline.compressors.uglifyjs.UglifyJSCompressor',
        'JAVASCRIPT': javascript_bundles,
        'STYLESHEETS': stylesheet_bundles,
        'BABEL_BINARY': babel_bin_path,
        'BABEL_ARGUMENTS': [
            '--presets', '@babel/preset-env,@babel/preset-typescript',
            '--plugins', ','.join(babel_plugins),
            '-s', 'true',
        ] + babel_extra_args,
        'UGLIFYJS_BINARY': uglifyjs_bin_path,
        'UGLIFYJS_ARGUMENTS': '--compress --mangle',
    }

    if use_lessc:
        config.update({
            'LESS_BINARY': lessc_bin_path,
            'LESS_ARGUMENTS': [
                '--include-path=%s:%s' % (static_root, node_modules_path),
                '--no-color',
                '--source-map',
                '--js',
                '--plugin=@beanbag/less-plugin-autoprefix',
            ] + less_extra_args,
        })

    if use_rollup:
        config.update({
            'ROLLUP_ARGUMENTS': rollup_extra_args,
            'ROLLUP_BINARY': rollup_bin_path,
        })

    config.update(extra_config)

    return config
