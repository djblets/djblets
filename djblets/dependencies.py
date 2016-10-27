"""Version information for certain Djblets dependencies.

This contains constants that other parts of Djblets and consumers of Djblets
can use to look up information on major dependencies of Djblets.

The contents in this file might change substantially between releases. If
you're going to make use of data from this file, code defensively.
"""

from __future__ import unicode_literals

# NOTE: This file may not import other files! It's used for packaging and
#       may be needed before any dependencies have been installed.


#: The major version of Django we're using for documentation.
django_doc_major_version = '1.6'

#: The version range required for Django.
django_version = '>=1.6.11,<1.8.999'

#: Dependencies required for LessCSS pipelining.
lesscss_npm_dependencies = {
    'less': '2.7.1',
}

#: Dependencies required for UglifyJS JavaScript compression.
uglifyjs_npm_dependencies = {
    'uglifyjs': '2.4.10',
}

#: All static media dependencies required to package/develop against Djblets.
npm_dependencies = {}
npm_dependencies.update(lesscss_npm_dependencies)
npm_dependencies.update(uglifyjs_npm_dependencies)

#: All dependencies required to install Djblets.
package_dependencies = {
    'Django': django_version,
    'django-pipeline': '>=1.3.23,<1.3.9999',
    'dnspython': '>=1.14.0',
    'feedparser': '>=5.1.2',
    'pillowfight': '',
    'publicsuffix': '>=1.1',
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
    return [
        '%s%s%s' % (dep_name, version_prefix, dep_version)
        for dep_name, dep_version in deps.items()
    ]
