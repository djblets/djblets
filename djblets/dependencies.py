"""Version information for certain Djblets dependencies.

This contains constants that other parts of Djblets and consumers of Djblets
can use to look up information on major dependencies of Djblets.

The contents in this file might change substantially between releases. If
you're going to make use of data from this file, code defensively.
"""

# NOTE: This file may not import other (non-Python) modules! It's used for
#       packaging and may be needed before any dependencies have been
#       installed.

import os
from typing import Dict


###########################################################################
# Python and Django compatibility
###########################################################################

#: The minimum supported version of Python 3.x.
PYTHON_3_MIN_VERSION = (3, 8)

#: A string representation of the minimum supported version of Python 3.x.
PYTHON_3_MIN_VERSION_STR = '%s.%s' % PYTHON_3_MIN_VERSION

#: A dependency version range for Python 3.x.
PYTHON_3_RANGE = ">='%s'" % PYTHON_3_MIN_VERSION_STR


#: The major version of Django we're using for documentation.
django_doc_major_version = '4.2'

#: The major version of Review Board we're using for documentation.
reviewboard_doc_major_version = 'dev'

#: The version range required for Django.
django_version = '~=4.2.17'

###########################################################################
# Python dependencies
###########################################################################

#: All dependencies required to install Djblets.
package_dependencies = {
    'cryptography': '>=41.0.7',
    'Django': django_version,
    'django-pipeline': '~=3.1.0',
    'dnspython': '>=2.3.0',
    'housekeeping': '~=1.1',
    'packaging': '>=23.1',
    'Pillow': '>=6.2',
    'publicsuffixlist': '~=0.10.0',
    'python-dateutil': '>=2.7',
    'pytz': '',
    'typing_extensions': '>=4.12.2',

    # importlib.metadata compatibility import.
    #
    # 6.6 is equivalent to importlib.metadata in Python 3.12.
    'importlib-metadata': '>=6.6',

    # importlib.resources compatibility import.
    #
    # 5.9 is equivalent to importlib.resources in Python 3.12.
    'importlib-resources': '>=5.9',
}


###########################################################################
# JavaScript dependencies
#
# These are auto-generated when running `npm install --save ...` (if the
# package is not already in node_modules).
#
# To re-generate manually, run: `./contrib/internal/build-npm-deps.py`.
###########################################################################

# Auto-generated Node.js dependencies {


#: Dependencies required for static media building.
frontend_buildkit_npm_dependencies: Dict[str, str] = {
    '@beanbag/frontend-buildkit': '^1.2.0',
    '@beanbag/ink': '^0.6.0',
    '@beanbag/spina': '^3.1.1',
    '@types/jquery': '^3.5.30',
    '@types/underscore': '^1.11.4',
    'backbone': '^1.4.1',
    'jasmine-core': '^5.0.1',
    'jquery': '^3.7.1',
    'jquery-ui': '^1.13.3',
}

#: Dependencies required for static media linting.
lint_npm_dependencies: Dict[str, str] = {
    '@beanbag/eslint-plugin': '^1.0.2',
    'eslint': '^8.29.0',
}


# } Auto-generated Node.js dependencies


#: Node dependencies required to package/develop/test Djblets.
npm_dependencies = {}
npm_dependencies.update(frontend_buildkit_npm_dependencies)
npm_dependencies.update(lint_npm_dependencies)


###########################################################################
# Packaging utilities
###########################################################################

def build_dependency_list(deps, version_prefix=''):
    """Build a list of dependency specifiers from a dependency map.

    This can be used along with :py:data:`package_dependencies`,
    :py:data:`npm_dependencies`, or other dependency dictionaries to build a
    list of dependency specifiers for use on the command line and in
    :file:`build-backend.py`.

    Args:
        deps (dict):
            A dictionary of dependencies.

    Returns:
        list of unicode:
        A list of dependency specifiers.
    """
    new_deps = []

    for dep_name, dep_details in deps.items():
        if isinstance(dep_details, list):
            new_deps += [
                '%s%s%s; python_version%s'
                % (dep_name, version_prefix, entry['version'], entry['python'])
                for entry in dep_details
            ]
        else:
            new_deps.append('%s%s%s' % (dep_name, version_prefix, dep_details))

    return sorted(new_deps, key=lambda s: s.lower())
