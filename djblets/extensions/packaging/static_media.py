"""A builder for static media files.

Version Added:
    5.0
"""

from __future__ import annotations

import inspect
import json
import os
import re
import sys
from pathlib import Path
from typing import (Dict, Optional, Sequence, TYPE_CHECKING, TypeVar,
                    Union, cast)

from django.core.management import call_command
from django.utils.translation import gettext as _
from typing_extensions import Self, TypeAlias

import djblets
from djblets.extensions.errors import ExtensionPackagingError
from djblets.pipeline.settings import build_pipeline_settings
from djblets.util.filesystem import is_exe_in_path

if TYPE_CHECKING:
    from djblets.extensions.extension import (CSSBundleConfigs,
                                              Extension,
                                              JSBundleConfigs)
    from djblets.util.typing import JSONDict

    _BundleConfigsT = TypeVar('_BundleConfigsT',
                              CSSBundleConfigs,
                              JSBundleConfigs)


#: A valid value for a LessCSS variable.
#:
#: Version Added:
#:     5.0
LessCSSValueType: TypeAlias = Union[bool, int, str]


#: A mapping of LessCSS variable names to values.
#:
#: Version Added:
#:     5.0
LessCSSVariables: TypeAlias = Dict[str, LessCSSValueType]


#: A mapping of NPM workspace names to paths.
#:
#: Version Added:
#:     5.0
NPMWorkspaceDirs: TypeAlias = Dict[str, Union[Path, str]]


