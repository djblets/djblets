"""Version information for certain Djblets dependencies.

This contains constants that other parts of Djblets and consumers of Djblets
can use to look up information on major dependencies of Djblets.

The contents in this file might change substantially between releases. If
you're going to make use of data from this file, code defensively.
"""

# NOTE: This file may not import other files! It's used for packaging and
#       may be needed before any dependencies have been installed.


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

#: Dependencies required for LessCSS pipelining.
lesscss_npm_dependencies = {
    'less': '^4.1.3',
    '@beanbag/less-plugin-autoprefix': '^3.0.0',
}

#: Dependencies required for UglifyJS JavaScript compression.
uglifyjs_npm_dependencies = {
    'uglify-js': '^3.16.1',
}

#: Dependencies required for Babel for JavaScript.
babel_npm_dependencies = {
    '@babel/cli': '^7.17.10',
    '@babel/core': '^7.18.5',
    '@babel/preset-env': '^7.18.2',
    'babel-plugin-dedent': '^2.1.0',
    'babel-plugin-django-gettext': '^1.1.1',
}

#: All static media dependencies required to package/develop against  Djblets.
npm_dependencies = {}
npm_dependencies.update(lesscss_npm_dependencies)
npm_dependencies.update(uglifyjs_npm_dependencies)
npm_dependencies.update(babel_npm_dependencies)

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
