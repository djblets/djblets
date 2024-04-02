"""Support for packaging extensions.

Version Changed:
    5.0:
    This has been split into sub-modules. Consumers should update any older
    imports for this module to instead import from
    :py:mod:`djblets.extensions.packaging.setuptools_backend`.
"""

# NOTE: It's important not to import anything directly in this module that
#       depends on a configured Django environment.

from __future__ import annotations

from typing import Any, Optional

from housekeeping import ClassMovedMixin, func_moved

from djblets.deprecation import RemovedInDjblets70Warning
import djblets.extensions.packaging.setuptools_backend as setuptools_backend


class BuildPy(ClassMovedMixin,
              setuptools_backend.BuildPy,
              warning_cls=RemovedInDjblets70Warning):
    """Setuptools command for building Python files.

    This is meant as a replacement for the standard ``build_py`` command
    that will trigger a build of static media files.

    Deprecated:
        5.0:
        This has been moved to :py:class:`djblets.extensions.packaging.
        setuptools_backend.BuildPy`. The legacy import will be removed in
        Djblets 7.
    """


class BuildStaticFiles(ClassMovedMixin,
                       setuptools_backend.BuildStaticFiles,
                       warning_cls=RemovedInDjblets70Warning):
    """Builds static files for the extension.

    This will build the static media files used by the extension. JavaScript
    bundles will be minified and versioned. CSS bundles will be processed
    through LessCSS (if using :file:`.less` files), minified and versioned.

    This must be subclassed by the project offering the extension support.
    The subclass must provide the :py:attr:`extension_entrypoint_group` and
    :py:attr:`django_settings_module parameters`.

    Deprecated:
        5.0:
        This has been moved to :py:class:`djblets.extensions.packaging.
        setuptools_backend.BuildStaticFiles`. The legacy import will be
        removed in Djblets 7.
    """

    def npm_install(
        self,
        package_spec: Optional[str] = None,
    ) -> None:
        """Install a package via npm.

        This will first determine if :command:`npm` is available, and then
        attempt to install the given package.

        Deprecated:
            5.0:
            This will be removed in Djblets 7. Please see
            :py:class:`~djblets.extensions.packaging.static_media.
            StaticMediaBuilder` for build customization.

        Args:
            package_spec (str, optional):
                The package specification (name and optional version range)
                to install. If not specified, this will use the default
                behavior of reading :file:`package.json`.
        """
        class_name = type(self).__name__
        RemovedInDjblets70Warning.warn(
            f'{class_name}.npm_install() is deprecated. Please set '
            f'{class_name}.static_media_builder_cls to a subclass of '
            f'StaticMediaBuilder and override an appropriate method '
            f'instead to install dependencies. This will be removed in '
            f'Djblets 7.')

        self._builder.npm_install(package_spec)

    def get_lessc_global_vars(self) -> dict[str, Any]:
        """Return a dictionary of LessCSS global variables and their values.

        This can be implemented by subclasses to provide global variables for
        .less files for processing.

        By default, this defines two variables: ``STATIC_ROOT`` and ``DEBUG``.

        ``STATIC_ROOT`` is set to ``/static/``. Any imports using
        ``@{STATIC_ROOT}`` will effectively look up the requested file in
        ``<import_path>/@{STATIC_ROOT}``. This assumes that the project
        serving the static files keeps them in :file:`static/{appname}/`.

        Projects using less.js for the runtime can then define ``STATIC_ROOT``
        to ``settings.STATIC_URL``, ensuring lookups work for development and
        packaged extensions.

        ``DEBUG`` is set to false. Runtimes using less.js can set this to
        ``settings.DEBUG`` for templates. This can be useful for LessCSS
        guards.

        Deprecated:
            5.0:
            This will be removed in Djblets 7. Please see
            :py:class:`~djblets.extensions.packaging.static_media.
            StaticMediaBuilder` for build customization.

        Returns:
            dict:
            A dictionary mapping variable names to values.
        """
        class_name = type(self).__name__
        RemovedInDjblets70Warning.warn(
            f'{class_name}.get_lessc_global_vars() is deprecated. Please set '
            f'{class_name}.static_media_builder_cls to a subclass of '
            f'StaticMediaBuilder and override an appropriate method '
            f'instead to install dependencies. This will be removed in '
            f'Djblets 7.')

        return {}


@func_moved(RemovedInDjblets70Warning,
            new_func=setuptools_backend.build_extension_cmdclass)
def build_extension_cmdclass(
    build_static_files_cls: type[BuildStaticFiles],
) -> dict[str, type]:
    """Build a Setuptools cmdclass for building extensions.

    This is passed a subclass of :py:class:`BuildStaticFiles`, and returns
    something that can be passed to ``setup()``.

    Deprecated:
        5.0:
        This has been moved to :py:class:`djblets.extensions.packaging.
        setuptools_backend.build_extension_cmdclass`. The legacy import will
        be removed in Djblets 7.

    Args:
        build_static_files_cls (type):
            The subclass of :py:class:`BuildStaticFiles`.

    Returns:
        dict:
        The resulting Setuptools command classes to use.
    """
    return setuptools_backend.build_extension_cmdclass(
        build_static_files_cls=build_static_files_cls)