class StaticMediaBuildContext:
    """Context for performing a static media build for an extension.

    Version Added:
        5.0
    """

    ######################
    # Instance variables #
    ######################

    #: The ID of the package being built.
    #:
    #: Type:
    #:     str
    package_id: str

    #: The absolute path to the root of the source tree.
    #:
    #: Type:
    #:     pathlib.Path
    source_root_dir: Path

    #: The absolute path to the target build directory for the package.
    #:
    #: Type:
    #:     pathlib.Path
    build_dir: Path

    #: The absolute path to the project's NPM workspaces directory.
    #:
    #: Type:
    #:     pathlib.Path
    workspaces_dir: Path

    #: The absolute path to the project's node_modules directory.
    #:
    #: Type:
    #:     pathlib.Path
    node_modules_dir: Path

    #: The absolute path to the source static directory for the extension.
    #:
    #: Type:
    #:     pathlib.Path
    static_dir: Path

    #: The normalized Pipeline CSS bundles to build.
    #:
    #: Type:
    #:     dict
    pipeline_css_bundles: CSSBundleConfigs

    #: The normalized Pipeline JavaScript bundles to build.
    #:
    #: Type:
    #:     dict
    pipeline_js_bundles: JSBundleConfigs

    @classmethod
    def create_for_extension(
        cls,
        *,
        extension_cls: type[Extension],
        source_root_dir: Path,
        build_dir: Optional[Path] = None,
        package_id: Optional[str] = None,
    ) -> Self:
        """Initialize the static media build context for an extension class.

        This will prepare paths, scan the extension, and prepare the static
        media bundles for building with Pipeline.

        Args:
            extension_cls (type):
                The static media extension class.

            source_root_dir (pathlib.Path):
                The root of the source tree.

            build_dir (pathlib.Path, optional):
                The path to the build directory.

                If not provided, this will use a :file:`build` subdirectory off
                of ``source_root_dir``.

            package_id (str, optional):
                An explicit ID for the package.

                If not provided, the extension class name will be used.

        Returns:
            StaticMediaBuildContext:
            The build context.
        """
        # Get the location of the static/ directory within the module in the
        # source tree. We're going to use it to look up static files for
        # input, and as a relative path within the module for the output.
        static_dir = Path(inspect.getfile(extension_cls)).parent / 'static'

        return cls(source_root_dir=source_root_dir,
                   static_dir=static_dir,
                   build_dir=build_dir,
                   package_id=package_id or extension_cls.__name__,
                   css_bundles=extension_cls.css_bundles,
                   js_bundles=extension_cls.js_bundles)

    def __init__(
        self,
        *,
        package_id: str,
        css_bundles: CSSBundleConfigs,
        js_bundles: JSBundleConfigs,
        source_root_dir: Path,
        static_dir: Path,
        build_dir: Optional[Path] = None,
    ) -> None:
        """Initialize the static media build context.

        This will prepare paths, scan the extension, and prepare the static
        media bundles for building with Pipeline.

        Args:
            package_id (str):
                The ID of the package.

            css_bundles (dict):
                The CSS bundles to build.

            js_bundles (dict):
                The JavaScript bundles to build.

            source_root_dir (pathlib.Path):
                The root of the source tree.

            static_dir (pathlib.Path):
                The path to the source directory for static files.

            build_dir (pathlib.Path, optional):
                The path to the build directory.

                If not provided, this will use a :file:`build` subdirectory off
                of ``source_root_dir``.
        """
        source_root_dir = source_root_dir.absolute()

        if build_dir:
            build_dir = build_dir.absolute()

        self.package_id = package_id

        self.build_dir = build_dir or (source_root_dir / 'build')
        self.source_root_dir = source_root_dir
        self.workspaces_dir = source_root_dir / '.npm-workspaces'
        self.node_modules_dir = source_root_dir / 'node_modules'
        self.static_dir = static_dir

        self.pipeline_js_bundles = self._make_pipeline_bundle(
            extension_bundles=js_bundles,
            default_dir=Path('js'),
            ext='.js')
        self.pipeline_css_bundles = self._make_pipeline_bundle(
            extension_bundles=css_bundles,
            default_dir=Path('css'),
            ext='.css')

    def get_npm_workspace_dirs(self) -> NPMWorkspaceDirs:
        """Return NPM workspace directories and symlinks to set up.

        Subclasses can override this to return additional workspaces to
        include. The parent class should always be called and the results
        included.

        Returns:
            dict:
            A mapping of symlink names to target locations.
        """
        return {
            'djblets': Path(djblets.__file__).parent.absolute(),
        }

    def get_lessc_global_vars(self) -> LessCSSVariables:
        """Return a dictionary of LessCSS global variables and their values.

        This can be implemented by subclasses to provide global variables for
        .less files for processing.

        For backwards-compatibility, the following two variables are provided,
        but should not be used:

        ``DEBUG``:
            Set to false, always.

        ``STATIC_ROOT``:
            Set to ``/static/``, always.

        Subclasses can override this to return custom variables.

        Returns:
            dict:
            A dictionary mapping variable names to values.
        """
        return {
            'DEBUG': False,
            'STATIC_ROOT': '/static/',
        }

    def get_lessc_include_path(self) -> set[str]:
        """Return the include path for LessCSS imports.

        By default, this will include the parent directory of every path in
        ``settings.STATICFILES_DIRS``, plus the static directory of the
        extension.

        Returns:
            set of str:
            The de-duplicated set of include paths.
        """
        from django.conf import settings

        less_include: set[str] = set()

        for staticfile_dir in settings.STATICFILES_DIRS:
            if isinstance(staticfile_dir, tuple):
                staticfile_dir = staticfile_dir[1]

            dirname = os.path.dirname(staticfile_dir)
            less_include.add(dirname)

            if os.path.basename(dirname) == 'static':
                # This code is here for compatibility reasons. With a proper
                # Babel setup, .less files should be able to reference others
                # relative to static/ directories. However, some paths may
                # still prefix /static/ to any paths, and we don't want those
                # to break. So, add the parent of this static/ directory
                # in order to allow those lookups to continue working.
                dirname = os.path.dirname(dirname)

            less_include.add(dirname)

        less_include.add(str(self.node_modules_dir))

        return less_include

    def _make_pipeline_bundle(
        self,
        *,
        extension_bundles: _BundleConfigsT,
        default_dir: Path,
        ext: str,
    ) -> _BundleConfigsT:
        """Return a new Pipeline bundle based on an extension's bundle.

        Args:
            extension_bundles (dict):
                The bundles defined on the extension.

            default_dir (pathlib.Path):
                The default directory for the source files, for any bundles
                that don't specify an explicit output filename.

            ext (str):
                The default extension for the source files, for any bundles
                that don't specify an explicit output filename.

        Returns:
            dict:
            The new extension bundle.
        """
        return cast('_BundleConfigsT', {
            name: {
                'source_filenames': list(bundle['source_filenames']),
                'output_filename': (
                    bundle.get('output_filename') or
                    str(default_dir / f'{name}.min{ext}')
                ),
                **{
                    key: bundle.get(key)
                    for key in ('compiler_options',
                                'extra_context',
                                'variant')
                    if key in bundle
                }
            }
            for name, bundle in extension_bundles.items()
        })


