"""Mixins for test cases that need to test enabled extensions."""

from __future__ import unicode_literals

from djblets.extensions.extension import ExtensionInfo
from djblets.extensions.manager import get_extension_managers
from djblets.extensions.models import RegisteredExtension


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
    extension_metadata = {}

    #: Optional package name to use for the extension information.
    extension_package_name = 'TestPackage'

    def setUp(self):
        super(ExtensionTestCaseMixin, self).setUp()

        self.extension_mgr = self.get_extension_manager()

        # We want to override all the information, even if a previous test
        # already set it. The metadata may be different, and the registration
        # definitely needs to be replaced (as it contains extension settings).
        extension_id = '%s.%s' % (self.extension_class.__module__,
                                  self.extension_class.__name__)

        self.extension_class.id = extension_id
        self.extension_class.info = ExtensionInfo(
            ext_class=self.extension_class,
            package_name=self.extension_package_name,
            metadata=self.extension_metadata)

        self.extension_class.registration = RegisteredExtension.objects.create(
            class_name=extension_id,
            name=self.extension_class.info.name,
            enabled=True,
            installed=True)

        # We're going to manually inject the extension, instead of calling
        # load(), since it might not be found otherwise.
        self.extension_mgr._extension_classes[extension_id] = \
            self.extension_class

        self.extension = self.extension_mgr.enable_extension(extension_id)
        assert self.extension

    def tearDown(self):
        super(ExtensionTestCaseMixin, self).tearDown()

        if self.extension.info.enabled:
            # Manually shut down the extension first, before we have the
            # extension manager disable it. This will help ensure we have the
            # right state up-front.
            self.extension.shutdown()

            self.extension_mgr.disable_extension(self.extension_class.id)

    def get_extension_manager(self):
        """Return the extension manager used for the tests.

        Subclasses may want to override this to pick a specific extension
        manager, if the project uses more than one. The default behavior is
        to return the first registered extension manager.

        Returns:
            djblets.extensions.manager.ExtensionManager:
            The extension manager used for tests.
        """
        return get_extension_managers()[0]
