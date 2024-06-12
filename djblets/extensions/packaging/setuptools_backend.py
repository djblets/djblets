"""Setuptools backend support for building extensions.

Version Added:
    5.0:
    This has moved from :py:mod:`djblets.extensions.packaging`, with
    deprecated functionality removed.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional, TYPE_CHECKING, Type, cast

from importlib_metadata import EntryPoint, Sectioned
from setuptools import Command
from setuptools.command.build_py import build_py

from djblets.deprecation import RemovedInDjblets70Warning

if TYPE_CHECKING:
    from djblets.extensions.extension import Extension
    from djblets.extensions.packaging.static_media import (
        StaticMediaBuildContext,
        StaticMediaBuilder,
    )


class BuildStaticFiles(Command):
    """Builds static files for the extension.

    This will build the static media files used by the extension. JavaScript
    bundles will be minified and versioned. CSS bundles will be processed
    through LessCSS (if using :file:`.less` files), minified and versioned.

    This must be subclassed by the project offering the extension support.
    The subclass must provide the :py:attr:`extension_entrypoint_group` and
    :py:attr:`django_settings_module parameters`.

    Version Added:
        5.0:
        This was moved from :py:mod:`djblets.extensions.packaging`.
    """

    description = 'Build static media files'
    user_options = [
        (str('remove-source-files'), None,
         'remove source files from the package'),
    ]
    boolean_options = [str('remove-source-files')]

    #: The packaging entry point group name that extensions register into.
    #:
    #: This must be provided by subclasses.
    extension_entrypoint_group: Optional[str] = None

    #: The Python module path for the project's settings.
    #:
    #: This must be provided by subclasses.
    django_settings_module: Optional[str] = None

    #: The context class used to customize static media building.
    #:
    #: Subclasses can override this to modify the build process.
    #:
    #: If ``None``, the default context is loaded and used at build time.
    #:
    #: Version Added:
    #:     5.0
    static_media_build_context_cls: Optional[type[StaticMediaBuildContext]] = \
        None

    #: The class responsible for building static media.
    #:
    #: Subclasses can override this to modify the build process.
    #:
    #: If ``None``, the default builder is loaded and used at build time.
    #:
    #: Version Added:
    #:     5.0
    static_media_builder_cls: Optional[type[StaticMediaBuilder]] = None

    ######################
    # Instance variables #
    ######################

    #: The instance of the builder responsible for building static media.
    #:
    #: Version Added:
    #:     5.0
    _builder: StaticMediaBuilder

    def initialize_options(self) -> None:
        """Initialize options for the command."""
        self.build_lib = None
        self.remove_source_files = False

    def finalize_options(self) -> None:
        """Finalize options for the command."""
        self.set_undefined_options('build', ('build_lib', 'build_lib'))

    def run(self) -> None:
        """Build the static files.

        This will setup a suitable Django environment and begin building
        static files for the extension.
        """
        import django

        class_name = type(self).__name__
        django_settings_module = self.django_settings_module
        extension_entrypoint_group = self.extension_entrypoint_group

        if not django_settings_module:
            raise ValueError(
                f'{class_name}.django_settings_module must be set to a '
                f'valid Django settings module path.'
            )

        if not extension_entrypoint_group:
            raise ValueError(
                f'{class_name}.extension_entrypoint_group must be set to a '
                f'valid Python Entry Point group name.'
            )

        distribution = self.distribution

        if not distribution:
            raise ValueError(
                'Received an empty Distribution during packaging.'
            )

        # Prepare to import the project's settings file, and the extension
        # modules that are being shipped, so we can scan for the bundled
        # media.
        old_settings_module = os.environ.get('DJANGO_SETTINGS_MODULE')
        os.environ['DJANGO_SETTINGS_MODULE'] = django_settings_module

        # Skip any initial pipeline settings validation in the consuming
        # project's settings.py. The paths may not exist at this stage. We'll
        # be creating them.
        os.environ['DJBLETS_SKIP_PIPELINE_VALIDATION'] = '1'

        django.setup()

        cwd = os.getcwd()
        sys.path = [
            os.path.join(cwd, package_name)
            for package_name in self.distribution.packages
        ] + sys.path

        # Load the entry points this package is providing, so we'll know
        # which extensions to scan.
        entry_points = getattr(distribution, 'entry_points', {})

        if not isinstance(entry_points, dict):
            raise ValueError(
                f'Received an unexpected value for Distribution.entry_points: '
                f'{entry_points!r}'
            )

        group_entry_points = entry_points.get(extension_entrypoint_group)

        if not group_entry_points:
            raise ValueError(
                'This package does not define any extension entry points.'
            )

        if isinstance(group_entry_points, str):
            group_entry_points_lines = group_entry_points
        elif isinstance(group_entry_points, list):
            group_entry_points_lines = '\n'.join(group_entry_points)
        else:
            raise ValueError(
                f'Received an unexpected value for the Entry Point groups: '
                f'{group_entry_points!r}'
            )

        extension_entry_points = [
            EntryPoint(name=item.value.name,
                       value=item.value.value,
                       group=extension_entrypoint_group)
            for item in Sectioned.section_pairs(
                f'[{extension_entrypoint_group}]\n'
                f'{group_entry_points_lines}\n'
            )
        ]

        if not extension_entry_points:
            raise ValueError(
                'This package does not define any extension entry points.'
            )

        # Begin building pipeline bundles for each of the bundles defined
        # in the extension.
        from djblets.extensions.extension import Extension

        for entrypoint in extension_entry_points:
            try:
                extension_cls = cast(Type[Extension], entrypoint.load())
            except ImportError:
                sys.stderr.write(
                    'Error loading the extension for entry point %s\n'
                    % entrypoint.name)
                raise

            self._build_static_media(extension_cls)

        # Restore the environment, so we don't possibly interfere with
        # anything else.
        if old_settings_module is not None:
            os.environ['DJANGO_SETTINGS_MODULE'] = old_settings_module

        sys.path = sys.path[len(distribution.packages):]

    def _build_static_media(
        self,
        extension_cls: type[Extension],
    ) -> None:
        """Build static media files for the extension.

        This will configure Pipeline for the extension, install any
        dependencies required, and then compile the static media.

        Args:
            extension_cls (type):
                The extension being packaged.
        """
        from djblets.extensions.packaging.static_media import (
            StaticMediaBuildContext,
            StaticMediaBuilder,
        )

        build_root = self.build_lib
        assert build_root and isinstance(build_root, str)

        if not os.path.exists(build_root):
            os.makedirs(build_root)

        static_media_build_context_cls = (
            self.static_media_build_context_cls or
            StaticMediaBuildContext
        )

        static_media_builder_cls = (
            self.static_media_builder_cls or
            StaticMediaBuilder
        )

        # Build the context state that we'll be using throughout the build
        # process.
        if hasattr(self, 'get_lessc_global_vars'):
            class_name = type(self).__name__

            RemovedInDjblets70Warning.warn(
                f'{class_name}.get_lessc_global_vars() is deprecated. Please '
                f'set {class_name}.static_media_builder_cls to a subclass of '
                f'StaticMediaBuilder and override the method there instead. '
                f'This will be removed in Djblets 7.')

            # We need to supply these to the static builder via subclass.
            class _StaticMediaBuildContext(static_media_build_context_cls):
                def get_lessc_global_vars(_self):
                    return dict(super().get_lessc_global_vars(),
                                **self.get_lessc_global_vars())

            static_media_build_context_cls = _StaticMediaBuildContext

        build_context = static_media_build_context_cls.create_for_extension(
            extension_cls=extension_cls,
            source_root_dir=Path.cwd(),
            build_dir=Path(build_root))

        if not build_context.static_dir.exists():
            # There's no static media to build. We can bail now.
            return

        builder = static_media_builder_cls(build_context=build_context)
        self._builder = builder

        builder.prepare_build()
        builder.install_deps()

        # Call this for backwards-compatibility.
        if hasattr(self, 'install_pipeline_deps'):
            class_name = type(self).__name__

            RemovedInDjblets70Warning.warn(
                f'{class_name}.install_pipeline_deps() is deprecated. Please '
                f'set {class_name}.static_media_builder_cls to a subclass of '
                f'StaticMediaBuilder and override the method there instead. '
                f'This will be removed in Djblets 7.')
            self.install_pipeline_deps()  # type: ignore

        builder.build_static_media()

        if self.remove_source_files:
            builder.prune_source_files()


class BuildPy(build_py):
    """Setuptools command for building Python files.

    This is meant as a replacement for the standard ``build_py`` command
    that will trigger a build of static media files.

    Version Added:
        5.0:
        This was moved from :py:mod:`djblets.extensions.packaging`.
    """

    def run(self) -> None:
        """Run the command."""
        self.run_command('build_static_files')
        super().run()


def build_extension_cmdclass(
    *,
    build_static_files_cls: type[BuildStaticFiles],
) -> dict[str, type]:
    """Build a Setuptools cmdclass for building extensions.

    This is passed a subclass of :py:class:`BuildStaticFiles`, and returns
    something that can be passed to ``setup()``.

    Version Added:
        5.0:
        This was moved from :py:mod:`djblets.extensions.packaging`.

    Args:
        build_static_files_cls (type):
            The subclass of :py:class:`BuildStaticFiles`.

    Returns:
        dict:
        The resulting Setuptools command classes to use.
    """
    return {
        'build_static_files': build_static_files_cls,
        'build_py': BuildPy,
    }
