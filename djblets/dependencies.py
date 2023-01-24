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


###########################################################################
# Python and Django compatibility
###########################################################################

#: The minimum supported version of Python 3.x.
PYTHON_3_MIN_VERSION = (3, 7)

#: A string representation of the minimum supported version of Python 3.x.
PYTHON_3_MIN_VERSION_STR = '%s.%s' % PYTHON_3_MIN_VERSION

#: A dependency version range for Python 3.x.
PYTHON_3_RANGE = ">='%s'" % PYTHON_3_MIN_VERSION_STR


#: The major version of Django we're using for documentation.
django_doc_major_version = '3.2'

#: The major version of Review Board we're using for documentation.
reviewboard_doc_major_version = 'dev'

#: The version range required for Django.
django_version = '~=3.2.16'

###########################################################################
# Python dependencies
###########################################################################

#: All dependencies required to install Djblets.
package_dependencies = {
    'cryptography': '>=1.8.1',
    'Django': django_version,
    'django-pipeline': '~=2.0.8',
    'dnspython': '>=1.14.0',
    'feedparser': '>=5.1.2',
    'Pillow': '>=6.2',
    'publicsuffix': '>=1.1',
    'python-dateutil': '>=2.7',
    'pytz': '',
    'typing_extensions': '>=4.4',
}


###########################################################################
# JavaScript dependencies
###########################################################################

#: Dependencies required for static media building.
frontend_buildkit_npm_dependencies = {
    # Customizable Beanbag-built dependencies.
    '@beanbag/frontend-buildkit': (
        os.environ.get('BEANBAG_FRONTEND_BUILDKIT_PATH') or
        '^1.1.0'),
}

#: Dependencies required for static media linting.
lint_npm_dependencies = {
    'eslint': '^8.29.0',

    # Customizable Beanbag-built dependencies.
    '@beanbag/eslint-plugin': (
        os.environ.get('BEANBAG_ESLINT_PLUGIN_PATH') or
        '^1.0.0'),
}

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
    list of dependency specifiers for use on the command line or in
    :file:`setup.py`.

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
