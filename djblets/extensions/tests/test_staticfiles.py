"""Unit tests for djblets.extensions.staticfiles.

Version Added:
    6.1.1
"""

from __future__ import annotations

import gc
import os
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from weakref import ref

from djblets.extensions.staticfiles import ExtensionFinder
from djblets.testing.testcases import TestCase


# Note that we don't need to test a real extension. We're caring about the
# storage and references for these tests. If that changes, we can make this
# more complicated, but one of the tests creates a lot of these.
class _MyExtension:
    id = 'test.extension'

    def __init__(
        self,
        location: str,
    ) -> None:
        self.info = SimpleNamespace(extract_resource=lambda name: location)


class ExtensionFinderTests(TestCase):
    """Unit tests for ExtensionFinder.

    Version Added:
        6.1.1
    """

    def test_get_storage_with_existing_storage_instance(self) -> None:
        """Testing ExtensionFinder._get_storage returns a cached result
        for the same extension
        """
        with TemporaryDirectory() as location:
            filename = os.path.join(location, 'test.css')

            with open(filename, 'w', encoding='ascii') as fp:
                fp.write('body {}')

            finder = ExtensionFinder()
            extension = _MyExtension(location)

            storage = finder._get_storage(extension)
            assert storage is not None

            self.assertEqual(storage.location, location)
            self.assertEqual(storage.prefix, 'ext/test.extension/')
            self.assertEqual(
                finder._find_in_extension(extension, 'test.css'),
                filename,
            )

            # A second call should return the same instance.
            self.assertIs(finder._get_storage(extension), storage)
            self.assertEqual(finder.storages, {
                extension: storage,
            })

    def test_get_storage_with_multiple_same_id(self) -> None:
        """Testing ExtensionFinder._get_storage returns different instances
        for different extension instances with the same ID
        """
        with TemporaryDirectory() as parent:
            storage1_path = os.path.join(parent, 'storage1')
            storage2_path = os.path.join(parent, 'storage2')

            os.mkdir(storage1_path, 0o700)
            os.mkdir(storage2_path, 0o700)

            finder = ExtensionFinder()

            extension1 = _MyExtension(storage1_path)
            extension1_ref = ref(extension1)
            storage1 = finder._get_storage(extension1)
            assert storage1 is not None

            extension2 = _MyExtension(storage2_path)
            storage2 = finder._get_storage(extension2)
            assert storage2 is not None

            self.assertIsNot(storage1, storage2)
            self.assertEqual(storage1.location, storage1_path)
            self.assertEqual(storage2.location, storage2_path)
            self.assertEqual(finder.storages, {
                extension1: storage1,
                extension2: storage2,
            })

            # Delete the extension from memory so the reference will go away.
            del extension1
            gc.collect()

            self.assertIsNone(extension1_ref())
            self.assertEqual(finder.storages, {
                extension2: storage2,
            })
            self.assertIs(finder._get_storage(extension2), storage2)

    def test_storages_with_extension_gc(self) -> None:
        """Testing ExtensionFinder discards extension state when extension
        is garbage collected
        """
        with TemporaryDirectory() as location:
            finder = ExtensionFinder()
            extension = _MyExtension(location)
            extension_ref = ref(extension)

            storage = finder._get_storage(extension)
            assert storage is not None

            self.assertEqual(storage.location, location)
            self.assertTrue(storage.exists(''))

            # Delete the extension from memory so the reference will go away.
            del extension
            gc.collect()

            self.assertIsNone(extension_ref())
            self.assertEqual(finder.storages, {})

    def test_storages_with_extension_gc_many(self) -> None:
        """Testing ExtensionFinder discards extension state when extension
        is garbage collected (pathological case)
        """
        with TemporaryDirectory() as location:
            finder = ExtensionFinder()
            extension_refs: list[ref[_MyExtension]] = []
            extension: (_MyExtension | None) = None

            # Create a whole bunch of extensions so we can make sure they
            # stay when we delete just one of them. Each will go out of scope
            # when garbage-collected, since nothing's holding onto the
            # references but the weakrefs.
            for i in range(100):
                extension = _MyExtension(location)
                extension_refs.append(ref(extension))
                finder._get_storage(extension)

                # Be explicit about clearing from the scope.
                extension = None

            gc.collect()

            for extension_ref in extension_refs:
                extension = extension_ref()

                self.assertIsNone(
                    extension,
                    f'Extension {extension} has an active ref!',
                )

            self.assertEqual(finder.storages, {})

    def test_ignored_extensions_with_extension_gc(self) -> None:
        """Testing ExtensionFinder.ignored_extensions discards state when
        extension is garbage collected
        """
        with TemporaryDirectory() as parent:
            finder = ExtensionFinder()
            extension = _MyExtension(os.path.join(parent, 'missing'))
            extension_ref = ref(extension)

            # Nothing should be in here to start with, since the storage
            # path was missing.
            self.assertIsNone(finder._get_storage(extension))
            self.assertIn(extension, finder.ignored_extensions)
            self.assertEqual(finder.storages, {})

            # Delete the extension from memory so the reference will go away.
            del extension
            gc.collect()

            self.assertIsNone(extension_ref())

            # It should have dropped from the ignored extensions.
            self.assertFalse(finder.ignored_extensions)
