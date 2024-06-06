"""Extension manager class for supporting extensions to an application."""

from __future__ import annotations

import atexit
import errno
import logging
import os
import shutil
import sys
import tempfile
import threading
import time
import traceback
import warnings
from contextlib import contextmanager
from importlib import import_module, reload
from typing import (Any, Dict, Iterator, List, Optional, Set, TYPE_CHECKING,
                    Type, Union)
from weakref import WeakValueDictionary

import importlib_metadata
from django.apps.registry import apps
from django.conf import LazySettings, settings
from django.contrib.admin.sites import AdminSite
from django.core.files import locks
from django.db import IntegrityError
from django.urls import include, path, reverse
from django.utils.module_loading import module_has_submodule
from django.utils.translation import gettext as _
from packaging.version import InvalidVersion, Version, parse as parse_version
from pipeline.conf import settings as pipeline_settings

try:
    from django_evolution.evolve import Evolver
except ImportError:
    Evolver = None

from djblets.cache.synchronizer import GenerationSynchronizer
from djblets.extensions.errors import (EnablingExtensionError,
                                       InstallExtensionError,
                                       InstallExtensionMediaError,
                                       InvalidExtensionError)
from djblets.extensions.extension import Extension, ExtensionInfo
from djblets.extensions.models import RegisteredExtension
from djblets.extensions.signals import (extension_disabled,
                                        extension_enabled,
                                        extension_initialized,
                                        extension_uninitialized)
from djblets.template.caches import (clear_template_caches,
                                     clear_template_tag_caches)
from djblets.urls.resolvers import DynamicURLResolver

if TYPE_CHECKING:
    from djblets.extensions.extension import CSSBundleConfigs, JSBundleConfigs


logger = logging.getLogger(__name__)

_extension_managers: WeakValueDictionary[int, ExtensionManager] = \
    WeakValueDictionary()


class SettingListWrapper:
    """Wraps list-based settings to provide management and ref counting.

    This can be used instead of direct access to a list in Django
    settings to ensure items are never added more than once, and only
    removed when nothing needs it anymore.

    Each item in the list is ref-counted. The initial items from the
    setting are populated and start with a ref count of 1. Adding items
    will increment a ref count for the item, adding it to the list
    if it doesn't already exist. Removing items reduces the ref count,
    removing when it hits 0.
    """

    def __init__(
        self,
        setting_name: str,
        display_name: str,
        parent_dict: Union[Optional[Dict[str, Any]], LazySettings] = None,
    ) -> None:
        """Initialize the settings wrapper.

        Args:
            setting_name (str):
                The name of the setting. This is the key in either
                ``parent_dict`` or ``settings``.

            display_name (str):
                The display name of the setting, for use in error output.

            parent_dict (dict, optional):
                The dictionary containing the setting. If not set, this
                will fall back to ``settings``.
        """
        self.setting_name = setting_name
        self.display_name = display_name
        self.ref_counts = {}

        parent_dict = parent_dict or settings

        if isinstance(parent_dict, dict):
            self.setting = parent_dict[setting_name]
        else:
            self.setting = getattr(parent_dict, setting_name)

        if isinstance(self.setting, tuple):
            self.setting = list(self.setting)

            if isinstance(parent_dict, dict):
                parent_dict[setting_name] = self.setting
            else:
                setattr(parent_dict, setting_name, self.setting)

        for item in self.setting:
            self.ref_counts[item] = 1

    def add(
        self,
        item: Any,
    ) -> None:
        """Add an item to the setting.

        If the item is already in the list, it won't be added again.
        The ref count will just be incremented.

        If it's a new item, it will be added to the list with a ref count
        of 1.

        Args:
            item (object):
                The item to add.
        """
        if item in self.ref_counts:
            self.ref_counts[item] += 1
        else:
            assert item not in self.setting, \
                ("Extension's %s %s is already in %s in settings, with "
                 "ref count of 0."
                 % (self.display_name, item, self.setting_name))

            self.ref_counts[item] = 1
            self.setting.append(item)

    def add_list(
        self,
        items: List[Any],
    ) -> None:
        """Add a list of items to the setting.

        Args:
            item (list of object):
                The list of items to add.
        """
        for item in items:
            self.add(item)

    def remove(
        self,
        item: Any,
    ) -> bool:
        """Remove an item from the setting.

        The item's ref count will be decremented. If it hits 0, it will
        be removed from the list.

        Args:
            item (object):
                The item to remove.

        Returns:
            bool:
            ``True`` if the item was removed from the list. ``False`` if it
            was left in due to still having a reference.
        """
        assert item in self.ref_counts, \
            ("Extension's %s %s is missing a ref count."
             % (self.display_name, item))
        assert item in self.setting, \
            ("Extension's %s %s is not in %s in settings"
             % (self.display_name, item, self.setting_name))

        if self.ref_counts[item] == 1:
            # This is the very last reference to this item in the list. We
            # can now safely remove it from the list and inform the caller.
            del self.ref_counts[item]
            self.setting.remove(item)

            return True
        else:
            # There's still more references to this item in the list. We can't
            # remove it yet.
            self.ref_counts[item] -= 1

            return False

    def remove_list(
        self,
        items: List[Any],
    ) -> List[Any]:
        """Remove a list of items from the setting.

        Args:
            items (list of object):
                The list of items to remove.

        Returns:
            list of object:
            The list of items that were removed (or that did not exist in
            the list).
        """
        removed_items = []

        for item in items:
            try:
                removed = self.remove(item)
            except ValueError:
                # This may have already been removed. Ignore the error.
                removed = True

            if removed:
                removed_items.append(item)

        return removed_items


