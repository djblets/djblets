from __future__ import unicode_literals

import os

from django.contrib.staticfiles.finders import (BaseFinder, FileSystemFinder,
                                                get_finder)
from django.contrib.staticfiles.utils import get_files
from django.core.files.storage import FileSystemStorage
from pipeline.storage import PipelineFinderStorage
from pkg_resources import resource_exists, resource_filename

from djblets.extensions.manager import get_extension_managers


class ExtensionStaticStorage(FileSystemStorage):
    """Provides access to static files owned by an extension.

    This is a thin wrapper around FileSystemStorage that determines the
    path to the static directory within the extension. It will only operate
    on files within that path.
    """
    source_dir = 'static'
    prefix = None

    def __init__(self, extension, *args, **kwargs):
        location = resource_filename(extension.__class__.__module__,
                                     self.source_dir)

        super(ExtensionStaticStorage, self).__init__(location, *args, **kwargs)


class ExtensionFinder(BaseFinder):
    """Finds static files within enabled extensions.

    ExtensionFinder can list static files belonging to an extension, and
    find the path of a static file, given an extension ID and path.

    All static files are expected to be in the form of
    ``ext/<extension_id>/<path>``, where ``extension_id`` is the ID given to
    an extension (based on the full class path for the extension class).

    An extension is only valid if it has a "static" directory.
    """
    storage_class = ExtensionStaticStorage

    def __init__(self, *args, **kwargs):
        super(ExtensionFinder, self).__init__(*args, **kwargs)

        self.storages = {}
        self.ignored_extensions = set()

    def list(self, ignore_patterns):
        """Lists static files within all enabled extensions."""
        for extension_manager in get_extension_managers():
            for extension in extension_manager.get_enabled_extensions():
                storage = self._get_storage(extension)

                if storage and storage.exists(''):
                    for path in get_files(storage, ignore_patterns):
                        yield path, storage

    def find(self, path, all=False):
        """Finds the real path to a static file, given a static path.

        The path must start with "ext/<extension_id>/". The files within will
        map to files within the extension's "static" directory.
        """
        parts = path.split('/', 2)

        if len(parts) < 3 or parts[0] != 'ext':
            return []

        extension_id, path = parts[1:]

        for extension_manager in get_extension_managers():
            extension = extension_manager.get_enabled_extension(extension_id)

            if extension:
                match = self._find_in_extension(extension, path)

                if match:
                    # The static file support allows for the same name
                    # across many locations, but as we involve extension IDs,
                    # we know we'll only have one.
                    if all:
                        return [match]
                    else:
                        return match

                break

        return []

    def _find_in_extension(self, extension, path):
        storage = self._get_storage(extension)

        if storage and storage.exists(path):
            matched_path = storage.path(path)

            if matched_path:
                return matched_path

        return None

    def _get_storage(self, extension):
        if extension in self.ignored_extensions:
            return None

        storage = self.storages.get(extension)

        if storage is None:
            storage = self.storage_class(extension)

            if not os.path.isdir(storage.location):
                self.ignored_extensions.add(extension)
                return None

            self.storages[extension] = storage

        return storage


class PackagingStorage(PipelineFinderStorage):
    """Looks up stored files when packaging an extension.

    This is a special Pipeline static file storage implementation that can
    locate the proper Storage class when trying to find a file.

    This works just like PipelineFinderStorage, but can interface with
    PackagingFinder to trigger a lookup across all storages, since
    PackagingFinder by default limits to the extension's static files.
    """
    def find_storage(self, name):
        for finder in self.finders.get_finders():
            if isinstance(finder, PackagingFinder):
                files = finder.list([], all_storages=True)
            else:
                files = finder.list([])

            for path, storage in files:
                prefix = getattr(storage, 'prefix', None)
                matched_path = self.match_location(name, path, prefix)

                if matched_path:
                    return matched_path, storage

        raise ValueError("The file '%s' could not be found with %r."
                         % (name, self))


class PackagingFinder(FileSystemFinder):
    """Finds static media files for an extension.

    This is used during packaging to list only static media files provided by
    the extension, but to allow looking up static media from all apps.

    It works with PackagingStorage to do the appropriate lookup given the
    parameters passed.

    Essentially, when collecting static media (using the collectstatic
    management command), Django will call `list()` on the finders, grabbing
    every known static file, and packaging those. For extensions, we don't
    want to grab media files from the main apps, and want to limit only to the
    files bundled with the extension.

    There are times when we do want to list all files, though. For example,
    when referencing definitions files provided by the project for .less
    files.

    In the default case, PackagingFinder.list will only look up files from
    the extension, but if given an extra parameter that PackagingStorage
    can pass (used for finding referenced files), it will look through all
    storages.
    """
    storage_class = PackagingStorage
    extension_static_dir = None

    def list(self, ignore_patterns, all_storages=False):
        if all_storages:
            locations = self.locations
        else:
            locations = [('', self.extension_static_dir)]

        for prefix, root in locations:
            storage = self.storages[root]

            for path in get_files(storage, ignore_patterns):
                yield path, storage
