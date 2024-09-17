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
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Optional

from setuptools import build_meta as _build_meta

from djblets.dependencies import build_dependency_list, package_dependencies


def get_requires_for_build_editable(
    config_settings: Optional[dict] = None,
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

    return (
        _get_build_dependencies() +
        _build_meta.get_requires_for_build_wheel(config_settings)
    )


def get_requires_for_build_sdist(
    config_settings: Optional[dict] = None,
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

    return (
        _get_build_dependencies() +
        _build_meta.get_requires_for_build_wheel(config_settings)
    )


def get_requires_for_build_wheel(
    config_settings: Optional[dict] = None,
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

    return (
        _get_build_dependencies() +
        _build_meta.get_requires_for_build_wheel(config_settings)
    )


def prepare_metadata_for_build_editable(
    metadata_directory: str,
    config_settings: Optional[dict] = None,
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
    config_settings: Optional[dict] = None,
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
    config_settings: Optional[dict] = None,
    metadata_directory: Optional[str] = None,
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
    _build_data_files(collect_static=False)

    return _build_meta.build_editable(
        wheel_directory,
        {
            'editable_mode': 'compat',
            **(config_settings or {})
        },
        metadata_directory)


def build_sdist(
    sdist_directory: str,
    config_settings: Optional[dict] = None,
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
    config_settings: Optional[dict] = None,
    metadata_directory: Optional[str] = None,
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


def _get_build_dependencies() -> list[str]:
    # For a build, we need django-evolution. Rather than hard-coding the
    # dependency twice, pull this from dev-requirements.txt.
    with open('dev-requirements.txt', 'r') as fp:
        dev_deps = [
            dep.strip()
            for dep in fp
            if dep.startswith('django_evolution')
        ]

    return build_dependency_list(package_dependencies) + dev_deps


def _write_dependencies() -> None:
    """Temporarily write dependencies to a file.

    This will write to :file:`package-requirements.txt`, so that
    :file:`pyproject.toml` can reference it.

    Context:
        The file will exist until the context closes.
    """
    with open('package-requirements.txt', 'w') as fp:
        fp.write('%s\n'
                 % '\n'.join(build_dependency_list(package_dependencies)))


def _build_data_files(
    *,
    collect_static: bool = True,
) -> None:
    """Build static media and i18n data files.

    Args:
        collect_static (bool, optional):
            Whether to run a ``collectstatic`` operation to build media
            files.

            If ``False``, support for building static media will still be
            installed.

    Raises:
        RuntimeError:
            There was an error building the media or i18n files.
    """
    media_env: dict[str, str] = os.environ.copy()

    if not collect_static:
        media_env['RUN_COLLECT_STATIC'] = '0'

    # Build the static media.
    retcode = subprocess.call(
        [
            sys.executable,
            os.path.join('contrib', 'internal', 'build-media.py'),
        ],
        env=media_env)

    if retcode != 0:
        raise RuntimeError('Failed to build media files')

    # Build the i18n files.
    retcode = subprocess.call([
        sys.executable,
        os.path.join('contrib', 'internal', 'build-i18n.py'),
    ])

    if retcode != 0:
        raise RuntimeError('Failed to build i18n files')
