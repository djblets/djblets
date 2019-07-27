"""Base support for djblets.extensions unit tests."""

from __future__ import unicode_literals

import pkg_resources
from django.utils import six

from djblets.extensions.manager import ExtensionManager


class FakeEntryPoint(object):
    """A fake entry point.

    This is modelled after :py:class:`pkg_resources.EntryPoint`.
    """

    def __init__(self, value, project_name, version='1.0', **metadata_kwargs):
        """Initialize the FakeEntryPoint.

        Args:
            value (object):
                The value to be returned when the entry point is loaded.

            project_name (unicode):
                The project name. This will be set in the metadata and as
                the distribution's name.

            **metadata_kwargs (dict):
                Keyword arguments to pass to the associated
                :py:class:`FakeProvider` constructor.
        """
        self._value = value
        self.dist = pkg_resources.Distribution(
            project_name=project_name,
            version=version,
            metadata=FakeProvider(project_name=project_name,
                                  version=version,
                                  **metadata_kwargs))

    def load(self):
        """Load the entry point.

        Returns:
            object: The value specified at initialization time.
        """
        return self._value


class FakeProvider(pkg_resources.DefaultProvider):
    """A fake provider for a distribution."""

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
            for field_name, value in six.iteritems(self.metadata)
        ).encode('utf-8')


class TestExtensionManager(ExtensionManager):
    """An extension manager for testing.

    The entry points are provided at initialization time.
    """

    def __init__(self, entry_points=None, *args, **kwargs):
        """Initialize the TestExtensionManager.

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
        super(TestExtensionManager, self).__init__(*args, **kwargs)
        self._entry_points = entry_points or []

    def _entrypoint_iterator(self):
        """Return the entry points.

        Returns:
            list: The entry points.
        """
        return self._entry_points


class ExtensionTestsMixin(object):
    """Mixin for Djblets extension-related unit tests.

    This is used to help set up an extension and extension manager to test
    with.

    This shouldn't generally be used by third-parties writing unit tests for
    their extensions. For those, see
    :py:mod:`djblets.extensions.testing.testcases`.
    """

    #: The project name to use in the entrypoint.
    test_project_name = 'TestProject'

    def setUp(self):
        """Set up state before a test run."""
        super(ExtensionTestsMixin, self).setUp()

        self.manager = None

    def tearDown(self):
        """Tear down state after a test run.

        This will properly ensure that the extension manager, if one was
        created, will clear all state and shut down.
        """
        super(ExtensionTestsMixin, self).tearDown()

        if self.manager:
            self.manager.clear_sync_cache()
            self.manager.shutdown()

    def setup_extension(self, extension_cls, enable=True, manager_key='tests'):
        """Set up an extension for use in a test.

        This will register the class in a new extension manager and then
        enable or otherwise instantiate the extension, returning the instance.

        Args:
            extension_cls (type):
                The extension class to register.

            enable (bool, optional):
                Whether the returned extension should be enabled.

            manager_key (unicode, optional):
                The key to use for the extension manager.

        Returns:
            djblets.extensions.extension.Extension:
            The resulting extension instance.
        """
        fake_entry_point = FakeEntryPoint(extension_cls,
                                          project_name=self.test_project_name)

        self.manager = TestExtensionManager([fake_entry_point], manager_key)
        self.manager.load()

        if enable:
            return self.manager.enable_extension(extension_cls.id)
        else:
            return extension_cls(self.manager)
