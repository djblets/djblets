#
# base.py -- Base classes for extensions.
#
# Copyright (c) 2010-2011  Beanbag, Inc.
# Copyright (c) 2008-2010  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import datetime
import logging
import os
import pkg_resources
import shutil
import sys
import time

from django.conf import settings
from django.conf.urls import patterns, include
from django.contrib.admin.sites import AdminSite
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.urlresolvers import get_mod_func, reverse
from django.db.models import loading
from django.template.loader import template_source_loaders
from django.utils.importlib import import_module
from django.utils.module_loading import module_has_submodule
from django_evolution.management.commands.evolve import Command as Evolution
from setuptools.command import easy_install

from djblets.extensions.errors import EnablingExtensionError, \
                                      InstallExtensionError, \
                                      InvalidExtensionError
from djblets.extensions.models import RegisteredExtension
from djblets.extensions.signals import extension_initialized, \
                                       extension_uninitialized
from djblets.util.misc import make_cache_key
from djblets.util.urlresolvers import DynamicURLResolver



if not hasattr(settings, "EXTENSIONS_STATIC_ROOT"):
    raise ImproperlyConfigured, \
          "settings.EXTENSIONS_STATIC_ROOT must be defined"


_extension_managers = []


class Settings(dict):
    """
    Settings data for an extension. This is a glorified dictionary that
    acts as a proxy for the extension's stored settings in the database.

    Callers must call save() when they want to make the settings persistent.

    If a key is not found in the dictionary, extension.default_settings
    will be checked as well.
    """
    def __init__(self, extension):
        dict.__init__(self)
        self.extension = extension
        self.load()

    def __getitem__(self, key):
        """Retrieve an item from the dictionary.

        This will attempt to return a default value from
        extension.default_settings if the setting has not
        been set.
        """
        if super(Settings, self).__contains__(key):
            return super(Settings, self).__getitem__(key)

        if key in self.extension.default_settings:
            return self.extension.default_settings[key]

        raise KeyError(
            'The settings key "%(key)s" was not found in extension %(ext)s' % {
                'key': key,
                'ext': self.extension.id
            })

    def __contains__(self, key):
        """Indicate if the setting is present.

        If the key is not present in the settings dictionary
        check the default settings as well.
        """
        if super(Settings, self).__contains__(key):
            return True

        return key in self.extension.default_settings

    def set(self, key, value):
        self[key] = value

    def load(self):
        """Loads the settings from the database."""
        try:
            self.update(self.extension.registration.settings)
        except ValueError:
            # The settings in the database are invalid. We'll have to discard
            # it. Note that this should never happen unless the user
            # hand-modifies the entries and breaks something.
            pass

    def save(self):
        """Saves all current settings to the database."""
        registration = self.extension.registration
        registration.settings = dict(self)
        registration.save()

        # Make sure others are aware that the configuration changed.
        self.extension.extension_manager._bump_sync_gen()


class Extension(object):
    """Base class for an extension.

    Extensions must subclass for this class. They'll automatically have
    support for settings, adding hooks, and plugging into the administration
    UI.

    If an extension supports configuration in the UI, it should set
    :py:attr:`is_configurable` to True.

    If an extension would like to specify defaults for the settings
    dictionary it should provide a dictionary in :py:attr:`default_settings`.

    If an extension would like a django admin site for modifying the database,
    it should set :py:attr:`has_admin_site` to True.

    Extensions should list all other extension names that they require in
    :py:attr:`requirements`.

    If an extension has any middleware, it should set :py:attr:`middleware`
    to a list of class names. This extension's middleware will be loaded after
    any middleware belonging to any extensions in the :py:attr:`requirements`
    list.
    """
    metadata = None
    is_configurable = False
    default_settings = {}
    has_admin_site = False
    requirements = []
    resources = []
    apps = []
    middleware = []

    def __init__(self, extension_manager):
        self.extension_manager = extension_manager
        self.hooks = set()
        self.settings = Settings(self)
        self.admin_site = None
        self.middleware_instances = [m() for m in self.middleware]

    def shutdown(self):
        """Shuts down the extension.

        This will shut down every registered hook.

        Subclasses should override this if they need custom shutdown behavior.
        """
        for hook in self.hooks:
            hook.shutdown()

    def _get_admin_urlconf(self):
        if not hasattr(self, "_admin_urlconf_module"):
            try:
                name = "%s.%s" % (get_mod_func(self.__class__.__module__)[0],
                                  "admin_urls")
                self._admin_urlconf_module = __import__(name, {}, {}, [''])
            except Exception, e:
                raise ImproperlyConfigured, \
                    "Error while importing extension's admin URLconf %r: %s" % \
                    (name, e)

        return self._admin_urlconf_module
    admin_urlconf = property(_get_admin_urlconf)


