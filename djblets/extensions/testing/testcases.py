"""Mixins for test cases that need to test enabled extensions."""

from __future__ import annotations

import os
import uuid
import weakref
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Union

import importlib_metadata

from djblets.extensions.extension import ExtensionInfo
from djblets.extensions.manager import (ExtensionManager,
                                        get_extension_managers,
                                        _extension_managers)
from djblets.extensions.models import RegisteredExtension


class _FakeProvider:
    """A fake provider for a distribution.

    Version Added:
        2.3
    """

    egg_info = '/fake/path'

    def __init__(self, author='Example Author',
                 author_email='author@example.com',
                 description='Test description\u2049',
                 home_page='http://example.com',
                 project_name='ExampleProject', license_name='Drivers',
                 summary='Test summary', version='1.0'):
        """Initialize the FakeDistribution.

        Args:
            author (unicode):
                The package author.

            author_email (unicode):
                The package author's e-mail address.

            description (unicode):
                The package description.

            home_page (unicode):
                The package's URL.

            project_name (unicode):
                The package's name.

            license_name (unicode):
                The name of the package license.

            summary (unicode):
                The package summary.
        """
        self.metadata = {
            'Author': author,
            'Author-email': author_email,
            'Description': description,
            'Home-page': home_page,
            'Name': project_name,
            'License': license_name,
            'Summary': summary,
            'Version': version,
        }

    def _get(self, path):
        """Return the metadata content.

        This is the method that package resource providers must override to
        return metadata content for the package. It's expected to return
        byte strings, which will then be handled through the normal metadata
        functions.

        Returns:
            bytes:
            The package metadata content.
        """
        return ''.join(
            '%s: %s\n' % (field_name, value)
            for field_name, value in self.metadata.items()
        ).encode('utf-8')


class _FakeDistribution(importlib_metadata.Distribution):
    """A fake packaging distribution.

    Version Added:
        3.3
    """

    def __init__(
        self,
        files,
    ) -> None:
        """Initialize the distribution.

        Args:
            files (dict):
                A dictionary of resource filenames to Unicode contents.
        """
        self._files = files

    def read_text(
        self,
        filename: str,
    ) -> Optional[str]:
        """Return text for a file.

        Args:
            filename (str):
                The resource filename.

        Returns:
            str:
            The text content, or ``None`` if the file could not be found.
        """
        try:
            return self._files[filename]
        except KeyError:
            return None

    def locate_file(
        self,
        path: Union[str, os.PathLike],
    ) -> Path:
        """Return the path to a resource file.

        This returns the path as-is, wrapped in a :py:class:`pathlib.Path`.

        Args:
            path (str):
                The resource path.

        Returns:
            pathlib.Path:
            The wrapped path.
        """
        return Path(path)


class _FakeEntryPoint:
    """A fake entry point.

    This is modelled after :py:class:`importlib.metadata.EntryPoint`.

    Version Added:
        2.3
    """

    def __init__(
        self,
        value,
        project_name: str = 'ExampleProject',
        version: str = '1.0',
        *,
        author: str = 'Example Author',
        author_email: str = 'author@example.com',
        description: str = 'Test description\u2049',
        home_page: str = 'http://example.com',
        license_name: str = 'Drivers',
        summary: str = 'Test summary',
        **metadata_kwargs,
    ) -> None:
        """Initialize the FakeEntryPoint.

        Version Changed:
            3.3:
            Added argument and default values for ``author``, ``author_email``,
            ``description``, ``home_page``, ``license_name``, ``summary``,
            and ``version``. These are preferred over older Python package
            metadata names.

        Args:
            value (object):
                The value to be returned when the entry point is loaded.

            project_name (str, optional):
                The project name. This will be set in the metadata and as
-               the distribution's name.

                Version Changed:
                    3.3:
                    This now has a default value.

            version (str, optional):
                The value for the ``Version`` metadata field.

                Version Added:
                    3.3

            author (str, optional):
                The value for the ``Author`` metadata field.

                Version Added:
                    3.3

            author_email (str, optional):
                The value for the ``Author-email`` metadata field.

                Version Added:
                    3.3

            description (str, optional):
                The value for the ``Description`` metadata field.

                Version Added:
                    3.3

            home_page (str, optional):
                The value for the ``Home-page`` metadata field.

                Version Added:
                    3.3

            license_name (str, optional):
                The value for the ``License`` metadata field.

                Version Added:
                    3.3

            summary (str, optional):
                The value for the ``Summary`` metadata field.

                Version Added:
                    3.3
        """
        metadata = {
            'Author': author,
            'Author-email': author_email,
            'Description': description,
            'Home-page': home_page,
            'License': license_name,
            'Name': project_name,
            'Summary': summary,
            'Version': version,
        }
        metadata.update(metadata_kwargs)

        self._value = value
        self.dist = _FakeDistribution(files={
            'METADATA': ''.join(
                f'{key}: {value}\n'
                for key, value in metadata.items()
            )
        })

    def load(self):
        """Load the entry point.

        Returns:
            object: The value specified at initialization time.
        """
        return self._value


