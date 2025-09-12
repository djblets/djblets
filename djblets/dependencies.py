"""Version information for certain Djblets dependencies.

This contains constants that other parts of Djblets and consumers of Djblets
can use to look up information on major dependencies of Djblets.

The contents in this file might change substantially between releases. If
you're going to make use of data from this file, code defensively.
"""

# NOTE: This file may not import other (non-Python) modules! It's used for
#       packaging and may be needed before any dependencies have been
#       installed.

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from typing import List, TypedDict, Union

    from typing_extensions import TypeAlias

    class PythonSpecificDependency(TypedDict):
        """A dependency definition that differs based on Python version.

        Version Added:
            5.3
        """

        #: The version limiter of Python the dependency is for.
        python: str

        #: The version of the dependency to use.
        version: str

    #: A package dependency version.
    #:
    #: Version Added:
    #:     5.3
    Dependency: TypeAlias = Union[str, List[PythonSpecificDependency]]


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
package_dependencies: Mapping[str, Dependency] = {
    'cryptography': '>=41.0.7',
    'Django': django_version,
    'django-assert-queries': '~=2.0.1',
    'django-pipeline': '~=3.1.0',
    'dnspython': '>=2.3.0',
    'housekeeping': '~=1.1',
    'packaging': '>=23.1',
    'Pillow': '>=6.2',
    'publicsuffixlist': '~=0.10.0',
    'python-dateutil': '>=2.7',
    'pytz': '',
    'typelets': '~=1.0.1',
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
# Packaging utilities
###########################################################################

def build_dependency_list(
    deps: Mapping[str, Dependency],
    version_prefix: str = '',
    *,
    local_packages: Mapping[str, str] = {},
) -> Sequence[str]:
    """Build a list of dependency specifiers from a dependency map.

    This can be used along with :py:data:`package_dependencies`
    or other dependency dictionaries to build a list of dependency specifiers
    for use on the command line and in :file:`build-backend.py`.

    Args:
        deps (dict):
            A dictionary of dependencies.

        version_prefix (str, optional):
            The prefix to include on version specifiers.

        local_packages (dict, optional):
            A mapping of dependency names to local paths where they could
            be found.

            Version Added:
                5.3

    Returns:
        list of str:
        A list of dependency specifiers.
    """
    new_deps = []

    for dep_name, dep_details in deps.items():
        lower_dep_name = dep_name.lower()

        if lower_dep_name in local_packages:
            package_path = local_packages[lower_dep_name]
            new_deps.append(f'{dep_name} @ file://{package_path}')
        elif isinstance(dep_details, list):
            new_deps += [
                f'{dep_name}{version_prefix}{entry["version"]}; '
                f'python_version{entry["python"]}'
                for entry in dep_details
            ]
        else:
            new_deps.append(
                f'{dep_name}{version_prefix}{dep_details}')

    return sorted(new_deps, key=lambda s: s.lower())