class ExtensionInfo(object):
    """Information on an extension.

    This class stores the information and metadata on an extension. This
    includes the name, version, author information, where it can be downloaded,
    whether or not it's enabled or installed, and anything else that may be
    in the Python package for the extension.
    """
    def __init__(self, entrypoint, ext_class):
        metadata = {}

        for line in entrypoint.dist.get_metadata_lines("PKG-INFO"):
            key, value = line.split(": ", 1)

            if value != "UNKNOWN":
                metadata[key] = value

        # Extensions will often override "Name" to be something
        # user-presentable, but we sometimes need the package name
        self.package_name = metadata.get('Name')

        if ext_class.metadata is not None:
            metadata.update(ext_class.metadata)

        self.metadata = metadata
        self.name = metadata.get('Name')
        self.version = metadata.get('Version')
        self.summary = metadata.get('Summary')
        self.description = metadata.get('Description')
        self.author = metadata.get('Author')
        self.author_email = metadata.get('Author-email')
        self.license = metadata.get('License')
        self.url = metadata.get('Home-page')
        self.author_url = metadata.get('Author-home-page', self.url)
        self.app_name = '.'.join(ext_class.__module__.split('.')[:-1])
        self.enabled = False
        self.installed = False
        self.is_configurable = ext_class.is_configurable
        self.has_admin_site = ext_class.has_admin_site
        self.htdocs_path = os.path.join(settings.EXTENSIONS_STATIC_ROOT,
                                        self.package_name)

    def __unicode__(self):
        return "%s %s (enabled = %s)" % (self.name, self.version, self.enabled)


class ExtensionHook(object):
    """The base class for a hook into some part of the project.

    ExtensionHooks are classes that can hook into an
    :py:class:`ExtensionHookPoint` to provide some level of functionality
    in a project. A project should provide a subclass of ExtensionHook that
    will provide functions for getting data or anything else that's needed,
    and then extensions will subclass that specific ExtensionHook.

    A base ExtensionHook subclass must use :py:class:`ExtensionHookPoint`
    as a metaclass. For example::

        class NavigationHook(ExtensionHook):
            __metaclass__ = ExtensionHookPoint
    """
    def __init__(self, extension):
        self.extension = extension
        self.extension.hooks.add(self)
        self.__class__.add_hook(self)

    def shutdown(self):
        self.__class__.remove_hook(self)


class ExtensionHookPoint(type):
    """A metaclass used for base Extension Hooks.

    Base :py:class:`ExtensionHook` classes use :py:class:`ExtensionHookPoint`
    as a metaclass. This metaclass stores the list of registered hooks that
    an :py:class:`ExtensionHook` will automatically register with.
    """
    def __init__(cls, name, bases, attrs):
        super(ExtensionHookPoint, cls).__init__(name, bases, attrs)

        if not hasattr(cls, "hooks"):
            cls.hooks = []

    def add_hook(cls, hook):
        """Adds an ExtensionHook to the list of active hooks.

        This is called automatically by :py:class:`ExtensionHook`.
        """
        cls.hooks.append(hook)

    def remove_hook(cls, hook):
        """Removes an ExtensionHook from the list of active hooks.

        This is called automatically by :py:class:`ExtensionHook`.
        """
        cls.hooks.remove(hook)


