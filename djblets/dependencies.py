"""Version information for certain Djblets dependencies.

This contains constants that other parts of Djblets and consumers of Djblets
can use to look up information on major dependencies of Djblets.

The contents in this file might change substantially between releases. If
you're going to make use of data from this file, code defensively.
"""

from __future__ import unicode_literals

# NOTE: This file may not import other files! It's used for packaging and
#       may be needed before any dependencies have been installed.


#: The minimum supported version of Python 2.x.
PYTHON_2_MIN_VERSION = (2, 7)

#: The minimum supported version of Python 3.x.
PYTHON_3_MIN_VERSION = (3, 6)

#: A string representation of the minimum supported version of Python 2.x.
PYTHON_2_MIN_VERSION_STR = '%s.%s' % (PYTHON_2_MIN_VERSION)

#: A string representation of the minimum supported version of Python 3.x.
PYTHON_3_MIN_VERSION_STR = '%s.%s' % (PYTHON_3_MIN_VERSION)

#: A dependency version range for Python 2.x.
PYTHON_2_RANGE = "=='%s.*'" % PYTHON_2_MIN_VERSION_STR

#: A dependency version range for Python 3.x.
PYTHON_3_RANGE = ">='%s'" % PYTHON_3_MIN_VERSION_STR


#: The major version of Django we're using for documentation.
django_doc_major_version = '1.6'

#: The major version of Review Board we're using for documentation.
reviewboard_doc_major_version = 'dev'

#: The version range required for Django.
django_version = '>=1.6.11,<1.11.999'

#: Dependencies required for LessCSS pipelining.
lesscss_npm_dependencies = {
    'less': '^3.11.0',
    '@beanbag/less-plugin-autoprefix': '^2.0.1',
}

#: Dependencies required for UglifyJS JavaScript compression.
uglifyjs_npm_dependencies = {
    'uglify-js': '^3.6.0',
}

#: Dependencies required for Babel for JavaScript.
babel_npm_dependencies = {
    'babel-cli': '^6.26.0',
    'babel-preset-env': '^1.7.0',
    'babel-plugin-dedent': '^2.0.0',
    'babel-plugin-django-gettext': '^1.1.0',
}

#: All static media dependencies required to package/develop against  Djblets.
npm_dependencies = {}
npm_dependencies.update(lesscss_npm_dependencies)
npm_dependencies.update(uglifyjs_npm_dependencies)
npm_dependencies.update(babel_npm_dependencies)

#: All dependencies required to install Djblets.
package_dependencies = {
    'Django': django_version,
    'django-pipeline': '>=1.6.14,<1.6.999',
    'dnspython': [
        {
            'python': PYTHON_2_RANGE,
            'version': '>=1.14.0,<1.999',
        },
        {
            'python': PYTHON_3_RANGE,
            'version': '>=1.14.0',
        },
    ],
    'feedparser': [
        {
            'python': PYTHON_2_RANGE,
            'version': '>=5.1.2,<5.999',
        },
        {
            'python': PYTHON_3_RANGE,
            'version': '>=5.1.2',
        },
    ],
    'Pillow': [
        {
            'python': PYTHON_2_RANGE,
            'version': '>=6.2,<6.999',
        },
        {
            'python': PYTHON_3_RANGE,
            'version': '>=6.2',
        },
    ],
    'publicsuffix': '>=1.1',
    'python-dateutil': [
        {
            'python': PYTHON_2_RANGE,
            'version': '>=2.7',
        },
        {
            'python': PYTHON_3_RANGE,
            'version': '>=2.7',
        },
    ],
    'pytz': '',
}


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
