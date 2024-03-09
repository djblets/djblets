"""Pipeline compiler for bundling modern JavaScript with rollup.js.

Version Added:
    4.0
"""

import os
import re
from pathlib import Path
from typing import List, Optional, Tuple

from pipeline.conf import settings
from pipeline.compilers import SubProcessCompiler

from djblets.pipeline.compilers.mixins import SourceMapStaleCheckMixin


#: The default regular expression used for rollup.js index files.
#:
#: Version Added:
#:     4.0
DEFAULT_FILE_PATTERN = r'index\.(js|es6|es6\.js|ts)$'


_match_regex = re.compile(settings.get('ROLLUP_FILE_PATTERN') or
                          DEFAULT_FILE_PATTERN)


class RollupCompiler(SourceMapStaleCheckMixin, SubProcessCompiler):
    """A Pipeline compiler for interfacing with rollup.js.

    `rollup.js <https://rollupjs.org/>`_ is a module bundler for JavaScript
    that compiles down a JavaScript codebase, linked together through module
    imports (ES6, CommonJS etc.), into a single JavaScript file. It can manage
    compilation with Babel or TypeScript, and supports a wide variety of
    plugins.

    This compiler makes it easy to develop modern JavaScript while still
    taking advantage of the best of Pipeline, such as managing separate
    bundles, loading bundles into Django templates, and triggering automatic
    recompilation on demand if any files (including those imported via modules)
    in the bundle are stale.

    To use this compiler, you will need an ``index`` file in your Pipeline
    JavaScript bundle, which imports any other modules that should be part
    of that compiled rollup.js bundle. An ``index`` file can be in the
    following forms:

    * :file:`index.js`
    * :file:`index.es6`
    * :file:`index.es6.js`
    * :file:`index.ts`

    Custom filename patterns can be specified by setting
    ``settings.PIPELINE['ROLLUP_FILE_PATTERN']`` to a regular expression string
    (defaults to :py:data:`DEFAULT_FILE_PATTERN`).

    Your Pipeline bundle may consist of just this one ``index`` file, or it
    may include other JavaScript as well. Each ``index`` will be compiled as
    its own rollup.js bundle, and its compiled contents included as part of the
    Pipeline bundle.

    Sourcemaps are used to check if any parts of the bundle are stale,
    triggering automatic recompilation when loading pages. Please note that
    any modules that you want included but are not actively being used within
    that rollup.js bundle may be excluded from automatic recompilation
    detection if you have treeshaking enabled (which is enabled by default).

    You will need to set ``settings.PIPELINE['ROLLUP_BINARY']`` to the path
    of :file:`rollup` and then set any command line arguments needed
    (such as a path to your configuration file) in
    ``settings.PIPELINE['ROLLUP_ARGUMENTS']``.

    The arguments should *not* include ``-c`` / ``--config`` to specify the
    Rollup configuration path. This will be computed automatically, in order
    to ensure the right file is used based on whichever source tree may be
    hosting the input file (such as when a project is consuming another
    project's source files and compiling them).

    Version Changed:
        4.1:
        Added support for :file:`rollup.config.mjs` and
        :file:`rollup.config.ts` files.

    Version Added:
        4.0
    """

    output_extension = 'js'

    def match_file(
        self,
        path: str,
    ) -> bool:
        """Return whether this compiler matches a source file.

        This will look for the following filenames by default:

        * :file:`index.js`
        * :file:`index.es6`
        * :file:`index.es6.js`
        * :file:`index.ts`

        To customize this, set ``settings.PIPELINE['ROLLUP_FILE_PATTERN']``
        to a regular expression string.

        Args:
            path (str):
                The path to the source file being considered.

        Returns:
            bool:
            ``True`` if this compiler will invoke rollup.js on this file.
            ``False`` if it will not.
        """
        return _match_regex.match(os.path.basename(path)) is not None

    def compile_file(
        self,
        infile: str,
        outfile: str,
        outdated: bool = False,
        force: bool = False,
    ) -> None:
        """Compile a file using rollup.js.

        This will cause the file and anything it imports in the tree into
        a rollup.js bundle, for inclusion in the Pipeline bundle.

        Args:
            infile (str):
                The source file.

            outfile (str):
                The destination file.

            outdated (bool, optional):
                Whether the destination file is known to be outdated.

            force (bool, optional):
                Whether to force re-running rollup.js on this file.
        """
        if outdated or force:
            # Look for the root of a tree, containing any of a number of
            # build configuration files.
            tree_root, rollup_config_path = \
                self._find_tree_root(os.path.dirname(infile))

            args: List[str] = [
                settings.ROLLUP_BINARY,
            ]

            if rollup_config_path:
                # We found a rollup.config.js. Make sure we tell rollup.js to
                # use it explicitly.
                rollup_config_filename = os.path.basename(rollup_config_path)

                if rollup_config_filename == 'rollup.config.js':
                    args.append('--bundleConfigAsCjs')
                elif rollup_config_filename == 'rollup.config.ts':
                    args += [
                        '--configPlugin',
                        'typescript',
                    ]

                args += [
                    '-c',
                    rollup_config_path,
                ]

            args += [
                settings.ROLLUP_ARGUMENTS,
                '--sourcemap',
                '-i',
                infile,
                '-o',
                outfile,
            ]

            self.execute_command(args, cwd=tree_root)

    def _find_tree_root(
        self,
        start_dir: str,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Return the root of a source tree for an input file.

        This will scan up the tree, looking for a Rollup configuration file:

        * :file:`rollup.config.js`
        * :file:`rollup.config.mjs`
        * :file:`rollup.config.ts`

        Plus another JavaScript configuration:

        * :file:`.babelrc`
        * :file:`babel.config.json`
        * :file:`tsconfig.json`

        This is used to try to find the proper working directory needed to
        successfully compile a file.

        This is important when a project is consuming and building another
        project's static media, so that the consumed project's configuration
        is applied.

        Version Changed:
            4.1:
            Added scanning for :file:`rollup.config.mjs`,
            :file:`rollup.config.ts`, :file:`babel.config.json`, and
            :file:`tsconfig.json` files.

        Args:
            start_dir (str):
                The starting directory for the search.

        Returns:
            str:
            The root of the source tree, or ``None`` if it could not be found.
        """
        path = Path(start_dir)
        root = Path(path.root)

        while path != root:
            for config_filename in ('rollup.config.js',
                                    'rollup.config.mjs',
                                    'rollup.config.ts'):
                rollup_config_path = Path(path / config_filename)

                if rollup_config_path.exists():
                    # This is the ideal result. We found the top-level of the
                    # tree and the rollup.config.js file.
                    return str(path), str(rollup_config_path)

            if (Path(path / '.babelrc').exists() or
                Path(path / 'babel.config.json').exists() or
                Path(path / 'tsconfig.json').exists()):
                # We didn't find rollup.config.js, but we found another
                # JavaScript configuration file. Consider this the top of
                # the tree.
                return str(path), None

            path = path.parent

        return None, None
