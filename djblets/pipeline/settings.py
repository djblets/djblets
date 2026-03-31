"""Utilities and constants for configuring Pipeline.

Note:
    This is safe to import from a project's :file:`settings.py` without
    side effects (for instance, it will not load any Django models or apps).

Version Added:
    2.1
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from django.core.exceptions import ImproperlyConfigured

from djblets.deprecation import RemovedInDjblets80Warning

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping, Sequence
    from typing import Any

    from djblets.pipeline.bundles import StaticBundle


logger = logging.getLogger(__name__)


#: Default list of compilers used by Djblets.
DEFAULT_PIPELINE_COMPILERS: list[str] = [
    'djblets.pipeline.compilers.es6.ES6Compiler',
    'djblets.pipeline.compilers.typescript.TypeScriptCompiler',
    'djblets.pipeline.compilers.less.LessCompiler',
]


def build_pipeline_settings(
    *,
    pipeline_enabled: bool,
    node_modules_path: str,
    static_root: str,
    javascript_bundles: (Mapping[str, StaticBundle] | None) = None,
    stylesheet_bundles: (Mapping[str, StaticBundle] | None) = None,
    compilers: list[str] = DEFAULT_PIPELINE_COMPILERS,
    babel_extra_plugins: (Sequence[str] | None) = None,
    babel_extra_args: (Sequence[str] | None) = None,
    less_extra_args: (Sequence[str] | None) = None,
    validate_paths: bool = True,
    use_rollup: bool = True,
    rollup_extra_args: (Sequence[str] | None) = None,
    extra_config: (Mapping[str, Any] | None) = None,
    use_terser: bool = False,
) -> dict[str, Any]:
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
        5.3:
        * Changed to support a colon-separated list for the
          ``node_modules_path`` argument.
        * Added support for `terser <https://terser.org>`.
        * Added the ``use_terser`` argument.

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

        node_modules_path (str):
            A colon-separated list of paths to :file:`node_modules`
            directories.

            If ``validate_paths=False``, it's up to the caller to ensure that
            the the first path in the list refers to a :file:`node_modules`
            directory that exists and contains the required binaries at
            build time.

        static_root (str):
            The value of the ``settings.STATIC_ROOT``. This must be provided
            explicitly, since :file:`settings.py` is likely the module
            calling this.

        javascript_bundles (list of dict, optional):
            A list of JavaScript bundle packages for Pipeline to handle.

        stylesheet_bundles (list of dict, optional):
            A list of stylesheet bundle packages for Pipeline to handle.

        compilers (list of str, optional):
            A list of compilers to use for static media.

        babel_extra_plugins (list of str, optional):
            A list of additional Babel plugins to enable.

        babel_extra_args (list of str, optional):
            Extra command line arguments to pass to Babel.

        less_extra_args (list of str, optional):
            Extra command line arguments to pass to LessCSS.

        validate_paths (bool, optional):
            Whether to validate any expected paths to binaries.

            It's recommended to set this based on ``DEBUG``, or another
            variable indicating a production vs. development environment. It
            should be ``False`` when binaries may not exist at call time of
            this function, but will exist later at build time.

            If the :envvar:`DJBLETS_SKIP_PIPELINE_VALIDATION` environment
            variable is set to ``1``, then this will be forced to ``False``.
            This is primarily used for packaging building.

        use_rollup (bool, optional):
            Whether to use rollup to assemble JavaScript bundles.

            Version Added:
                4.0

        rollup_extra_args (list of str, optional):
            Extra command line arguments to pass to rollup.

            Version Added:
                4.0

        extra_config (dict, optional):
            Additional configuration to merge into the resulting dictionary.

            Version Added:
                4.0

        use_terser (bool, optional):
            Whether to use Terser instead of UglifyJS.

            Version Added:
                5.3

    Returns:
        dict:
        The pipeline configuration dictionary.
    """
    # A mapping of binary names to the node_modules path that
    # `npm exec` should be ran from when executing the binary
    # (i.e. the `--prefix` path).
    #
    # This is guaranteed to include babel + all the packages that have
    # `use_<package>=True`.
    exec_paths: dict[str, str] = {}

    validate_paths = (
        validate_paths and
        os.environ.get('DJBLETS_SKIP_PIPELINE_VALIDATION') != '1'
    )
    use_lessc = (
        'djblets.pipeline.compilers.less.LessCompiler' in compilers or
        'pipeline.compilers.less.LessCompiler' in compilers
    )

    binaries: Sequence[tuple[str, str, Sequence[str], bool]] = [
        ('babel', 'BABEL_BINARY', ['babel', '-V'], True),
        ('lessc', 'LESS_BINARY', ['lessc', '-v'], use_lessc),
        ('rollup', 'ROLLUP_BINARY', ['rollup', '-v'], use_rollup),
        ('uglifyjs', 'UGLIFYJS_BINARY', ['uglifyjs', '-V'], not use_terser),
        ('terser', 'TERSER_BINARY', ['terser', '-V'], use_terser),
    ]

    if use_rollup:
        # Make sure that rollup is before any other JavaScript compilers.
        compilers = [
            'djblets.pipeline.compilers.rollup.RollupCompiler',
            *compilers,
        ]

    if validate_paths:
        # Validate the given node_modules paths.
        def _try_exec(
            tool: str,
            command: Sequence[str],
            node_modules_paths: Sequence[Path],
        ) -> str | None:
            for path in node_modules_paths:
                prefix_path = str(path.parent)

                full_exec_command = [
                    'npm',
                    'exec',
                    '--prefix',
                    prefix_path,
                    '--no',
                    '--',
                    *command,
                ]

                try:
                    with subprocess.Popen(full_exec_command,
                                          stdout=subprocess.PIPE) as p:
                        stdout, _stderr = p.communicate(timeout=5)

                        logger.info(
                            'Using %s: %s', tool, stdout.decode().strip())

                        if p.returncode == 0:
                            return prefix_path
                except Exception as e:
                    logger.error('Unable to execute %s: %s',
                                 subprocess.list2cmdline(full_exec_command),
                                 e)

            return None

        node_modules_paths: list[Path] = []
        path_exists: bool = False

        for path in node_modules_path.split(':'):
            path_obj = Path(path)

            if path and path_obj.exists():
                path_exists = True
                node_modules_paths.append(path_obj)
            else:
                logger.warning('node_modules path "%s" does not exist', path)

        if not path_exists:
            raise ImproperlyConfigured(
                f'No node_modules paths in "{node_modules_path}" exist')

        # Validate that the necessary binaries exist for Pipeline and
        # set their prefix paths.
        for binary, config_key, cmdline, check in binaries:
            if not check:
                continue

            exec_path = _try_exec(binary, cmdline, node_modules_paths)

            if exec_path is None:
                raise ImproperlyConfigured(
                    f'"{binary}" could not be found in configured '
                    f'node_modules paths "{node_modules_path}".'
                )

            exec_paths[binary] = exec_path
    else:
        # Skip node_modules path validation and assume that the path exists.
        #
        # If we have multiple node_modules paths we have no way of choosing
        # the best one since we're skipping validation, so just use the
        # first one in the list.
        path = node_modules_path.split(':')[0]
        path_obj = Path(path)
        prefix_path = str(path_obj.parent)

        for binary, config_key, cmdline, check in binaries:
            if not check:
                continue

            exec_paths[binary] = prefix_path

    os.environ['NODE_PATH'] = node_modules_path

    babel_plugins = [
        'dedent',
        'django-gettext',
    ]

    if babel_extra_plugins:
        babel_plugins.extend(babel_extra_plugins)

    config: dict[str, Any] = {
        'PIPELINE_ENABLED': bool(pipeline_enabled),
        'COMPILERS': compilers,
        'CSS_COMPRESSOR': None,
        'JS_COMPRESSOR': 'pipeline.compressors.terser.TerserCompressor',
        'JAVASCRIPT': javascript_bundles or {},
        'STYLESHEETS': stylesheet_bundles or {},
        'BABEL_ARGUMENTS': [
            '--presets', '@babel/preset-env,@babel/preset-typescript',
            '--plugins', ','.join(babel_plugins),
            '-s', 'true',
            *(babel_extra_args or []),
        ],
    }

    if use_terser:
        config.update({
            'TERSER_ARGUMENTS': [
                '--compress',
                '--mangle',
                '--keep-classnames',
                '--keep-fnames',
            ],
        })
    else:
        RemovedInDjblets80Warning.warn(
            'Support for UglifyJS is deprecated and will be removed in '
            'Djblets 8.0. To use terser instead, call '
            'build_pipeline_settings() with use_terser=True.'
        )
        config.update({
            'UGLIFYJS_ARGUMENTS': '--compress --mangle --no-module',
        })

    if use_lessc:
        config.update({
            'LESS_ARGUMENTS': [
                f'--include-path={static_root}:{node_modules_path}',
                '--no-color',
                '--source-map',
                '--js',
                '--plugin=@beanbag/less-plugin-autoprefix',
                *(less_extra_args or []),
            ],
        })

    if use_rollup:
        config.update({
            'ROLLUP_ARGUMENTS': rollup_extra_args or [],
        })

    # Set the `npm exec` prefix paths for the binaries.
    config.update({
        config_key: [
            'npm',
            'exec',
            '--prefix',
            exec_paths[binary],
            '--',
            binary,
        ]
        for binary, config_key, cmdline, check in binaries
        if check
    })

    if extra_config:
        config.update(extra_config)

    return config


def find_node_modules_dirs(directory: str | Path) -> Iterator[Path]:
    """Find and return all ``node_modules`` directories above a given path.

    Version Added:
        5.3

    Args:
        directory (str or pathlib.Path):
            The directory to search from.

    Yields:
        list of pathlib.Path:
        A list of all existing ``node_modules`` directories which are found at
        or above the given directory.
    """
    if not isinstance(directory, Path):
        directory = Path(directory)

    for parent in [directory, *directory.parents]:
        modules_path = parent / 'node_modules'

        if modules_path.is_dir():
            yield modules_path
