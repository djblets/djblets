"""Python build backend for Djblets.

This is a specialization of the setuptools build backend, making the following
custom changes:

1. Including all of Djblets's dependencies as build-time dependencies.

   We execute code within Djblets as part of the build process, meaning that
   we need most (if not all) of the dependencies at build time. To play it
   safe, we simply include them all.

2. Introspecting djblets/dependencies.py for package metadata.

   Setuptools allows for dynamic dependencies, but only when including it
   via a requirements.txt-formatted file. We temporarily generate one of those
   for Setuptools when building the metadata.

   (Note that we have no other place to inject this, as pyproject.toml's
   dependencies, even if empty/not specified, override anything we could set
   anywhere else.)

3. Building media and i18n files.

   When building wheels or source distributions, we run our media-building
   scripts, ensuring they get included in the resulting files.

Version Added:
    5.2


Editable Installs
-----------------

If you need to set up an editable install against in-development builds of
Django, Django-Pipeline, or other packages, you will need to set up symlinks
to your local packages in :file:`.local-packages/`. For example:

.. code-block:: console

   $ cd .local-packages
   $ ln -s ~/src/typelets typelets

This must match the package name as listed in the dependencies (but is
case-insensitive).
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING

from setuptools import build_meta as _build_meta

from djblets.dependencies import build_dependency_list, package_dependencies

if TYPE_CHECKING:
    from typing import Any


LOCAL_PACKAGES_DIR = '.local-packages'


def get_requires_for_build_editable(
    config_settings: (dict[str, Any] | None) = None,
) -> list[str]:
    """Return build-time requirements for editable builds.

    This will return the standard Djblets dependencies, along with any
    pyproject-specified build-time dependencies.

    Args:
        config_settings (dict, optional):
            Configuration settings to pass to Setuptools.

    Returns:
        list of str:
        The list of build-time dependencies.
    """
    _write_dependencies()

    local_paths: dict[str, str] = {}

    if os.path.exists(LOCAL_PACKAGES_DIR):
        for name in os.listdir(LOCAL_PACKAGES_DIR):
            local_paths[name.lower()] = os.path.abspath(
                os.readlink(os.path.join(LOCAL_PACKAGES_DIR, name)))

    return [
        *build_dependency_list(
            package_dependencies,
            local_packages=local_paths),
        *_get_dev_dependencies(),
        *_build_meta.get_requires_for_build_wheel(config_settings),
    ]


def get_requires_for_build_sdist(
    config_settings: (dict[str, Any] | None) = None,
) -> list[str]:
    """Return build-time requirements for source distributions.

    This will return the standard Djblets dependencies, along with any
    pyproject-specified build-time dependencies.

    Args:
        config_settings (dict, optional):
            Configuration settings to pass to Setuptools.

    Returns:
        list of str:
        The list of build-time dependencies.
    """
    _write_dependencies()

    return [
        *build_dependency_list(package_dependencies),
        *_get_dev_dependencies(),
        *_build_meta.get_requires_for_build_wheel(config_settings)
    ]


def get_requires_for_build_wheel(
    config_settings: (dict[str, Any] | None) = None,
) -> list[str]:
    """Return build-time requirements for wheel distributions.

    This will return the standard Djblets dependencies, along with any
    pyproject-specified build-time dependencies.

    Args:
        config_settings (dict, optional):
            Configuration settings to pass to Setuptools.

    Returns:
        list of str:
        The list of build-time dependencies.
    """
    _write_dependencies()

    return [
        *build_dependency_list(package_dependencies),
        *_get_dev_dependencies(),
        *_build_meta.get_requires_for_build_wheel(config_settings)
    ]


def prepare_metadata_for_build_editable(
    metadata_directory: str,
    config_settings: (dict[str, Any] | None) = None,
) -> str:
    """Prepare metadata for an editable build.

    This will write out Djblets's dependencies to a temporary file so that
    pyproject.toml can locate it.

    Args:
        metadata_directory (str):
            The target directory for metadata.

        config_settings (dict, optional):
            Configuration settings to pass to Setuptools.

    Returns:
        str:
        The basename for the generated ``.dist-info`` directory.
    """
    _write_dependencies()

    return _build_meta.prepare_metadata_for_build_editable(
        metadata_directory,
        config_settings)


def prepare_metadata_for_build_wheel(
    metadata_directory: str,
    config_settings: (dict[str, Any] | None) = None,
) -> str:
    """Prepare metadata for a wheel distribution.

    This will write out Djblets's dependencies to a temporary file so that
    pyproject.toml can locate it.

    Args:
        metadata_directory (str):
            The target directory for metadata.

        config_settings (dict, optional):
            Configuration settings to pass to Setuptools.

    Returns:
        str:
        The basename for the generated ``.dist-info`` directory.
    """
    _write_dependencies()

    return _build_meta.prepare_metadata_for_build_wheel(
        metadata_directory,
        config_settings)


def build_editable(
    wheel_directory: str,
    config_settings: (dict[str, Any] | None) = None,
    metadata_directory: (str | None) = None,
) -> str:
    """Build an editable environment.

    This will build the static media and i18n files needed by Djblets, and
    then let Setuptools build the editable environment.

    Args:
        wheel_directory (str):
            The directory where the editable wheel will be placed.

        config_settings (dict, optional):
            Configuration settings to pass to Setuptools.

        metadata_directory (str, optional):
            The directory where metadata would be stored.

    Returns:
        str:
        The basename for the generated source distribution file.
    """
    _install_npm_packages()

    return _build_meta.build_editable(
        wheel_directory,
        {
            'editable_mode': 'compat',
            **(config_settings or {})
        },
        metadata_directory)


def build_sdist(
    sdist_directory: str,
    config_settings: (dict[str, Any] | None) = None,
) -> str:
    """Build a source distribution.

    This will build the static media and i18n files needed by Djblets, and
    then let Setuptools build the distribution.

    Args:
        sdist_directory (str):
            The directory where the source distribution will be placed.

        config_settings (dict, optional):
            Configuration settings to pass to Setuptools.

    Returns:
        str:
        The basename for the generated source distribution file.
    """
    _build_data_files()

    return _build_meta.build_sdist(sdist_directory,
                                   config_settings)


def build_wheel(
    wheel_directory: str,
    config_settings: (dict[str, Any] | None) = None,
    metadata_directory: (str | None) = None,
) -> str:
    """Build a wheel.

    This will build the static media and i18n files needed by Djblets, and
    then let Setuptools build the distribution.

    Args:
        wheel_directory (str):
            The directory where the wheel will be placed.

        config_settings (dict, optional):
            Configuration settings to pass to Setuptools.

        metadata_directory (str, optional):
            The directory where metadata would be stored.

    Returns:
        str:
        The basename for the generated wheel file.
    """
    _build_data_files()

    return _build_meta.build_wheel(wheel_directory,
                                   config_settings,
                                   metadata_directory)


def _get_dev_dependencies() -> list[str]:
    # For a build, we need django-evolution. Rather than hard-coding the
    # dependency twice, pull this from dev-requirements.txt.
    with open('dev-requirements.txt', mode='r', encoding='utf-8') as fp:
        return [
            dep.strip()
            for dep in fp
            if dep.startswith('django_evolution')
        ]


def _write_dependencies() -> None:
    """Temporarily write dependencies to a file.

    This will write to :file:`package-requirements.txt`, so that
    :file:`pyproject.toml` can reference it.
    """
    with open('package-requirements.txt', mode='w', encoding='utf-8') as fp:
        dependencies = '\n'.join(
            build_dependency_list(package_dependencies))

        fp.write(f'{dependencies}\n')


def _install_npm_packages() -> None:
    """Install NPM packages.

    Raises:
        RuntimeError:
            There was an error installing npm packages.
    """
    try:
        subprocess.run(['npm', 'install'],
                       stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT,
                       check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f'Failed to install npm packages: {e.output}')


def _build_data_files() -> None:
    """Build static media and i18n data files.

    Raises:
        RuntimeError:
            There was an error building the media or i18n files.
    """
    try:
        # Build the static media.
        subprocess.run(
            [
                sys.executable,
                os.path.join('contrib', 'internal', 'build-media.py'),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f'Failed to build media files: {e.output}')

    try:
        # Build the i18n files.
        subprocess.run(
            [
                sys.executable,
                os.path.join('contrib', 'internal', 'build-i18n.py'),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f'Failed to build i18n files: {e.output}')
