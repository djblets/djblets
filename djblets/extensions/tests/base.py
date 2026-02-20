"""Base support for djblets.extensions unit tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from importlib_metadata import Distribution, EntryPoint

from djblets.extensions.manager import ExtensionManager

if TYPE_CHECKING:
    import os
    from typing import Any
    from unittest import TestCase

    from djblets.extensions.base import Extension

    MixinParent = TestCase
else:
    MixinParent = object


class FakeDistribution(Distribution):
    """A fake distribution.

    Version Added:
        6.0
    """

    ######################
    # Instance variables #
    ######################

    #: The project name.
    _project_name: str

    #: The project version.
    _version: str

    #: The metadata dictionary.
    _metadata: dict[str, Any]

    def __init__(
        self,
        *,
        project_name: str = 'ExampleProject',
        version: str = '1.0',
        metadata: (dict[str, Any] | None) = None,
    ) -> None:
        """Initialize the distribution.

        Args:
            project_name (str, optional):
                The name of the extension package.

            version (str, optional):
                The version of the extension package.

            metadata (dict, optional):
                Metadata for the distribution.
        """
        self._project_name = project_name
        self._version = version
        self._metadata = {
            'Author': 'Example Author',
            'Author-email': 'author@example.com',
            'Description': 'Test description\u2049',
            'Home-page': 'http://example.com',
            'Name': project_name,
            'License': 'Drivers',
            'Summary': 'Test summary',
            'Version': version,
        }

        if metadata:
            self._metadata.update(metadata)

    def read_text(
        self,
        filename: str,
    ) -> str | None:
        """Attempt to read a file.

        This is used to return the metadata for the fake package.

        Args:
            filename (str):
                The file to read.

        Returns:
            str or None:
            The metadata as a string.
        """
        return '\n'.join(
            f'{key}: {value}'
            for key, value in self._metadata.items()
        )

    def locate_file(
        self,
        path: str | os.PathLike[str],
    ) -> Any:
        """Return a path for a file in the distribution.

        This method must be implemented in order to create a subclass of the
        abstract base, but we don't actually use it.

        Args:
            path (str or os.PathLike):
                The path to search for.

        Returns:
            object:
            The path object.
        """
        raise NotImplementedError


class FakeEntryPoint(EntryPoint):
    """A fake entry point.

    Version Changed:
        6.0:
        Changed to inherit from importlib_metadata.EntryPoint.
    """

    _value: type[Extension]

    def __init__(
        self,
        value: type[Extension],
        *,
        project_name: str,
        version: str = '1.0',
        **metadata_kwargs,
    ) -> None:
        """Initialize the FakeEntryPoint.

        Args:
            value (object):
                The value to be returned when the entry point is loaded.

            project_name (str):
                The project name. This will be set in the metadata and as
                the distribution's name.

            version (str, optional):
                The project version.

            **metadata_kwargs (dict):
                Keyword arguments to pass to the associated
                :py:class:`FakeDistribution` constructor.
        """
        dist = FakeDistribution(
            project_name=project_name,
            version=version,
            metadata=metadata_kwargs,
        )

        vars(self).update(_value=value, dist=dist)

    def load(self) -> Any:
        """Load the entry point.

        Returns:
            object: The value specified at initialization time.
        """
        return self._value


class MyTestExtensionManager(ExtensionManager):
    """An extension manager for testing.

    The entry points are provided at initialization time.
    """

    def __init__(self, entry_points=None, *args, **kwargs):
        """Initialize the MyTestExtensionManager.

        Args:
            entry_points (list):
                A list of :py:class:`FakeEntryPoint`s.

            *args (tuple):
                Additional positional arguments to pass to the base class'
                constructor.

            **kwargs (dict):
                Additional keyword arguments to pass to the base class'
                constructor.
        """
        super(MyTestExtensionManager, self).__init__(*args, **kwargs)
        self._entry_points = entry_points or []

    def _entrypoint_iterator(self):
        """Return the entry points.

        Returns:
            list: The entry points.
        """
        return self._entry_points


class ExtensionTestsMixin(MixinParent):
    """Mixin for Djblets extension-related unit tests.

    This is used to help set up an extension and extension manager to test
    with.

    This shouldn't generally be used by third-parties writing unit tests for
    their extensions. For those, see
    :py:mod:`djblets.extensions.testing.testcases`.
    """

    #: The project name to use in the entrypoint.
    test_project_name = 'TestProject'

    def setUp(self) -> None:
        """Set up state before a test run."""
        super().setUp()

        self.manager = None

    def tearDown(self) -> None:
        """Tear down state after a test run.

        This will properly ensure that the extension manager, if one was
        created, will clear all state and shut down.
        """
        super().tearDown()

        if self.manager:
            self.manager.clear_sync_cache()
            self.manager.shutdown()

    def setup_extension(
        self,
        extension_cls: type[Extension],
        enable: bool = True,
        manager_key: str = 'tests',
    ) -> Extension | None:
        """Set up an extension for use in a test.

        This will register the class in a new extension manager and then
        enable or otherwise instantiate the extension, returning the instance.

        Args:
            extension_cls (type):
                The extension class to register.

            enable (bool, optional):
                Whether the returned extension should be enabled.

            manager_key (str, optional):
                The key to use for the extension manager.

        Returns:
            djblets.extensions.extension.Extension:
            The resulting extension instance.
        """
        fake_entry_point = FakeEntryPoint(extension_cls,
                                          project_name=self.test_project_name)

        self.manager = MyTestExtensionManager([fake_entry_point], manager_key)
        self.manager.load()

        if enable:
            return self.manager.enable_extension(extension_cls.id)
        else:
            return extension_cls(self.manager)
