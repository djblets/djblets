#!/usr/bin/env python3
"""Write node.js dependencies to djblets/dependencies.py.

Version Added:
    4.0
"""

from __future__ import annotations

import itertools
import json
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import TextIO


MARKER_START = '# Auto-generated Node.js dependencies {\n'
MARKER_END = '# } Auto-generated Node.js dependencies\n'


LINT_DEP_NAMES = {
    'eslint',
    '@beanbag/eslint-plugin',
}


BUILDKIT_DEP_NAMES = {
    '@beanbag/frontend-buildkit',
    '@beanbag/js-buildkit',
}


def _write_deps(
    *,
    fp: TextIO,
    doc: str,
    name: str,
    deps: Mapping[str, str],
) -> None:
    """Write dependencies to the file.

    This will write the Python code to list each dependency and the
    matching version.

    Args:
        fp (io.TextIO):
            The file to write to.

        doc (str):
            The doc comment contents.

        name (str):
            The name of the variable to write to.

        deps (dict):
            The dependencies to write.
    """
    dependencies = '\n'.join(
        f"    '{dep_name}': '{dep_ver}',"
        for dep_name, dep_ver in deps.items()

    )

    fp.write(
        f'#: {doc}\n'
        f'{name}: Mapping[str, str] = {{\n'
        f'{dependencies}\n'
        f'}}\n'
        f'\n'
    )


def main() -> None:
    """Embed package.json into djblets/dependencies.py."""
    scripts_dir = os.path.abspath(os.path.dirname(__file__))
    top_dir = os.path.abspath(os.path.join(scripts_dir, '..', '..'))
    djblets_dir = os.path.join(top_dir, 'djblets')
    package_json_path = os.path.join(djblets_dir, 'package.json')
    deps_py_path = os.path.join(djblets_dir, 'dependencies.py')

    # Load the dependencies and organize them.
    with open(package_json_path, mode='r', encoding='utf-8') as fp:
        package_json = json.load(fp)

    frontend_deps: dict[str, str] = {}
    lint_deps: dict[str, str] = {}
    npm_deps: dict[str, str] = {}

    for dep_name, dep_ver in sorted(
        itertools.chain(
            package_json['dependencies'].items(),
            package_json['devDependencies'].items(),
        )):
        if dep_name in LINT_DEP_NAMES:
            lint_deps[dep_name] = dep_ver
        elif dep_name in BUILDKIT_DEP_NAMES:
            frontend_deps[dep_name] = dep_ver
        else:
            npm_deps[dep_name] = dep_ver

    # Parse out the existing dependencies.py and grab everything outside the
    # markers.
    new_lines_pre: str = ''
    new_lines_post: str = ''

    with open(deps_py_path, mode='r', encoding='utf-8') as fp:
        data = fp.read()

        i = data.find(MARKER_START)
        assert i != -1

        j = data.find(MARKER_END, i)
        assert j != -1

        new_lines_pre = data[:i]
        new_lines_post = data[j + len(MARKER_END) + 1:]

    # Write out the new dependencies.py.
    with open(deps_py_path, mode='w', encoding='utf-8') as fp:
        fp.write(new_lines_pre)
        fp.write(f'{MARKER_START}\n\n')

        _write_deps(
            fp=fp,
            doc='Dependencies required for static media building.',
            name='frontend_buildkit_npm_dependencies',
            deps=frontend_deps)

        _write_deps(
            fp=fp,
            doc='Dependencies required for static media linting.',
            name='lint_npm_dependencies',
            deps=lint_deps)

        _write_deps(
            fp=fp,
            doc='Node dependencies required to package/develop/test Djblets.',
            name='npm_dependencies',
            deps=npm_deps)

        fp.write(
            'npm_dependencies.update(frontend_buildkit_npm_dependencies)\n'
            'npm_dependencies.update(lint_npm_dependencies)\n'
            '\n\n'
        )
        fp.write(f'{MARKER_END}\n')
        fp.write(new_lines_post)


if __name__ == '__main__':
    main()