class DefaultTestsExtensionManager(ExtensionManager):
    """Default extension manager for unit tests.

    Version Added:
        2.3
    """


class ExtensionTestCaseMixin(object):
    """Unit tests mixin for more easily testing extensions.

    This will do the hard work of creating the fake registration information
    needed for an extension and to instantiate an instance for testing.

    Subclasses need to define :py:attr:`extension_class` and may want to
    implement :py:meth:`get_extension_manager` (by default, the first
    registered extension manager will be used).

    Projects may want to provide their own subclass for their extensions to use
    that implements :py:meth:`get_extension_manager`, so extensions won't have
    to.

    Version Changed:
        2.3:
        Extensions and extension managers are now cleaned up and removed after
        test runs.

        Subclasses can more easily set up default extension state, or create
        new extensions as needed.

    Attributes:
        extension_mgr (djblets.extensions.manager.ExtensionManager):
            The extension manager owning the extension. Tests can use this to
            manually enable/disable the extension, if needed.

        extension (djblets.extensions.extension.Extension):
            The extension instance being tested.
    """

    #: The extension class to test.
    extension_class = None

    #: Optional metadata to use for the extension information.
    extension_metadata = {
        'Version': '1.0',
    }

    #: Optional package name to use for the extension information.
    extension_package_name = 'TestPackage'

    #: Whether to enable the extension by default.
    #:
    #: Version Added:
    #:     2.3
    #:
    #: Type:
    #:     bool
    extension_enable_by_default = True

    #: The default extension manager to use if one is not instantiated.
    #:
    #: This will be created only if the consuming project hasn't already
    #: instantiated an extension manager.
    #:
    #: Version Added:
    #:     2.3
    #:
    #: Type:
    #:     type
    default_extension_manager_cls = DefaultTestsExtensionManager

    #: Whether to allow use of an existing registered extension manager.
    #:
    #: If disabled, a new extension manager will be created for the test run.
    #: This is enabled by default for backwards-compatibility.
    #:
    #: Version Added:
    #:     2.3
    #:
    #: Type:
    #:     bool
    allow_existing_extension_manager = True

    def setUp(self):
        super(ExtensionTestCaseMixin, self).setUp()

        self.extension_mgr = self.get_extension_manager()

        self._extension_classes = []
        self._extension_instances = []
        self._extensions = []
        self._orig_extension_managers = set(get_extension_managers())

        if self.extension_class is not None:
            self.extension = self.setup_extension(
                extension_cls=self.extension_class,
                package_name=self.extension_package_name,
                metadata=self.extension_metadata,
                enable=self.extension_enable_by_default)
        else:
            self.extension = None

    def tearDown(self):
        super(ExtensionTestCaseMixin, self).tearDown()

        self.reset_extensions()

    def reset_extensions(self):
        """Unregister and clean up all extensions and extension managers.

        This will disable and unregister any extensions that have been set
        up using :py:meth:`setup_extension`. It will also shut down and
        unregister all extension managers created during the test run.

        This is normally called when a unit test has finished. Tests can
        explicitly call this to reset the extension management state.

        Version Added:
            2.3
        """
        for extension_ref in self._extension_instances:
            extension = extension_ref()

            if extension is not None and getattr(extension, 'info', None):
                extension_mgr = extension.extension_manager

                if extension.info.enabled:
                    # Manually shut down the extension first, before we have
                    # the extension manager disable it. This will help ensure
                    # we have the right state up-front.
                    extension.shutdown()

                extension_mgr.disable_extension(extension.id)

        # If the unit test created any new extension managers, remove them now.
        new_extension_mgrs = (
            (set(get_extension_managers()) - self._orig_extension_managers) |
            {self.extension_mgr})

        for extension_mgr in new_extension_mgrs:
            extension_mgr.clear_sync_cache()
            extension_mgr.shutdown()

            for extension_cls_ref in self._extension_classes:
                extension_cls = extension_cls_ref()

                if (extension_cls is not None and
                    extension_cls.id in extension_mgr._extension_classes):
                    del extension_mgr._extension_classes.pop[extension_cls.id]
                    del self._extension_classes[extension_cls.id]
                    break

            _extension_managers.pop(id(extension_mgr), None)

        self._extension_classes = []
        self._extension_instances = []
        self._extensions = []
        self._orig_extension_managers = set(get_extension_managers())
        self.extension_mgr = None
        self.extension = None

    @contextmanager
    def scanned_extensions(self, extension_classes=[], extension_mgr=None):
        """Make the specified extension classes available for scanning.

        This should be called before calling :py:meth:`ExtensionManager.load()
        <djblets.extensions.manager.ExtensionManager.load>` in order to ensure
        the specified list of extension classes are available to be scanned.

        Version Added:
            2.3

        Args:
            extension_classes (list, optional):
                The list of extensions to be made available.

                Each entry can be an extension class, or a tuple of
                ``(extension_class, package_name)``.

                If any extension is not registered, it will be assigned
                a default package name of :py:attr:`extension_package_name`.

            extension_mgr (djblets.extensions.manager.ExtensionManager,
                           optional):
                An explicit extension manager that will be used to scan,
                rather than the test suite's :py:attr:`extension_mgr`
                attribute.

        Context:
            The provided extensions will be available for scanning.
        """
        assert hasattr(self, 'spy_on'), (
            '%r must inherit from kgb.SpyAgency.' % type(self))

        if extension_mgr is None:
            extension_mgr = self.extension_mgr

        assert extension_mgr is not None

        def _entrypoint_iterator(_self):
            results = []

            for entry in extension_classes:
                if isinstance(entry, tuple):
                    extension_cls, package_name = entry
                else:
                    extension_cls = entry
                    info = getattr(extension_cls, 'info', None)

                    if info is not None:
                        package_name = info.package_name
                    else:
                        package_name = self.extension_package_name

                results.append(_FakeEntryPoint(extension_cls,
                                               project_name=package_name))

            return results

        spy = self.spy_on(extension_mgr._entrypoint_iterator,
                          call_fake=_entrypoint_iterator)

        try:
            yield
        finally:
            spy.unspy()

    def setup_extension(self,
                        extension_cls=None,
                        package_name=None,
                        metadata=None,
                        enable=True,
                        extension_mgr=None):
        """Set up a new extension instance.

        This will construct an new extension of the provided type with the
        provided information.

        The extension will be registered in the extension manager, and cleaned
        up when the unit test has finished.

        Version Added:
            2.3

        Args:
            extension_cls (type, optional):
                The extension's class.

                Defaults to :py:attr:`extension_class`.

            package_name (unicode, optional):
                The package name assigned as the owner of the extension.

                Defaults to :py:attr:`extension_package_name`.

            metadata (dict, optional):
                The extension package metadata.

                Defaults to :py:attr:`metadata`.

            enable (bool, optional):
                Whether to enable the extension.

                If not enabled, an instance will still be returned, but it
                won't be registered as enabled in the extension manager.

            extension_mgr (djblets.extensions.manager.ExtensionManager,
                           optional):
                An explicit extension manager to register this extension in.

                Defaults to the result of :py:meth:`get_extension_manager`.

        Returns:
            djblets.extensions.extension.Extension:
            The extension instance, if enabling. Otherwise, ``None`` will be
            returned.
        """
        if extension_cls is None:
            extension_cls = self.extension_class

        if package_name is None:
            package_name = self.extension_package_name

        if metadata is None:
            metadata = self.extension_metadata

        if extension_cls is None:
            raise ValueError('extension_cls cannot be None.')

        if package_name is None:
            raise ValueError('package_name cannot be None.')

        if metadata is None:
            raise ValueError('metadata cannot be None.')

        if extension_cls in self._extension_classes:
            raise ValueError(
                '%r has already been registered during this test run.'
                % extension_cls)

        extension_mgr = extension_mgr or self.extension_mgr

        # We want to override all the information, even if a previous test
        # already set it. The metadata may be different, and the registration
        # definitely needs to be replaced (as it contains extension settings).
        extension_id = '%s.%s' % (extension_cls.__module__,
                                  extension_cls.__name__)

        extension_cls.id = extension_id
        extension_cls.info = ExtensionInfo(ext_class=extension_cls,
                                           package_name=package_name,
                                           metadata=metadata)

        extension_cls.registration = RegisteredExtension.objects.create(
            class_name=extension_id,
            name=extension_cls.info.name,
            enabled=True,
            installed=True)

        # We're going to manually inject the extension, instead of calling
        # load(), since it might not be found otherwise.
        extension_mgr._extension_classes[extension_id] = extension_cls
        self._extension_classes.append(weakref.ref(extension_cls))

        if enable:
            extension = extension_mgr.enable_extension(extension_id)
            assert extension is not None

            self._extension_instances.append(weakref.ref(extension))
        else:
            extension = None

        return extension

    def get_extension_manager(self):
        """Return the extension manager used for the tests.

        Subclasses may want to override this to pick a specific extension
        manager, if the project uses more than one. The default behavior is
        to return the first registered extension manager, or create one if
        one is not available.

        If :py:attr:`self.allow_existing_extension_manager` is ``False``, this
        will always create a new extension manager.

        Version Changed:
            2.3:
            This is now guaranteed to return an extension manager instance,
            and that instance is guaranteed to be cleaned up after the test
            has finished.

        Returns:
            djblets.extensions.manager.ExtensionManager:
            The extension manager used for tests.
        """
        extension_manager = None

        if self.allow_existing_extension_manager:
            try:
                extension_manager = get_extension_managers()[0]
            except IndexError:
                pass

        if extension_manager is None:
            extension_manager = self.default_extension_manager_cls(
                key='tests-%s' % uuid.uuid4())

        return extension_manager