class StaticMediaBuilder:
    """A builder for an extension's static media files.

    This is responsible for setting up the build process for CSS and
    JavaScript files for an extension. It will configure Django and Pipeline
    for the build process, collect any information needed to set up the
    build tree (which can be customized via subclasses), and then perform
    the build.

    Version Added:
        5.0
    """

    ######################
    # Instance variables #
    ######################

    #: The build context used for this build.
    #:
    #: Type:
    #:     type
    build_context: StaticMediaBuildContext

    #: Whether NPM support has been checked.
    #:
    #: Type:
    #:     bool
    _checked_npm: bool

    def __init__(
        self,
        *,
        build_context: StaticMediaBuildContext,
    ) -> None:
        """Initialize the builder.

        Args:
            build_context (StaticMediaBuildContext):
                The context used for the build.
        """
        self.build_context = build_context
        self._checked_npm = False

    def prepare_build(self) -> None:
        """Prepare the initial steps for the build.

        This will set up the initial directories and Django environment for
        the build process.
        """
        self.ensure_build_files()
        self.prepare_django_env()

    def ensure_build_files(self) -> None:
        """Set up the build tree and configuration files.

        This will set up the NPM workspaces and a starting
        :file:`package.json` file that can be used to manage the build.

        If there are any changes to the :file:`package.json` in the tree,
        they will be reported to the user.
        """
        build_context = self.build_context
        source_dir = build_context.source_root_dir
        workspaces_dir = build_context.workspaces_dir
        npm_workspace_dirs = build_context.get_npm_workspace_dirs()

        for path in (build_context.build_dir,
                     workspaces_dir):
            if not path.exists():
                path.mkdir(0o755)

        for (npm_workspace_name,
             npm_workspace_dir) in npm_workspace_dirs.items():
            npm_workspace_symlink = workspaces_dir / npm_workspace_name

            if npm_workspace_symlink.exists():
                if npm_workspace_symlink.is_symlink():
                    npm_workspace_symlink.unlink()
                else:
                    sys.stderr.write(
                        _('Cannot symlink %(workspace_name)s to '
                          '%(workspace_target)s. This may cause problems '
                          'building your extension. Check if you can remove '
                          'this path in your tree and try again.')
                        % {
                            'workspace_name': npm_workspace_symlink,
                            'workspace_target': npm_workspace_dir,
                        })
                    continue

            npm_workspace_symlink.symlink_to(npm_workspace_dir)

        # Generate a package.json to install the dependencies for building
        # static media. If there's already one, don't remove it.
        package_json_path = source_dir / 'package.json'
        package_json = self.build_package_json()

        if package_json_path.exists():
            with package_json_path.open('r') as fp:
                existing_package_json = json.load(fp)

            if package_json != existing_package_json:
                # Check if there's anything that may have changed that we
                # would want to set.
                for key, value in package_json.items():
                    if (key not in ('private', 'name') and
                        (key not in existing_package_json or
                         value != existing_package_json[key])):
                        # We found something that may need to be updated.
                        # Complain about it, show the updates, and then
                        # move on.
                        print()
                        print('-' * 75)
                        print()
                        print(f'WARNING: Cowardly refusing to overwrite '
                              f'{package_json_path} with these settings:')
                        print()
                        print(json.dumps(package_json,
                                         indent=2,
                                         sort_keys=True))
                        print()
                        print('You may need to make these changes to your '
                              'own copy manually.')
                        print()
                        print('-' * 75)
                        print()
                        break
        else:
            with package_json_path.open('w') as fp:
                json.dump(package_json,
                          fp,
                          indent=2,
                          sort_keys=True)
                fp.write('\n')

    def prepare_django_env(self) -> None:
        """Set up the Django environment.

        This will set up the settings for both Django and Pipeline to
        control the build process.

        The CSS and JavaScript bundles will be set in Pipeline so that
        Django's build process will run them through Pipeline, outputting to
        the right build directory.
        """
        from django.conf import settings
        from djblets.extensions.staticfiles import PackagingFinder
        from pipeline.conf import settings as pipeline_settings

        build_context = self.build_context
        static_dir = build_context.static_dir

        PackagingFinder.extension_static_dir = str(static_dir)

        settings.STATICFILES_FINDERS = (
            'djblets.extensions.staticfiles.PackagingFinder',
        )
        settings.STORAGES['staticfiles']['BACKEND'] = \
            'djblets.extensions.staticfiles.PackagingCachedFilesStorage'

        settings.STATICFILES_DIRS = [
            *settings.STATICFILES_DIRS,
            str(static_dir),
        ]

        static_root = str(
            build_context.build_dir /
            static_dir.relative_to(Path.cwd())
        )
        settings.STATIC_ROOT = static_root

        settings.INSTALLED_APPS = [
            'django.contrib.staticfiles',
        ]
        settings.CACHES = {
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            },
        }

        # Update the Pipeline settings.
        pipeline_settings.update(build_pipeline_settings(
            pipeline_enabled=True,
            node_modules_path=str(build_context.node_modules_dir),
            static_root=static_root,
            javascript_bundles=build_context.pipeline_js_bundles,
            stylesheet_bundles=build_context.pipeline_css_bundles,
            use_rollup=True,
            extra_config={
                # Tell djblets.pipeline.compiles.less.LessCompiler not to
                # check for outdated files using its special import script,
                # and to in fact assume all files are outdated so they'll
                # all be rebuilt. This will also prevent access denied
                # issues (due to referenced files not being in the
                # sandboxed tree defined for the static media).
                '_DJBLETS_LESS_ALWAYS_REBUILD': True,

                # Overwrite the arguments from build_pipeline_settings(),
                # and add our own instead.
                'LESS_ARGUMENTS': self._build_lessc_args(),
            }))

    def build_package_json(self) -> JSONDict:
        """Return the contents for a default package.json file.

        Subclasses can override this to return custom content.

        Returns:
            dict:
            The default :file:`package.json` contents.
        """
        build_context = self.build_context
        workspaces_rel_dir = (
            build_context.workspaces_dir
            .relative_to(build_context.source_root_dir)
        )

        return {
            'name': build_context.package_id,
            'private': True,
            'workspaces': [
                f'{workspaces_rel_dir}/*',
            ],
        }

    def install_deps(self) -> None:
        """Install dependencies for building static media.

        This will run :command:`npm install`.
        """
        cwd = os.getcwd()
        os.chdir(self.build_context.source_root_dir)

        try:
            self.npm_install()
        finally:
            os.chdir(cwd)

    def build_static_media(self) -> None:
        """Build static media for the extension."""
        call_command('collectstatic', interactive=False, verbosity=2)

    def prune_source_files(self) -> None:
        """Prune any source files from the package.

        This can be used to produce a Python package without any of the
        source CSS and JavaScript files. Only the final bundles will be
        left behind.
        """
        from django.conf import settings

        build_context = self.build_context
        static_root = Path(settings.STATIC_ROOT)

        # Remove source files from the package, if requested by the
        # packager. This will leave only the CSS and JavaScript bundles.
        self._remove_source_files(build_context.pipeline_css_bundles,
                                  static_root / 'css')
        self._remove_source_files(build_context.pipeline_js_bundles,
                                  static_root / 'js')

    def npm_install(
        self,
        package_spec: Optional[str] = None,
        /,
    ) -> None:
        """Install a package via npm.

        This will first determine if npm is available, and then attempt to
        install the given package.

        Args:
            package_spec (str, optional):
                The package specification (name and optional version range)
                to install.

                If not specified, this will use the default behavior of
                reading :file:`package.json`.

        Raises:
            djblets.extensions.errors.ExtensionPackagingError:
                :command:`npm` could not be found, or there was an error
                installing the package.
        """
        if not self._checked_npm:
            if not is_exe_in_path('npm'):
                raise ExtensionPackagingError(
                    _('Unable to locate npm in the path, which is needed to '
                      'install %s. Static media cannot be built.')
                    % package_spec)

            self._checked_npm = True

        if package_spec:
            # Ensure there's a node_modules directory here (which should be
            # the source directory), so it doesn't install higher up in the
            # directory hierarchy.
            if not os.path.exists('node_modules'):
                os.mkdir('node_modules', 0o755)

            print(_('Installing %(npm_package_spec)s...') % {
                'npm_package_spec': package_spec,
            })
            result = os.system(f'npm install {package_spec}')
        else:
            print(_('Installing npm packages...'))
            result = os.system('npm install')

        if result != 0:
            raise ExtensionPackagingError(_('Installation from npm failed.'))

    def _remove_source_files(
        self,
        pipeline_bundles: _BundleConfigsT,
        media_build_dir: Path,
    ) -> None:
        """Remove all source files, leaving only built bundles.

        Args:
            pipeline_bundles (dict):
                The pipeline bundles to scan for files to remove.

            media_build_dir (str):
                The path to the build directory for the files.
        """
        for root, dirs, files in os.walk(media_build_dir, topdown=False):
            for name in files:
                # A valid file will be represented as one of:
                #
                #     (bundle_name, 'min', stamp, ext)
                #     (bundle_name, 'min', ext)
                #
                # We keep both the pre-stamped and post-stamped versions so
                # that Django's CachedFilesStorage can generate and cache
                # the stamp from the contents of the non-stamped file.
                name_parts = name.split('.')

                if (len(name_parts) < 3 or
                    name_parts[0] not in pipeline_bundles or
                    name_parts[1] != 'min'):
                    # This doesn't appear to be a file representing a bundle,
                    # so we should get rid of it.
                    os.unlink(os.path.join(root, name))

            for name in dirs:
                try:
                    os.rmdir(os.path.join(root, name))
                except Exception:
                    # The directory is probably not empty yet.
                    pass

    def _build_lessc_args(self) -> Sequence[str]:
        """Build the list of arguments for the less compiler.

        This will return a set of arguments that define any global variables
        or include paths for the less compiler. It respects most existing
        arguments already in ``settings.PIPELINE['LESS_ARGUMENTS']``, but
        will filter out any existing include paths and global variables needed
        for packaging.

        Returns:
            list:
            A list of arguments to pass to lessc.
        """
        from django.conf import settings

        build_context = self.build_context

        # Get all the arguments that the application defines, but remove those
        # that we need to override or the ones that aren't compatible with
        # building this media.
        lessc_global_vars = build_context.get_lessc_global_vars()
        exclude_re = re.compile(
            '^--(include-path=|global-var="?(%s)=)'
            % '|'.join(
                re.escape(global_var)
                for global_var in lessc_global_vars.keys()
            ))

        lessc_args = [
            lessc_arg
            for lessc_arg in settings.PIPELINE.get('LESS_ARGUMENTS', [])
            if not exclude_re.match(lessc_arg)
        ]

        lessc_include_paths = sorted(build_context.get_lessc_include_path())

        # Register the include path and any global variables used for
        # building .less files.
        return [
            *lessc_args,
            '--include-path=%s' % os.path.pathsep.join(lessc_include_paths),
            *(
                '--global-var=%s=%s'
                % (key, self._serialize_lessc_value(value))
                for key, value in lessc_global_vars.items()
            )
        ]

    def _serialize_lessc_value(
        self,
        value: LessCSSValueType,
    ) -> str:
        """Serialize a LessCSS-compatible value to a string.

        Args:
            value (LessCSSValueType):
                The value type to serialize.

        Returns:
            str:
            The serialized representation of the value.

        Raises:
            TypeError:
                The provided value passed in is not a valid type.
        """
        if isinstance(value, str):
            return '"%s"' % value.replace('"', r'\"')
        elif isinstance(value, bool):
            if value:
                return 'true'
            else:
                return 'false'
        elif isinstance(value, int):
            return str(value)
        else:
            raise TypeError(
                f'{value!r} is not a valid LessCSS global variable value.'
            )