class ExtensionManager:
    """A manager for all extensions.

    ExtensionManager manages the extensions available to a project. It can
    scan for new extensions, enable or disable them, determine dependencies,
    install into the database, and uninstall.

    An installed extension is one that has been installed by a Python package
    on the system.

    A registered extension is one that has been installed and information then
    placed in the database. This happens automatically after scanning for
    an installed extension. The registration data stores whether or not it's
    enabled, and stores various pieces of information on the extension.

    An enabled extension is one that is actively enabled and hooked into the
    project.

    Each project should have one ExtensionManager.

    Projects can set ``settings.EXTENSIONS_ENABLED_BY_DEFAULT`` to a list of
    extension IDs (class names) that should be automatically enabled when their
    registrations are first created. This will ensure that those extensions
    will default to being enabled. If an administrator later disables the
    extension, it won't automatically re-renable unless the registration is
    removed.
    """

    #: Whether to explicitly install static media files from packages.
    #:
    #: By default, we install static media files if
    #: :django:setting:`PRODUCTION` is ``True``. Subclasses can override this
    #: to factor in other settings, if needed.
    should_install_static_media = getattr(settings, 'PRODUCTION',
                                          not settings.DEBUG)

    #: The key in the settings indicating the last known configured version.
    #:
    #: This setting is used to differentiate the version of an extension
    #: installed locally on a system and the last version that completed
    #: database-related installation/upgrade steps.
    #:
    #: This should not be changed by subclasses, and generally is not needed
    #: outside of this class.
    VERSION_SETTINGS_KEY = '_extension_installed_version'

    _MEDIA_LOCK_SLEEP_TIME_SECS = 1

    ######################
    # Instance variables #
    ######################

    #: Extension middleware class names, ordered by dependencies.
    #:
    #: Type:
    #:     list of str
    middleware_classes: List[str]

    #: A mapping of extension ID to extension classes.
    _extension_classes: Dict[str, Type[Extension]]

    #: A mapping of extension ID to extension class instances.
    _extension_instances: Dict[str, Extension]

    #: The URL to the extension list.
    _extension_list_url: Optional[str]

    #: A mapping of extension ID to error message.
    _load_errors: Dict[str, str]

    def __init__(
        self,
        key: str,
    ) -> None:
        """Initialize the extension manager.

        Args:
            key (str):
                A key that's unique to this extension manager instance. It
                must also be the same key used to look up Python entry points.
        """
        self.key = key

        self._extension_classes = {}
        self._extension_instances = {}
        self._load_errors = {}

        # State synchronization
        self._gen_sync = GenerationSynchronizer('extensionmgr:%s:gen' % key)
        self._load_lock = threading.Lock()
        self._shutdown_lock = threading.Lock()
        self._block_sync_gen = False

        self.dynamic_urls = DynamicURLResolver()
        self._extension_list_url = None

        self.middleware_classes = []

        # Wrap the INSTALLED_APPS and TEMPLATE_CONTEXT_PROCESSORS settings
        # to allow for ref-counted add/remove operations.
        self._installed_apps_setting = SettingListWrapper('INSTALLED_APPS',
                                                          'installed app')

        self._context_processors_setting = SettingListWrapper(
            'context_processors',
            'context processor',
            parent_dict=settings.TEMPLATES[0]['OPTIONS'])

        instance_id = id(self)
        _extension_managers[instance_id] = self

    def get_url_patterns(self) -> List[DynamicURLResolver]:
        """Return the URL patterns for the Extension Manager.

        This should be included in the root urlpatterns for the site.

        Returns:
            list:
            The list of URL patterns for the Extension Manager.
        """
        return [self.dynamic_urls]

    def is_expired(self) -> bool:
        """Returns whether or not the extension state is possibly expired.

        Extension state covers the lists of extensions and each extension's
        configuration. It can expire if the state synchronization value
        falls out of cache or is changed.

        Each ExtensionManager has its own state synchronization cache key.

        Returns:
            bool:
            Whether the state has expired.
        """
        return self._gen_sync.is_expired()

    def clear_sync_cache(self) -> None:
        """Clear the extension synchronization state.

        This will force every process to reload the extension list and
        settings.
        """
        self._gen_sync.clear()

    def get_absolute_url(self) -> str:
        """Return an absolute URL to the view for listing extensions.

        By default, this simply looks up the "extension-list" URL.

        Subclasses can override this to provide a more specific URL, but should
        take care to cache the result in order to avoid unwanted lookups caused
        by URL resolver cache flushes.

        Returns:
            str:
            The URL to the extension list view.
        """
        if not self._extension_list_url:
            self._extension_list_url = reverse('extension-list')

        assert self._extension_list_url is not None

        return self._extension_list_url

    def get_can_disable_extension(
        self,
        registered_extension: RegisteredExtension,
    ) -> bool:
        """Return whether an extension can be disabled.

        Extensions can only be disabled if already enabled or there's a load
        error.

        Args:
            registered_extension (djblets.extensions.models.
                                  RegisteredExtension):
                The registered extension entry representing the extension.

        Returns:
            bool:
            ``True`` if the extension can be disabled. ``False`` if it cannot.
        """
        extension_id = registered_extension.class_name

        return (registered_extension.extension_class is not None and
                (self.get_enabled_extension(extension_id) is not None or
                 extension_id in self._load_errors))

    def get_can_enable_extension(
        self,
        registered_extension: RegisteredExtension,
    ) -> bool:
        """Return whether an extension can be enabled.

        Extensions can only be enabled if already disabled.

        Args:
            registered_extension (djblets.extensions.models.
                                  RegisteredExtension):
                The registered extension entry representing the extension.

        Returns:
            bool:
            ``True`` if the extension can be enabled. ``False`` if it cannot.
        """
        return (
            registered_extension.extension_class is not None and
            self.get_enabled_extension(registered_extension.class_name) is None
        )

    def get_enabled_extension(
        self,
        extension_id: str,
    ) -> Optional[Extension]:
        """Return an enabled extension for the given exetnsion ID.

        Args:
            extension_id (str):
                The ID of the extension.

        Returns:
            djblets.extensions.extension.Extension:
            The extension matching the given ID, if enabled. If disabled or
            not found, ``None`` will be returned.
        """
        return self._extension_instances.get(extension_id)

    def get_enabled_extensions(self) -> List[Extension]:
        """Return a list of all enabled extensions.

        Returns:
            list of djblets.extensions.extension.Extension:
            All extension instances currently enabled.
        """
        return list(self._extension_instances.values())

    def get_installed_extensions(self) -> List[Type[Extension]]:
        """Return a list of all installed extension classes.

        Returns:
            list of type:
            All extension classes currently registered.
        """
        return list(self._extension_classes.values())

    def get_installed_extension(
        self,
        extension_id: str,
    ) -> Type[Extension]:
        """Return the installed extension class with the given extension ID.

        The extension class must be available on the system and must be
        importable.

        Args:
            extension_id (str):
                The ID of the extension.

        Returns:
            type:
            The extension class matching the ID.

        Raises:
            djblets.extensions.errors.InvalidExtensionError:
                The extension could not be found.
        """
        try:
            return self._extension_classes[extension_id]
        except KeyError:
            raise InvalidExtensionError(extension_id)

    def get_dependent_extensions(
        self,
        dependency_extension_id: str,
    ) -> List[str]:
        """Return a list of all extension IDs required by an extension.

        Args:
            dependency_extension_id (str):
                The ID of the extension to retrieve dependencies for.

        Returns:
            list of str:
            The list of extension IDs required by this extension.

        Raises:
            djblets.extensions.errors.InvalidExtensionError:
                The extension could not be found.
        """
        # This will raise InvalidExtensionError if not found.
        dependency = self.get_installed_extension(dependency_extension_id)
        extension_classes = self._extension_classes.items()

        return [
            extension_id
            for extension_id, extension in extension_classes
            if (extension_id != dependency_extension_id and
                dependency in extension.info.requirements)
        ]

    def enable_extension(
        self,
        extension_id: str,
    ) -> Optional[Extension]:
        """Enable an extension.

        Enabling an extension will install any data files the extension
        may need, any tables in the database, perform any necessary
        database migrations, and then will start up the extension.

        If the extension is already enabled, this will do nothing.

        After enabling the extension, the
        :py:data:`djblets.extensions.signals.extension_enabled` signal will be
        emitted.

        Args:
            extension_id (str):
                The ID of the extension to enable.

        Returns:
            djblets.extensions.extension.Extension:
            The extension instance.

        Raises:
            djblets.extensions.errors.EnablingExtensionError:
                There was an error enabling an extension. The error
                information will be provided.

            djblets.extensions.errors.InvalidExtensionError:
                The extension could not be found.
        """
        if extension_id in self._extension_instances:
            # It's already enabled.
            return None

        try:
            ext_class = self._extension_classes[extension_id]
        except KeyError:
            if extension_id in self._load_errors:
                raise EnablingExtensionError(
                    _('There was an error loading this extension'),
                    self._load_errors[extension_id],
                    needs_reload=True)

            raise InvalidExtensionError(extension_id)

        # Enable the extension's dependencies.
        for requirement_id in ext_class.requirements:
            self.enable_extension(requirement_id)

        extension = self._init_extension(ext_class)

        # Mark this extension as enabled for future threads/processes.
        ext_class.registration.enabled = True
        ext_class.registration.save()

        # Begin updating the settings and synchronization information so that
        # this process and others will update to use the extension's features.
        clear_template_caches()
        self._bump_sync_gen()
        self._recalculate_middleware()

        extension_enabled.send_robust(sender=self, extension=extension)

        return extension

    def disable_extension(
        self,
        extension_id: str,
    ) -> None:
        """Disable an extension.

        Disabling an extension will remove any data files the extension
        installed and then shut down the extension and all of its hooks.

        It will not delete any data from the database.

        After disabling the extension, the
        :py:data:`djblets.extensions.signals.extension_disabled` signal will be
        emitted.

        Args:
            extension_id (str):
                The ID of the extension to disable.

        Raises:
            djblets.extensions.errors.InvalidExtensionError:
                The extension could not be found.
        """
        has_load_error = extension_id in self._load_errors

        if not has_load_error:
            if extension_id not in self._extension_instances:
                # It's not enabled.
                return

            try:
                extension = self._extension_instances[extension_id]
            except KeyError:
                raise InvalidExtensionError(extension_id)

            # Disable each of the extensions depended on by this extension.
            for dependent_id in self.get_dependent_extensions(extension_id):
                self.disable_extension(dependent_id)

            self._uninstall_extension(extension)
            self._uninit_extension(extension)
            self._unregister_static_bundles(extension)

            registration = extension.registration
        else:
            extension = None
            del self._load_errors[extension_id]

            if extension_id in self._extension_classes:
                # The class was loadable, so it just couldn't be instantiated.
                # Update the registration on the class.
                ext_class = self._extension_classes[extension_id]
                registration = ext_class.registration
            else:
                registration = RegisteredExtension.objects.get(
                    class_name=extension_id)

        registration.enabled = False
        registration.save(update_fields=['enabled'])

        clear_template_caches()
        self._bump_sync_gen()
        self._recalculate_middleware()

        if extension is not None:
            extension_disabled.send_robust(sender=self,
                                           extension=extension)

    def install_extension(
        self,
        install_url: str,
        package_name: str,
    ) -> None:
        """Install an extension from a remote source.

        This will attempt to install or upgrade an extension package using
        :command:`easy_install`.

        Deprecated:
            3.3:
            This support has been removed. It's never worked quite right,
            didn't keep up with modern Python Wheel packages, and was
            previously documented as not being fully-supported.

        Args:
            install_url (str):
                The URL of the package to install.

            package_name (str):
                The name of the package being installed.

        Raises:
            djblets.extensions.errors.InstallExtensionError:
                Always raised to indicate support is unavailable.
        """
        # This did not go through a deprecation cycle, but the implementation
        # is too risky to keep around in the current form. This was never
        # fully supported.
        raise InstallExtensionError(
            'install_extension() has not fully worked in a long time, and '
            'does not work in modern environments. Support is unavailable.')

    def load(
        self,
        full_reload: bool = False,
    ) -> None:
        """Load information on all extensions on the system.

        This will begin looking up all extensions on the system, adding
        registration entries and enabling any that were previously enabled.

        Calling this a second time will refresh the list of extensions, adding
        any new ones and deleting old ones.

        This method is designed to be thread-safe. Only one load across threads
        can occur at once.

        Args:
            full_reload (bool, optional):
                If ``True``, a full reload will be performed, disabling all
                enabled extensions, clearing all state, and re-loading
                all extension data.
        """
        with self._load_lock:
            self._block_sync_gen = True
            self._load_extensions(full_reload)
            self._block_sync_gen = False

    def shutdown(self) -> None:
        """Shut down the extension manager and all of its extensions.

        This method is designed to be thread-safe. Only one shutdown across
        threads can occur at once.
        """
        with self._shutdown_lock:
            self._clear_extensions()

    def _load_extensions(
        self,
        full_reload: bool = False,
    ) -> None:
        """Load information on all extension on the system.

        This is responsible for the bulk of the work for loading extensions,
        storing registration information and enabling any extensions that need
        to be enabled. It's called by :py:meth:`load` in the thread lock and
        should not otherwise be called directly.

        Args:
            full_reload (bool, optional):
                If ``True``, a full reload will be performed, disabling all
                enabled extensions, clearing all state, and re-loading
                all extension data.
        """
        if full_reload:
            # We're reloading everything, so nuke all the cached copies.
            self._clear_extensions()
            clear_template_caches()
            self._load_errors = {}

        # Preload all the RegisteredExtension objects
        registered_extensions = {
            registered_ext.class_name: registered_ext
            for registered_ext in RegisteredExtension.objects.all()
        }

        found_extensions = {}
        found_registrations = {}
        registrations_to_fetch = []
        find_registrations = False
        extensions_changed = False

        for entrypoint in self._entrypoint_iterator():
            registered_ext = None

            try:
                ext_class = entrypoint.load()
            except Exception as e:
                logger.exception('Error loading extension %s: %s',
                                 entrypoint.name, e)
                extension_id = '%s.%s' % (entrypoint.module, entrypoint.attr)
                self._store_load_error(extension_id, e)
                continue

            # A class's extension ID is its class name. We want to
            # make this easier for users to access by giving it an 'id'
            # variable, which will be accessible both on the class and on
            # instances.
            class_name = ext_class.id = '%s.%s' % (ext_class.__module__,
                                                   ext_class.__name__)
            self._extension_classes[class_name] = ext_class
            found_extensions[class_name] = ext_class

            # Don't override the info if we've previously loaded this
            # class.
            if not getattr(ext_class, 'info', None):
                ext_class.info = ExtensionInfo.create_from_entrypoint(
                    entrypoint, ext_class)

            registered_ext = registered_extensions.get(class_name)

            if registered_ext:
                found_registrations[class_name] = registered_ext

                if not hasattr(ext_class, 'registration'):
                    find_registrations = True
            else:
                assert entrypoint.dist is not None

                registrations_to_fetch.append(
                    (class_name, entrypoint.dist.name))
                find_registrations = True

        if find_registrations:
            if registrations_to_fetch:
                stored_registrations = list(
                    RegisteredExtension.objects.filter(
                        class_name__in=registrations_to_fetch))

                # Go through the list of registrations found in the database
                # and mark them as found for later processing.
                for registered_ext in stored_registrations:
                    class_name = registered_ext.class_name
                    found_registrations[class_name] = registered_ext

            enabled_by_default = \
                set(getattr(settings, 'EXTENSIONS_ENABLED_BY_DEFAULT', []))

            # Go through each registration we still need and couldn't find,
            # and create an entry in the database. These are going to be
            # newly discovered extensions.
            for class_name, ext_name in registrations_to_fetch:
                if class_name not in found_registrations:
                    try:
                        registered_ext = RegisteredExtension.objects.create(
                            class_name=class_name,
                            enabled=class_name in enabled_by_default,
                            name=ext_name)
                    except IntegrityError:
                        # An entry was created since we last looked up
                        # anything. Fetch it from the database.
                        registered_ext = RegisteredExtension.objects.get(
                            class_name=class_name)

                    found_registrations[class_name] = registered_ext

        # Now we have all the RegisteredExtension instances. Go through
        # and initialize each of them.
        for class_name, registered_ext in found_registrations.items():
            ext_class = found_extensions[class_name]
            ext_class.registration = registered_ext

            if (ext_class.registration.enabled and
                ext_class.id not in self._extension_instances):
                try:
                    self._init_extension(ext_class)
                except EnablingExtensionError:
                    # When in developer mode, we want this error to be noticed.
                    # However, in production, it shouldn't break the whole
                    # server, so continue on.
                    if settings.PRODUCTION:
                        continue

                extensions_changed = True

        # At this point, if we're reloading, it's possible that the user
        # has removed some extensions. Go through and remove any that we
        # can no longer find.
        #
        # While we're at it, since we're at a point where we've seen all
        # extensions, we can set the ExtensionInfo.requirements for
        # each extension
        for class_name, ext_class in self._extension_classes.items():
            if class_name not in found_extensions:
                if class_name in self._extension_instances:
                    self.disable_extension(class_name)

                del self._extension_classes[class_name]
                extensions_changed = True
            else:
                ext_class.info.requirements = [
                    self.get_installed_extension(requirement_id)
                    for requirement_id in ext_class.requirements
                ]

        # Add the sync generation if it doesn't already exist.
        self._gen_sync.refresh()
        settings.AJAX_SERIAL = self._gen_sync.sync_gen

        if extensions_changed:
            self._recalculate_middleware()

    def _clear_extensions(self) -> None:
        """Clear the entire list of known extensions.

        This will bring the ExtensionManager back to the state where
        it doesn't yet know about any extensions, requiring a re-load.
        """
        for extension in self.get_enabled_extensions():
            # Make sure this is actually an enabled extension, and not one
            # that's already been shut down by another instance of this
            # ExtensionManager (which should only happen in tests):
            if hasattr(extension.__class__, 'info'):
                self._uninit_extension(extension)

        for extension_class in self.get_installed_extensions():
            if hasattr(extension_class, 'info'):
                delattr(extension_class, 'info')

            if hasattr(extension_class, 'registration'):
                delattr(extension_class, 'registration')

        self._extension_classes = {}
        self._extension_instances = {}

    def _init_extension(
        self,
        ext_class: Type[Extension],
    ) -> Extension:
        """Initialize an extension.

        This will register the extension, install any URLs that it may need,
        and make it available in Django's list of apps. It will then notify
        that the extension has been initialized.

        Args:
            ext_class (type):
                The extension's class to initialize.
        """
        extension_id = ext_class.id

        assert extension_id not in self._extension_instances

        try:
            extension = ext_class(extension_manager=self)
        except Exception as e:
            logger.exception('Unable to initialize extension %s: %s',
                             ext_class, e)
            raise EnablingExtensionError(
                _('Error initializing extension: %s') % e,
                self._store_load_error(extension_id, str(e)))

        # If this extension previously failed to load, and has a stored error,
        # clear it.
        try:
            del self._load_errors[extension_id]
        except KeyError:
            pass

        self._extension_instances[extension_id] = extension
        ext_class.instance = extension

        try:
            if extension.has_admin_site:
                try:
                    self._init_admin_site(extension)
                except Exception as e:
                    raise EnablingExtensionError(
                        _("Error setting up extension's administration "
                          "site: %s")
                        % e,
                        self._store_load_error(ext_class.id, str(e)))

            # Installing the urls must occur after _init_admin_site(). The urls
            # for the admin site will not be generated until it is called.
            try:
                self._install_admin_urls(extension)
            except Exception as e:
                raise EnablingExtensionError(
                    _('Error setting up administration URLs: %s') % e,
                    self._store_load_error(ext_class.id, str(e)))

            self._register_static_bundles(extension)

            extension.info.installed = extension.registration.installed
            extension.info.enabled = True

            new_installed_apps = self._add_to_installed_apps(extension)
            extension.info.apps_registered = True

            self._context_processors_setting.add_list(
                extension.context_processors)
            extension.info.context_processors_registered = True

            clear_template_tag_caches()

            try:
                self.install_extension_media(ext_class)
            except InstallExtensionMediaError as e:
                raise EnablingExtensionError(str(e), e.load_error)

            # Check if the version information stored along with the extension
            # is stale. If so, we may need to perform some updates.
            cur_version = ext_class.info.version
            assert cur_version is not None

            if ext_class.registration.installed:
                old_version = extension.settings.get(self.VERSION_SETTINGS_KEY)
            else:
                old_version = None

            parsed_old_version = self._parse_version(old_version)
            parsed_cur_version = self._parse_version(cur_version)

            if parsed_cur_version is None:
                logger.warning('Could not parse the version "%s" for '
                               'extension "%s". This is not a valid Python '
                               'package version. Database upgrades will not '
                               'be performed.',
                               cur_version,
                               extension_id)
            elif (parsed_old_version is None or
                  parsed_old_version < parsed_cur_version):
                # If any models are introduced by this extension, we may need
                # to update the database.
                self._sync_database(ext_class, new_installed_apps)

                # Record this version so we don't update the database again.
                extension.settings.set(self.VERSION_SETTINGS_KEY, cur_version)
                extension.settings.save()
            elif (parsed_old_version is not None and
                  parsed_old_version > parsed_cur_version):
                logger.warning(
                    'The version of the "%s" extension installed '
                    'on the server is older than the version '
                    'recorded in the database! Upgrades will not '
                    'be performed.',
                    ext_class)

            # Mark the extension as installed.
            if not ext_class.registration.installed:
                ext_class.registration.installed = True
                ext_class.registration.save(update_fields=('installed',))
        except EnablingExtensionError as e:
            self._uninit_extension(extension)

            logger.exception('Error initializing extension %s: %s',
                             ext_class.id, e)

            # Raise this as-is.
            raise
        except Exception as e:
            self._uninit_extension(extension)

            logger.exception('Unexpected error initializing extension %s: %s',
                             ext_class.id, e)

            raise EnablingExtensionError(
                _('Unexpected error initializing the extension: %s') % e,
                self._store_load_error(ext_class.id, str(e)))

        extension_initialized.send_robust(self, ext_class=extension)

        return extension

    def _sync_database(
        self,
        ext_class: Type[Extension],
        new_installed_app_names: List[str],
    ) -> None:
        """Synchronize extension-provided models to the database.

        This will create any database tables that need to be created and
        the perform a database migration, if needed.

        This requires that Django Evolution be installed. Otherwise, models
        will not be synced to the database.

        Args:
            ext_class (type):
                The extension class owning the database models.

            new_installed_app_names (list of str):
                The list of new Django app names that are installed by an
                extension.

        Raises:
            djblets.extensions.errors.InstallExtensionError:
                The extension's database entries could not be installed to
                the database or upgraded.
        """
        installed_apps = self._get_app_modules_with_models(
            new_installed_app_names)

        if not installed_apps:
            return

        if not Evolver:
            warnings.warn('Extension database models will not be synced '
                          'to the database. Django Evolution must be '
                          'installed.')
            return

        evolver = Evolver()

        for app in installed_apps:
            evolver.queue_evolve_app(app)

        if evolver.get_evolution_required():
            try:
                evolver.evolve()
            except Exception as e:
                logger.exception('Error evolving extension models for %s: %s',
                                 ext_class.id, e)

                raise InstallExtensionError(
                    str(e),
                    self._store_load_error(ext_class.id, str(e)))

    def _get_app_modules_with_models(
        self,
        app_names: List[str],
    ) -> List[str]:
        """Return app modules containing models for each app name.

        This will iterate through the list of app names for an extension and
        return the app module for each app that contains models.

        Args:
            app_names (list of str):
                The list of Django app names.

        Returns:
            list of str:
            The list of modules for each app that contains models.
        """
        results = []

        # There's no way of looking up an AppConfig based on the app
        # name, so we'll need to start by building our own map.
        all_app_configs = {
            app_config.name: app_config
            for app_config in apps.get_app_configs()
        }

        for app_name in app_names:
            app_config = all_app_configs[app_name]

            if app_config.models and app_config.models_module:
                results.append(app_config.models_module)

        return results

    def _uninit_extension(
        self,
        extension: Extension,
    ) -> None:
        """Uninitialize the extension.

        This will shut down the extension, remove any URLs, remove it from
        Django's list of apps, and send a signal saying the extension was
        shut down.

        Args:
            extension (djblets.extensions.extension.Extension):
                The extension instance to uninitialize.
        """
        try:
            extension.shutdown()
        except Exception as e:
            logger.exception('Unexpected error shutting down extension %s: %s',
                             extension.id, e)

        if getattr(extension, 'admin_urlpatterns', []):
            try:
                self.dynamic_urls.remove_patterns(extension.admin_urlpatterns)
            except Exception as e:
                logger.exception('Unexpected error removing custom admin URL '
                                 'patterns for extension %s: %s',
                                 extension.id, e)

        if getattr(extension, 'admin_site_urlpatterns', []):
            try:
                self.dynamic_urls.remove_patterns(
                    extension.admin_site_urlpatterns)
            except Exception as e:
                logger.exception('Unexpected error removing AdminSite URL '
                                 'patterns for extension %s: %s',
                                 extension.id, e)

        if hasattr(extension, 'admin_site'):
            del extension.admin_site

        if (extension.info.context_processors_registered and
            extension.context_processors):
            try:
                self._context_processors_setting.remove_list(
                    extension.context_processors)
            except Exception as e:
                logger.exception('Unexpected error unregistering context '
                                 'processors for extension %s: %s',
                                 extension.id, e)

        if extension.info.apps_registered:
            try:
                self._remove_from_installed_apps(extension)
            except Exception as e:
                logger.exception('Unexpected error removing installed app '
                                 'modules for extension %s: %s',
                                 extension.id, e)

        try:
            clear_template_tag_caches()
        except Exception as e:
            logger.exception('Unexpected error clearing template tag caches '
                             'when uninitializing extension %s: %s',
                             extension.id, e)

        extension.info.enabled = False

        extension_uninitialized.send_robust(self, ext_class=extension)

        del self._extension_instances[extension.id]
        extension.__class__.instance = None

    def _store_load_error(
        self,
        extension_id: str,
        err: str,
    ) -> str:
        """Store and return a load error for the extension ID.

        Arg:
            extension_id (str):
                The ID for the exetnsion.

            err (str):
                The error string.

        Returns:
            str:
            A detailed error message indicating a load failure. This will
            contain the provided error message and a traceback.
        """
        error_details = '%s\n\n%s' % (err, traceback.format_exc())
        self._load_errors[extension_id] = error_details

        return error_details

    def install_extension_media(
        self,
        ext_class: Type[Extension],
        force: bool = False,
        max_lock_attempts: int = 10,
    ) -> None:
        """Install extension static media.

        This will check whether we actually need to install extension media,
        based on the presence and version of the locally-stored extension
        media. If media needs to be installed, this will pull it out of the
        extension package and place it in the appropriate static media
        location.

        This is thread-safe. If multiple threads are attempting to install
        extension media at the same time, only one will actually perform the
        install and the rest will make use of that new media.

        Args:
            ext_class (type):
                The extension class owning the static media to install.

            force (bool, optional):
                Whether to force installation of static media, regardless of
                the media version.

            max_lock_attempts (int, optional):
                Maximum number of attempts to try to claim a lock in order
                to install media files.

        Raises:
            djblets.extensions.errors.InstallExtensionMediaError:
                There was an error installing extension media. Details are in
                the error message.
        """
        # If we're not installing static media, it's assumed that media will
        # be looked up using the static media finders instead. In that case,
        # media will be served directly out of the extension's static/
        # directory. We won't want to be storing version files there.
        if not self.should_install_static_media:
            return

        cur_version = ext_class.info.version

        # We only want to fetch the existing version information if the
        # extension is already installed. We remove this key when
        # disabling an extension, so if it were there, it was either
        # copy/pasted, or something went wrong. Either way, we wouldn't
        # be able to trust it.
        if force:
            logger.debug('Forcing installation of extension media for %s',
                         ext_class.info)
            old_version = None
        else:
            if ext_class.registration.installed:
                # There may be a static media version stamp we can fetch from
                # this site. This also might be ``None``, if the file does not
                # exist.
                old_version = ext_class.info.get_installed_static_version()
            else:
                # This is either a new install, or an older one from before the
                # media version stamp files.
                old_version = None

            if old_version == cur_version:
                # Nothing to do
                return

            if old_version:
                logger.debug('Upgrading/re-installing extension media for '
                             '%s from version %s to %s',
                             ext_class.info, old_version, cur_version)
            else:
                logger.debug('Installing extension media for %s',
                             ext_class.info)

        if old_version == cur_version:
            # Nothing to do. The media is up-to-date.
            return

        lockfile = '%s.lock' % ext_class.id
        attempt = 0

        while old_version != cur_version and attempt < max_lock_attempts:
            try:
                with self._open_lock_file(ext_class, lockfile):
                    # These will raise exceptions if there's a fatal error,
                    # such as permission issues with the destination directory
                    # for static media files and the version file.
                    self._install_extension_media_internal(ext_class)
                    ext_class.info.write_installed_static_version()

                    old_version = cur_version
            except IOError as e:
                # There was an error writing or locking the lock file.
                # Depending on the error, we may want to try again.
                if e.errno not in (errno.EACCES, errno.EAGAIN, errno.EINTR):
                    raise InstallExtensionMediaError(
                        _('Unexpected error installing extension media files '
                          'for this extension. A lock file could not be '
                          'established: %s')
                        % e)

                # See if the version has changed at all. If so, we'll be able
                # to break the loop. Otherwise, we're going to try for the
                # lock again.
                temp_version = ext_class.info.get_installed_static_version()

                if temp_version != cur_version:
                    if temp_version is not None:
                        cur_version = temp_version

                    # Sleep for one second before we try again.
                    attempt += 1

                    if attempt < max_lock_attempts:
                        time.sleep(self._MEDIA_LOCK_SLEEP_TIME_SECS)

        if old_version != cur_version:
            # We never succeeded. We probably hit the maximum number of
            # attempts.
            raise InstallExtensionMediaError(
                _('Unable to install static media files for this extension. '
                  'There have been %(attempts)d attempts to install the '
                  'media files. Please make sure that "%(static_path)s", its '
                  'contents, its parent directory, and "%(temp_path)s" are '
                  'writable by the web server.')
                % {
                    'attempts': attempt,
                    'static_path': ext_class.info.installed_static_path,
                    'temp_path': tempfile.gettempdir(),
                })

    def _install_extension_media_internal(
        self,
        ext_class: Type[Extension],
    ) -> None:
        """Install static media for an extension.

        This performs any installation necessary for an extension. If the
        extension has a modern :file:`static/` directory, they will be
        installed into :file:`{settings.STATIC_ROOT}/ext/`.

        Args:
            ext_class (type):
                The extension class owning the static media to install.

        Raises:
            djblets.extensions.errors.InstallExtensionMediaError:
                There was a fatal error writing static media files. The
                error will be logged and details will be in the error
                message.
        """
        ext_info = ext_class.info

        if ext_info.has_resource('htdocs'):
            # This is an older extension that doesn't use the static file
            # support. Log a notice that the files won't be installed.
            logger.error('The %s extension uses the deprecated "htdocs" '
                         'directory for static files. This is no longer '
                         'supported. It must be updated to use a "static" '
                         'directory instead.',
                         ext_info.name)

        ext_static_path = ext_info.installed_static_path

        if os.path.exists(ext_static_path):
            # Get rid of the old static contents.
            shutil.rmtree(ext_static_path, ignore_errors=True)

            if os.path.exists(ext_static_path):
                # We'll warn here, but we're probably going to fail further
                # down. We'll raise a suitable error at that time.
                logger.critical('Unable to remove old extension media for %s '
                                'at %s. Make sure this path, its parent, and '
                                'everything under it is writable by your '
                                'web server.',
                                ext_info.name, ext_static_path)

        try:
            extracted_path = ext_info.extract_resource('static')

            if extracted_path:
                shutil.copytree(extracted_path, ext_static_path, symlinks=True)
        except Exception as e:
            logger.exception('Unable to install extension media for %s to '
                             '%s: %s. The extension may not work, and '
                             'pages may crash.',
                             ext_info.name, ext_static_path, e)

            raise InstallExtensionMediaError(
                _('Unable to install static media files for this extension. '
                  'The extension will not work correctly without them. Please '
                  'make sure that "%(path)s", its contents, and its parent '
                  'directory are owned by the web server.')
                % {
                    'path': ext_class.info.installed_static_path,
                })

    def _uninstall_extension(
        self,
        extension: Extension,
    ) -> None:
        """Uninstall extension data.

        This performs any uninstallation necessary for an extension. That
        includes the removal of static media, and will disable the registration
        for the extension.

        Args:
            extension (djblets.extensions.extension.Extension):
                The extension being uninstalled.
        """
        extension.settings.set(self.VERSION_SETTINGS_KEY, None)
        extension.settings.save()

        extension.registration.installed = False
        extension.registration.save()

        for media_path in (extension.info.installed_htdocs_path,
                           extension.info.installed_static_path):
            if os.path.exists(media_path):
                shutil.rmtree(media_path, ignore_errors=True)

    def _install_admin_urls(
        self,
        extension: Extension,
    ) -> None:
        """Install administration URLs.

        This provides URLs for configuring an extension, plus any additional
        admin urlpatterns that the extension provides.

        Args:
            extension (djblets.extensions.extension.Extension):
                The extension being installed.
        """
        prefix = self.get_absolute_url()

        if hasattr(settings, 'SITE_ROOT'):
            prefix = prefix[len(settings.SITE_ROOT):]

        # Note that we're adding to the resolve list on the root of the
        # install, and prefixing it with the admin extensions path.
        # The reason we're not just making this a child of our extensions
        # urlconf is that everything in there gets passed an
        # extension_manager variable, and we don't want to force extensions
        # to handle this.
        if extension.is_configurable:
            urlconf = extension.admin_urlconf

            if hasattr(urlconf, 'urlpatterns'):
                extension.admin_urlpatterns = [
                    path('%s%s/config/' % (prefix, extension.id),
                         include(urlconf.__name__)),
                ]

                self.dynamic_urls.add_patterns(extension.admin_urlpatterns)

        if getattr(extension, 'admin_site', None):
            extension.admin_site_urlpatterns = [
                path('%s%s/db/' % (prefix, extension.id),
                     extension.admin_site.urls)
            ]

            self.dynamic_urls.add_patterns(extension.admin_site_urlpatterns)

    def _register_static_bundles(
        self,
        extension: Extension,
    ) -> None:
        """Register the extension's static bundles with Pipeline.

        Each static bundle will appear as an entry in Pipeline. The
        bundle name and filenames will be changed to include the extension
        ID for the static file lookups.

        Args:
            extension (djblets.extensions.extension.Extension):
                The extension containing the static media bundles to register.
        """
        def _add_prefix(
            filename: str,
        ) -> str:
            return f'ext/{extension.id}/{filename}'

        def _add_bundles(
            *,
            pipeline_bundles: dict[str, dict[str, Any]],
            extension_bundles: Union[CSSBundleConfigs, JSBundleConfigs],
            default_dir: str,
            ext: str,
        ) -> None:
            for name, bundle in extension_bundles.items():
                pipeline_bundles[extension.get_bundle_id(name)] = {
                    **bundle,
                    'source_filenames': [
                        _add_prefix(filename)
                        for filename in bundle.get('source_filenames', [])
                    ],
                    'output_filename': _add_prefix(bundle.get(
                        'output_filename',
                        f'{default_dir}/{name}.min{ext}')),
                }

        _add_bundles(pipeline_bundles=pipeline_settings.STYLESHEETS,
                     extension_bundles=extension.css_bundles,
                     default_dir='css',
                     ext='.css')

        _add_bundles(pipeline_bundles=pipeline_settings.JAVASCRIPT,
                     extension_bundles=extension.js_bundles,
                     default_dir='js',
                     ext='.js')

    def _unregister_static_bundles(
        self,
        extension: Extension,
    ) -> None:
        """Unregister the extension's static bundles from Pipeline.

        Every static bundle previously registered for this extension will be
        removed. Further static media lookups involving the extension will
        fail.

        Args:
            extension (djblets.extensions.extension.Extension):
                The extension containing the static media bundles to
                unregister.
        """
        def _remove_bundles(
            *,
            pipeline_bundles: dict[str, dict[str, Any]],
            extension_bundles: Union[CSSBundleConfigs, JSBundleConfigs],
        ) -> None:
            for name, bundle in extension_bundles.items():
                try:
                    del pipeline_bundles[extension.get_bundle_id(name)]
                except KeyError:
                    pass

        if hasattr(settings, 'PIPELINE'):
            _remove_bundles(pipeline_bundles=pipeline_settings.STYLESHEETS,
                            extension_bundles=extension.css_bundles)

            _remove_bundles(pipeline_bundles=pipeline_settings.JAVASCRIPT,
                            extension_bundles=extension.js_bundles)

    def _init_admin_site(
        self,
        extension: Extension,
    ) -> None:
        """Create and initialize an administration site for an extension.

        The administration site is used for browsing extension-owned database
        models and providing configuration or other administration-specific
        views.

        This creates the admin site and imports the extensions admin
        module to register the models.

        Args:
            extension (djblets.extensions.extension.Extension):
                The extension to create the administration site for.
        """
        extension.admin_site = AdminSite(extension.info.app_name)

        # Import the extension's admin module.
        try:
            admin_module_name = '%s.admin' % extension.info.app_name

            if admin_module_name in sys.modules:
                # If the extension has been loaded previously and we are
                # re-enabling it, we must reload the module. Just importing
                # again will not cause the ModelAdmins to be registered.
                reload(sys.modules[admin_module_name])
            else:
                import_module(admin_module_name)
        except ImportError:
            mod = import_module(extension.info.app_name)

            # Decide whether to bubble up this error. If the app just doesn't
            # have an admin module, we can ignore the error attempting to
            # import it, otherwise we want it to bubble up.
            if module_has_submodule(mod, 'admin'):
                raise ImportError(
                    'Importing admin module for extension "%s" failed'
                    % extension.info.app_name)

    def _add_to_installed_apps(
        self,
        extension: Extension,
    ) -> List[str]:
        """Add an extension's apps to the list of installed apps.

        This will register each app with Django and clear any caches needed
        to load the extension's modules.

        Args:
            extension (djblets.extensions.extension.Extension):
                The extension whose apps are being added.

        Returns:
            list of str:
            The list of newly-installed apps.
        """
        new_installed_apps = extension.apps or [extension.info.app_name]
        self._installed_apps_setting.add_list(new_installed_apps)

        apps.set_installed_apps(settings.INSTALLED_APPS)

        return new_installed_apps

    def _remove_from_installed_apps(
        self,
        extension: Extension,
    ) -> None:
        """Remove an extension's apps from the list of installed apps.

        This will unregister each app with Django and clear any caches
        storing the apps' models.

        Args:
            extension (djblets.extensions.extension.Extension):
                The extension whose apps are being removed.
        """
        # Remove the extension's apps from INSTALLED_APPS.
        self._installed_apps_setting.remove_list(
            extension.apps or [extension.info.app_name])

        # Now clear the apps and their modules from any caches.
        apps.unset_installed_apps()

    def _entrypoint_iterator(
        self,
    ) -> Iterator[importlib_metadata.EntryPoint]:
        """Iterate through registered Python entry points.

        This is a thin wrapper around
        :py:func:`importlib.metadata.entry_points`. It's primarily here for
        unit test purposes.

        Yields:
            importlib.metadata.EntryPoint:
            A Python entry point for the extension manager's key.
        """
        return iter(importlib_metadata.entry_points(group=self.key))

    def _bump_sync_gen(self) -> None:
        """Bump the synchronization generation value.

        If there's an existing synchronization generation in cache,
        increment it. Otherwise, start fresh with a new one.

        This will also set ``settings.AJAX_SERIAL``, which will guarantee any
        cached objects that depends on templates and use this serial number
        will be invalidated, allowing TemplateHooks and other hooks
        to be re-run.
        """
        # If we're in the middle of loading extension state, perhaps due to
        # the sync number being bumped by another process, this flag will be
        # sent in order to block any further attempts at bumping the number.
        # Failure to do this can result in a loop where the number gets
        # bumped by every process/thread reacting to another process/thread
        # bumping the number, resulting in massive slowdown and errors.
        if self._block_sync_gen:
            return

        self._gen_sync.mark_updated()
        settings.AJAX_SERIAL = self._gen_sync.sync_gen

    def _recalculate_middleware(self) -> None:
        """Recalculate the list of middleware.

        All middleware provided by extensions will be registered in the
        Django settings and will be used for future requests.
        """
        self.middleware_classes = []
        done: Set[Extension] = set()

        for e in self.get_enabled_extensions():
            self.middleware_classes += self._get_extension_middleware(e, done)

    def _get_extension_middleware(
        self,
        extension: Extension,
        done: Set[Extension],
    ) -> List[str]:
        """Return a list of middleware for an extension and its dependencies.

        This is a recursive utility function initially called by
        :py:meth:`_recalculate_middleware` that ensures that middleware for all
        dependencies are inserted before that of the given extension. It also
        ensures that each extension's middleware is inserted only once.

        Args:
            extension (djblets.extensions.extension.Extension):
                The extension to load middleware from.

            done (set):
                A set of middleware that's already been loaded. Any middleware
                found that exist in this set will be ignored.

        Returns:
            list:
            A list of classes for middleware.
        """
        middleware: List[str] = []

        if extension in done:
            return middleware

        done.add(extension)

        for req in extension.requirements:
            e = self.get_enabled_extension(req)

            if e:
                middleware += self._get_extension_middleware(e, done)

        middleware.extend(extension.middleware_classes)
        return middleware

    def _parse_version(
        self,
        version: Optional[str],
    ) -> Optional[Version]:
        """Parse and return a Version for a package.

        If the version can't be parsed, ``None`` will be returned.

        Version Added:
            3.3

        Args:
            version (str):
                The version string.

        Returns:
            packaging.version.Version:
            The parsed version, or ``None`` if the version could not be
            parsed.
        """
        if version is not None:
            try:
                return parse_version(version)
            except InvalidVersion:
                pass

        return None

    @contextmanager
    def _open_lock_file(
        self,
        ext_class: Type[Extension],
        filename: str,
        lock_flags: int = locks.LOCK_EX | locks.LOCK_NB,
    ) -> Iterator:
        """Open a lock file for a multi-threaded/process operation.

        This will attempt to create a lock file and acquire a lock on it,
        yielding to the caller if a lock is acquired, and cleaning up after
        if it is not.

        If a lock file cannot be written or a lock cannot be acquired, this
        will raise immediately.

        Args:
            ext_class (type):
                The extension class that this lock file pertains to.

            filename (str):
                The name of the lock file. This will be created within the
                temp directory, and should just be a filename.

            lock_flags (int, optional):
                Flags to specify when acquiring a lock.

        Context:
            The lock will be acquired. The caller can successfully perform
            its operations.

        Raises:
            IOError:
                The lock file could not be written or a lock could not be
                acquired.
        """
        if not os.path.isabs(filename):
            filename = os.path.join(tempfile.gettempdir(), filename)

        with open(filename, 'w') as fp:
            locks.lock(fp, lock_flags)

            try:
                yield
            finally:
                locks.unlock(fp)

                try:
                    os.unlink(filename)
                except OSError as e:
                    # A "No such file or directory" (ENOENT) is most likely
                    # due to another thread removing the lock file before
                    # this thread could. It's safe to ignore. We want to
                    # handle all others, though.
                    if e.errno != errno.ENOENT:
                        logger.exception(
                            'Failed to unlock lock file "%s" for extension '
                            '"%s": %s',
                            filename, ext_class.info, e)


def get_extension_managers() -> List[ExtensionManager]:
    """Return all extension manager instances.

    This will return all the extension managers that have been constructed.
    The order is not guaranteed.

    Returns:
        list of ExtensionManager:
        The list of all extension manager instances currently registered.
    """
    return list(_extension_managers.values())


def shutdown_extension_managers() -> None:
    """Shut down all extension managers.

    This is called automatically when the process exits, but can be run
    manually.
    """
    for extension_manager in get_extension_managers():
        extension_manager.shutdown()


# When the process ends, shut down the extensions on this manager.
# That will help work around bugs in Django where it attempts to
# work with garbage state being held onto by extensions.
atexit.register(shutdown_extension_managers)