class ExtensionManager(object):
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
    """
    def __init__(self, key):
        self.key = key

        self.pkg_resources = None

        self._extension_classes = {}
        self._extension_instances = {}

        # State synchronization
        self._sync_key = make_cache_key('extensionmgr:%s:gen' % key)
        self._last_sync_gen = None

        self.dynamic_urls = DynamicURLResolver()

        # Extension middleware instances, ordered by dependencies.
        self.middleware = []

        _extension_managers.append(self)

    def get_url_patterns(self):
        """Returns the URL patterns for the Extension Manager.

        This should be included in the root urlpatterns for the site.
        """
        return patterns('', self.dynamic_urls)

    def is_expired(self):
        """Returns whether or not the extension state is possibly expired.

        Extension state covers the lists of extensions and each extension's
        configuration. It can expire if the state synchronization value
        falls out of cache or is changed.

        Each ExtensionManager has its own state synchronization cache key.
        """
        sync_gen = cache.get(self._sync_key)

        return (sync_gen is None or
                (type(sync_gen) is int and sync_gen != self._last_sync_gen))

    def clear_sync_cache(self):
        cache.delete(self._sync_key)

    def get_absolute_url(self):
        return reverse("djblets.extensions.views.extension_list")

    def get_enabled_extension(self, extension_id):
        """Returns an enabled extension with the given ID."""
        if extension_id in self._extension_instances:
            return self._extension_instances[extension_id]

        return None

    def get_enabled_extensions(self):
        """Returns the list of all enabled extensions."""
        return self._extension_instances.values()

    def get_installed_extensions(self):
        """Returns the list of all installed extensions."""
        return self._extension_classes.values()

    def get_installed_extension(self, extension_id):
        """Returns the installed extension with the given ID."""
        if extension_id not in self._extension_classes:
            raise InvalidExtensionError(extension_id)

        return self._extension_classes[extension_id]

    def get_dependent_extensions(self, dependency_extension_id):
        """Returns a list of all extensions required by an extension."""
        if dependency_extension_id not in self._extension_instances:
            raise InvalidExtensionError(dependency_extension_id)

        dependency = self.get_installed_extension(dependency_extension_id)
        result = []

        for extension_id, extension in self._extension_classes.iteritems():
            if extension_id == dependency_extension_id:
                continue

            for ext_requirement in extension.info.requirements:
                if ext_requirement == dependency:
                    result.append(extension_id)

        return result

    def enable_extension(self, extension_id):
        """Enables an extension.

        Enabling an extension will install any data files the extension
        may need, any tables in the database, perform any necessary
        database migrations, and then will start up the extension.
        """
        if extension_id in self._extension_instances:
            # It's already enabled.
            return

        if extension_id not in self._extension_classes:
            raise InvalidExtensionError(extension_id)

        ext_class = self._extension_classes[extension_id]

        # Enable extension dependencies
        for requirement_id in ext_class.requirements:
            self.enable_extension(requirement_id)

        try:
            self._install_extension(ext_class)
        except InstallExtensionError, e:
            raise EnablingExtensionError(e.message)

        ext_class.registration.enabled = True
        ext_class.registration.save()
        extension = self._init_extension(ext_class)

        self._clear_template_cache()
        self._bump_sync_gen()
        self._recalculate_middleware()

        return extension

    def disable_extension(self, extension_id):
        """Disables an extension.

        Disabling an extension will remove any data files the extension
        installed and then shut down the extension and all of its hooks.

        It will not delete any data from the database.
        """
        if extension_id not in self._extension_instances:
            # It's not enabled.
            return

        if extension_id not in self._extension_classes:
            raise InvalidExtensionError(extension_id)

        extension = self._extension_instances[extension_id]

        for dependent_id in self.get_dependent_extensions(extension_id):
            self.disable_extension(dependent_id)

        self._uninstall_extension(extension)
        self._uninit_extension(extension)
        extension.registration.enabled = False
        extension.registration.save()

        self._clear_template_cache()
        self._bump_sync_gen()
        self._recalculate_middleware()

    def install_extension(self, install_url, package_name):
        """Install an extension from a remote source.

        Installs an extension from a remote URL containing the
        extension egg. Installation may fail if a malformed install_url
        or package_name is passed, which will cause an InstallExtensionError
        exception to be raised. It is also assumed that the extension is not
        already installed.
        """

        try:
            easy_install.main(["-U", install_url])

            # Update the entry points.
            dist = pkg_resources.get_distribution(package_name)
            dist.activate()
            pkg_resources.working_set.add(dist)
        except pkg_resources.DistributionNotFound:
            raise InstallExtensionError("Invalid package name.")
        except SystemError:
            raise InstallExtensionError("Installation failed "
                                        "(probably malformed URL).")

        # Refresh the extension manager.
        self.load(True)

    def load(self, full_reload=False):
        """
        Loads all known extensions, initializing any that are recorded as
        being enabled.

        If this is called a second time, it will refresh the list of
        extensions, adding new ones and removing deleted ones.

        If full_reload is passed, all state is cleared and we reload all
        extensions and state from scratch.
        """
        if full_reload:
            # We're reloading everything, so nuke all the cached copies.
            self._clear_extensions()
            self._clear_template_cache()

        # Preload all the RegisteredExtension objects
        registered_extensions = {}
        for registered_ext in RegisteredExtension.objects.all():
            registered_extensions[registered_ext.class_name] = registered_ext

        found_extensions = {}
        extensions_changed = False

        for entrypoint in self._entrypoint_iterator():
            registered_ext = None

            try:
                ext_class = entrypoint.load()

                # Don't override the info if we've previously loaded this
                # class.
                if not getattr(ext_class, "info", None):
                    ext_class.info = ExtensionInfo(entrypoint, ext_class)
            except Exception, e:
                logging.error("Error loading extension %s: %s" %
                              (entrypoint.name, e))
                continue

            # A class's extension ID is its class name. We want to
            # make this easier for users to access by giving it an 'id'
            # variable, which will be accessible both on the class and on
            # instances.
            class_name = ext_class.id = "%s.%s" % (ext_class.__module__,
                                                   ext_class.__name__)
            self._extension_classes[class_name] = ext_class
            found_extensions[class_name] = ext_class

            # If the ext_class has a registration variable that's set, then
            # it's already been loaded. We don't want to bother creating a
            # new one.
            if not hasattr(ext_class, "registration"):
                if class_name in registered_extensions:
                    registered_ext = registered_extensions[class_name]
                else:
                    registered_ext, is_new = \
                        RegisteredExtension.objects.get_or_create(
                            class_name=class_name,
                            defaults={
                                'name': entrypoint.dist.project_name
                            })

                ext_class.registration = registered_ext

            if (ext_class.registration.enabled and
                ext_class.id not in self._extension_instances):
                self._init_extension(ext_class)
                extensions_changed = True

        # At this point, if we're reloading, it's possible that the user
        # has removed some extensions. Go through and remove any that we
        # can no longer find.
        #
        # While we're at it, since we're at a point where we've seen all
        # extensions, we can set the ExtensionInfo.requirements for
        # each extension
        for class_name, ext_class in self._extension_classes.iteritems():
            if class_name not in found_extensions:
                if class_name in self._extension_instances:
                    self.disable_extension(class_name)

                del self._extension_classes[class_name]
                extensions_changed = True
            else:
                ext_class.info.requirements = \
                    [self.get_installed_extension(requirement_id)
                     for requirement_id in ext_class.requirements]

        # Add the sync generation if it doesn't already exist.
        self._add_new_sync_gen()
        self._last_sync_gen = cache.get(self._sync_key)
        settings.AJAX_SERIAL = self._last_sync_gen

        if extensions_changed:
            self._recalculate_middleware()

    def _clear_extensions(self):
        """Clear the entire list of known extensions.

        This will bring the ExtensionManager back to the state where
        it doesn't yet know about any extensions, requiring a re-load.
        """
        for extension in self._extension_instances.values():
            self._uninit_extension(extension)

        for extension_class in self._extension_classes.values():
            if hasattr(extension_class, 'info'):
                delattr(extension_class, 'info')

            if hasattr(extension_class, 'registration'):
                delattr(extension_class, 'registration')

        self._extension_classes = {}
        self._extension_instances = {}

    def _clear_template_cache(self):
        """Clears the Django template caches."""
        if template_source_loaders:
            for template_loader in template_source_loaders:
                if hasattr(template_loader, 'reset'):
                    template_loader.reset()

    def _init_extension(self, ext_class):
        """Initializes an extension.

        This will register the extension, install any URLs that it may need,
        and make it available in Django's list of apps. It will then notify
        that the extension has been initialized.
        """
        assert ext_class.id not in self._extension_instances

        try:
            extension = ext_class(extension_manager=self)
        except Exception, e:
            logging.error('Unable to initialize extension %s: %s'
                          % (ext_class, e), exc_info=1)
            raise EnablingExtensionError('Error initializing extension: %s'
                                         % e)

        self._extension_instances[extension.id] = extension

        if extension.has_admin_site:
            self._init_admin_site(extension)

        # Installing the urls must occur after _init_admin_site(). The urls
        # for the admin site will not be generated until it is called.
        self._install_admin_urls(extension)

        extension.info.installed = extension.registration.installed
        extension.info.enabled = True
        self._add_to_installed_apps(extension)
        self._reset_templatetags_cache()
        extension_initialized.send(self, ext_class=extension)

        return extension

    def _uninit_extension(self, extension):
        """Uninitializes the extension.

        This will shut down the extension, remove any URLs, remove it from
        Django's list of apps, and send a signal saying the extension was
        shut down.
        """
        extension.shutdown()

        if hasattr(extension, "admin_urlpatterns"):
            self.dynamic_urls.remove_patterns(
                extension.admin_urlpatterns)

        if hasattr(extension, "admin_site_urlpatterns"):
            self.dynamic_urls.remove_patterns(
                extension.admin_site_urlpatterns)

        if extension.has_admin_site:
            del extension.admin_site

        self._remove_from_installed_apps(extension)
        self._reset_templatetags_cache()
        extension.info.enabled = False
        extension_uninitialized.send(self, ext_class=extension)

        del self._extension_instances[extension.id]

    def _reset_templatetags_cache(self):
        """Clears the Django templatetags_modules cache."""
        # We'll import templatetags_modules here because
        # we want the most recent copy of templatetags_modules
        from django.template.base import get_templatetags_modules, \
                                         templatetags_modules
        # Wipe out the contents
        del(templatetags_modules[:])

        # And reload the cache
        get_templatetags_modules()

    def _install_extension(self, ext_class):
        """Installs extension data.

        Performs any installation necessary for an extension.
        This will install the contents of htdocs into the
        EXTENSIONS_STATIC_ROOT directory.
        """
        ext_path = ext_class.info.htdocs_path
        ext_path_exists = os.path.exists(ext_path)

        if ext_path_exists:
            # First, get rid of the old htdocs contents, so we can start
            # fresh.
            shutil.rmtree(ext_path, ignore_errors=True)

        if pkg_resources.resource_exists(ext_class.__module__, "htdocs"):
            # Now install any new htdocs contents.
            extracted_path = \
                pkg_resources.resource_filename(ext_class.__module__, "htdocs")

            shutil.copytree(extracted_path, ext_path, symlinks=True)

        # Mark the extension as installed
        ext_class.registration.installed = True
        ext_class.registration.save()

        # Now let's build any tables that this extension might need
        self._add_to_installed_apps(ext_class)

        # Call syncdb to create the new tables
        loading.cache.loaded = False
        call_command('syncdb', verbosity=0, interactive=False)

        # Run evolve to do any table modification
        try:
            evolution = Evolution()
            evolution.evolve(verbosity=0, interactive=False,
                             execute=True, hint=False,
                             compile_sql=False, purge=False,
                             database=False)
        except CommandError, e:
            # Something went wrong while running django-evolution, so
            # grab the output.  We can't raise right away because we
            # still need to put stdout back the way it was
            logging.error(e.message)
            raise InstallExtensionError(e.message)

        # Remove this again, since we only needed it for syncdb and
        # evolve.  _init_extension will add it again later in
        # the install.
        self._remove_from_installed_apps(ext_class)

        # Mark the extension as installed
        ext_class.registration.installed = True
        ext_class.registration.save()

    def _uninstall_extension(self, extension):
        """Uninstalls extension data.

        Performs any uninstallation necessary for an extension.
        This will uninstall the contents of
        EXTENSIONS_STATIC_ROOT/extension-name/.
        """
        ext_path = extension.info.htdocs_path
        ext_path_exists = os.path.exists(ext_path)

        if ext_path_exists:
            shutil.rmtree(ext_path, ignore_errors=True)

    def _install_admin_urls(self, extension):
        """Installs administration URLs.

        This provides URLs for configuring an extension, plus any additional
        admin urlpatterns that the extension provides.
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
            if hasattr(urlconf, "urlpatterns"):
                extension.admin_urlpatterns = patterns('',
                    (r'^%s%s/config/' % (prefix, extension.id),
                     include(urlconf.__name__)))

                self.dynamic_urls.add_patterns(
                    extension.admin_urlpatterns)

        if extension.has_admin_site:
            extension.admin_site_urlpatterns = patterns('',
                (r'^%s%s/db/' % (prefix, extension.id),
                include(extension.admin_site.urls)))

            self.dynamic_urls.add_patterns(
                extension.admin_site_urlpatterns)

    def _init_admin_site(self, extension):
        """Creates and initializes an admin site for an extension.

        This creates the admin site and imports the extensions admin
        module to register the models.

        The url patterns for the admin site are generated in
        _install_admin_urls().
        """
        extension.admin_site = AdminSite(extension.info.app_name)

        # Import the extension's admin module.
        try:
            admin_module_name = '%s.admin' % extension.info.app_name
            if admin_module_name in sys.modules:
                # If the extension has been loaded previously and
                # we are re-enabling it, we must reload the module.
                # Just importing again will not cause the ModelAdmins
                # to be registered.
                reload(sys.modules[admin_module_name])
            else:
                import_module(admin_module_name)
        except ImportError:
            mod = import_module(extension.info.app_name)

            # Decide whether to bubble up this error. If the app just
            # doesn't have an admin module, we can ignore the error
            # attempting to import it, otherwise we want it to bubble up.
            if module_has_submodule(mod, 'admin'):
                raise ImportError(
                    "Importing admin module for extension %s failed"
                    % extension.info.app_name)

    def _add_to_installed_apps(self, extension):
        for app in extension.apps or [extension.info.app_name]:
            if app not in settings.INSTALLED_APPS:
                settings.INSTALLED_APPS.append(app)

    def _remove_from_installed_apps(self, extension):
        for app in extension.apps or [extension.info.app_name]:
            if app in settings.INSTALLED_APPS:
                settings.INSTALLED_APPS.remove(app)

    def _entrypoint_iterator(self):
        return pkg_resources.iter_entry_points(self.key)

    def _bump_sync_gen(self):
        """Bumps the synchronization generation value.

        If there's an existing synchronization generation in cache,
        increment it. Otherwise, start fresh with a new one.

        This will also set ``settings.AJAX_SERIAL``, which will guarantee any
        cached objects that depends on templates and use this serial number
        will be invalidated, allowing TemplateHooks and other hooks
        to be re-run.
        """
        try:
            self._last_sync_gen = cache.incr(self._sync_key)
        except ValueError:
            self._last_sync_gen = self._add_new_sync_gen()

        settings.AJAX_SERIAL = self._last_sync_gen

    def _add_new_sync_gen(self):
        val = time.mktime(datetime.datetime.now().timetuple())
        return cache.add(self._sync_key, int(val))

    def _recalculate_middleware(self):
        """Recalculates the list of middleware."""
        self.middleware = []
        done = set()

        for e in self.get_enabled_extensions():
            self.middleware.extend(self._get_extension_middleware(e, done))

    def _get_extension_middleware(self, extension, done):
        """Returns a list of middleware for 'extension' and its dependencies.

        This is a recursive utility function initially called by
        _recalculate_middleware() that ensures that middleware for all
        dependencies are inserted before that of the given extension.  It
        also ensures that each extension's middleware is inserted only once.
        """
        middleware = []

        if extension in done:
            return middleware

        done.add(extension)

        for req in extension.requirements:
            e = self.get_enabled_extension(req)

            if e:
                middleware.extend(self._get_extension_middleware(e, done))

        middleware.extend(extension.middleware_instances)
        return middleware


def get_extension_managers():
    return _extension_managers
