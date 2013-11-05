import inspect
import os
import sys

import pkg_resources
from distutils.command.build_py import build_py
from distutils.core import Command
from django.conf import settings
from django.core.management import call_command
from django.utils import six


class BuildStaticFiles(Command):
    """Builds static files for the extension.

    This will build the static media files used by the extension. JavaScript
    bundles will be minified and versioned. CSS bundles will be processed
    through lesscss (if using .less files), minified and versioned.

    This must be subclassed by the project offering the extension support.
    The subclass must provide the extension_entrypoint_group and
    django_settings_module parameters.

    extension_entrypoint_group is the group name that entry points register
    into.

    django_settings_module is the Python module path for the project's
    settings module, for use in the DJANGO_SETTINGS_MODULE environment
    variable.
    """
    description = 'Build static media files'
    extension_entrypoint_group = None
    django_settings_module = None

    def initialize_options(self):
        self.build_lib = None

    def finalize_options(self):
        self.set_undefined_options('build', ('build_lib', 'build_lib'))

    def run(self):
        # Prepare to import the project's settings file, and the extension
        # modules that are being shipped, so we can scan for the bundled
        # media.
        old_settings_module = os.environ.get('DJANGO_SETTINGS_MODULE')
        os.environ['DJANGO_SETTINGS_MODULE'] = self.django_settings_module
        cwd = os.getcwd()
        sys.path = [
            os.path.join(cwd, package_name)
            for package_name in self.distribution.packages
        ] + sys.path

        # Set up the common Django settings for the builds.
        settings.STATICFILES_FINDERS = (
            'django.contrib.staticfiles.finders.FileSystemFinder',
        )
        settings.STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'
        settings.INSTALLED_APPS = [
            'django.contrib.staticfiles',
        ]
        settings.CACHES = {
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            },
        }

        # Load the entry points this package is providing, so we'll know
        # which extensions to scan.
        entrypoints = pkg_resources.EntryPoint.parse_map(
            self.distribution.entry_points,
            dist=self.distribution)

        extension_entrypoints = \
            entrypoints.get(self.extension_entrypoint_group)
        assert extension_entrypoints, 'No extension entry points were defined.'

        # Begin building pipeline bundles for each of the bundles defined
        # in the extension.
        for ep_name, entrypoint in six.iteritems(extension_entrypoints):
            try:
                extension = entrypoint.load(require=False)
            except ImportError:
                sys.stderr.write('Error loading the extension for entry '
                                 'point %s\n' % ep_name)
                raise

            self._build_static_media(extension)

        # Restore the environment, so we don't possibly interfere with
        # anything else.
        if old_settings_module is not None:
            os.environ['DJANGO_SETTINGS_MODULE'] = old_settings_module

        sys.path = sys.path[len(self.distribution.packages):]

    def _build_static_media(self, extension):
        pipeline_js = {}
        pipeline_css = {}

        self._add_bundle(pipeline_js, extension.js_bundles, 'js', '.js')
        self._add_bundle(pipeline_css, extension.css_bundles, 'css', '.css')

        # Get the location of the static/ directory within the module in the
        # source tree. We're going to use it to look up static files for
        # input, and as a relative path within the module for the output.
        module_dir = os.path.dirname(inspect.getmodule(extension).__file__)

        # Set the appropriate settings in order to build these static files.
        settings.PIPELINE_JS = pipeline_js
        settings.PIPELINE_CSS = pipeline_css
        settings.PIPELINE_ENABLED = True
        settings.STATICFILES_DIRS = [
            os.path.join(module_dir, 'static')
        ]
        settings.STATIC_ROOT = \
            os.path.join(self.build_lib,
                         os.path.relpath(os.path.join(module_dir, 'static')))

        # Due to how Pipeline copies and stores its settings, we actually
        # have to copy over some of these, as they'll be from the original
        # loaded settings.
        from pipeline.conf import settings as pipeline_settings

        pipeline_settings.PIPELINE_JS = settings.PIPELINE_JS
        pipeline_settings.PIPELINE_CSS = settings.PIPELINE_CSS
        pipeline_settings.PIPELINE_ENABLED = settings.PIPELINE_ENABLED
        pipeline_settings.PIPELINE_ROOT = settings.STATIC_ROOT

        # Collect and process all static media files.
        call_command('collectstatic', interactive=False, verbosity=2)

    def _add_bundle(self, pipeline_bundles, extension_bundles, default_dir,
                    ext):
        for name, bundle in six.iteritems(extension_bundles):
            if 'output_filename' not in bundle:
                bundle['output_filename'] = \
                    '%s/%s.min%s' % (default_dir, name, ext)

            pipeline_bundles[name] = bundle


class BuildPy(build_py):
    def run(self):
        self.run_command('build_static_files')
        build_py.run(self)


def build_extension_cmdclass(build_static_files_cls):
    """Builds a cmdclass to pass to setup.

    This is passed a subclass of BuildStaticFiles, and returns something
    that can be passed to setup().
    """
    return {
        'build_static_files': build_static_files_cls,
        'build_py': BuildPy,
    }
