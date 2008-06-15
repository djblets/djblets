import os
import shutil
import sys

from django.conf import settings
from django.conf.urls.defaults import patterns, include
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import get_resolver, get_mod_func

from djblets.extensions.models import RegisteredExtension


if not hasattr(settings, "EXTENSIONS_MEDIA_ROOT"):
    raise ImproperlyConfigured, \
          "settings.EXTENSIONS_MEDIA_ROOT must be defined"

if not os.path.exists(settings.EXTENSIONS_MEDIA_ROOT):
    raise ImproperlyConfigured, \
          "%s must exist and must be writable by the web server." % \
          settings.EXTENSIONS_MEDIA_ROOT


_extension_managers = []


class Settings(dict):
    """
    Settings data for an extension. This is a glorified dictionary that
    acts as a proxy for the extension's stored settings in the database.

    Callers must call save() when they want to make the settings persistent.
    """
    def __init__(self, extension):
        dict.__init__(self)
        self.extension = extension
        self.load()

    def load(self):
        try:
            self.update(self.extension.registration.settings)
        except ValueError:
            # The settings in the database are invalid. We'll have to discard
            # it. Note that this should never happen unless the user
            # hand-modifies the entries and breaks something.
            pass

    def save(self):
        registration = self.extension.registration
        registration.settings = dict(self)
        registration.save()


class Extension(object):
    def __init__(self):
        self.hooks = set()
        self.admin_ext_resolver = None
        self.settings = Settings(self)

    def shutdown(self):
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


    def get_is_configurable(self):
        """
        Returns whether or not this extension can be configured. Extensions
        returning true should have a config/ URL in their admin_url_patterns.
        """
        return False

    # Don't bind directly to the function or extensions won't be able to
    # override it.
    is_configurable = property(lambda self: self.get_is_configurable())


class ExtensionInfo(object):
    def __init__(self, entrypoint, ext_class):
        metadata = {}

        for line in entrypoint.dist.get_metadata_lines("PKG-INFO"):
            key, value = line.split(": ", 1)

            if value != "UNKNOWN":
                metadata[key] = value

        self.metadata = metadata
        self.name = entrypoint.dist.project_name
        self.version = entrypoint.dist.version
        self.summary = metadata.get('Summary')
        self.description = metadata.get('Description')
        self.author = metadata.get('Author')
        self.author_email = metadata.get('Author-email')
        self.license = metadata.get('License')
        self.url = metadata.get('Home-page')
        self.enabled = False
        self.htdocs_path = os.path.join(settings.EXTENSIONS_MEDIA_ROOT,
                                        self.name)


class ExtensionHook(object):
    def __init__(self, extension):
        self.extension = extension
        self.extension.hooks.add(self)
        self.__class__.add_hook(self)

    def shutdown(self):
        self.__class__.remove_hook(self)


class ExtensionHookPoint(type):
    def __init__(cls, name, bases, attrs):
        super(ExtensionHookPoint, cls).__init__(name, bases, attrs)

        if not hasattr(cls, "hooks"):
            cls.hooks = []

    def add_hook(cls, hook):
        cls.hooks.append(hook)

    def remove_hook(cls, hook):
        cls.hooks.remove(hook)


class ExtensionManager(object):
    def __init__(self, key):
        self.key = key

        self.pkg_resources = None

        self._extension_classes = {}
        self._extension_instances = {}
        self._admin_ext_resolver = get_resolver(None)

        _extension_managers.append(self)

    def get_absolute_url(self):
        return self._admin_ext_resolver.reverse(
            "djblets.extensions.views.extension_list")

    def get_enabled_extension(self, extension_id):
        if extension_id in self._extension_instances:
            return self._extension_instances[extension_id]

        return None

    def get_enabled_extensions(self):
        return self._extension_instances.values()

    def get_installed_extensions(self):
        return self._extension_classes.values()

    def enable_extension(self, extension_id):
        if extension_id in self._extension_instances:
            # It's already enabled.
            return

        if extension_id not in self._extension_classes:
            # Invalid class.
            # TODO: Raise an exception
            return

        ext_class = self._extension_classes[extension_id]
        ext_class.registration.enabled = True
        ext_class.registration.save()
        self.__install_extension(ext_class)
        return self.__init_extension(ext_class)

    def disable_extension(self, extension_id):
        if extension_id not in self._extension_instances:
            # Invalid extension.
            # TODO: Raise an exception
            return

        extension = self._extension_instances[extension_id]
        extension.registration.enabled = False
        extension.registration.save()
        self.__uninstall_extension(extension)
        self.__uninit_extension(extension)

    def load(self):
        """
        Loads all known extensions, initializing any that are recorded as
        being enabled.

        If this is called a second time, it will refresh the list of
        extensions, adding new ones and removing deleted ones.
        """
        # Preload all the RegisteredExtension objects
        registered_extensions = {}
        for registered_ext in RegisteredExtension.objects.all():
            registered_extensions[registered_ext.class_name] = registered_ext

        found_extensions = {}

        # Reload pkg_resources
        import pkg_resources
        if pkg_resources:
            del pkg_resources
            del sys.modules['pkg_resources']
            import pkg_resources

        for entrypoint in pkg_resources.iter_entry_points(self.key):
            try:
                ext_class = entrypoint.load()

                # Don't override the info if we've previously loaded this
                # class.
                if not getattr(ext_class, "info", None):
                    ext_class.info = ExtensionInfo(entrypoint, ext_class)
            except Exception, e:
                print "Error loading extension %s: %s" % (entrypoint.name, e)
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
            if not getattr(ext_class, "registration", None):
                if class_name in registered_extensions:
                    registered_ext = registered_extensions[class_name]
                else:
                    try:
                        registered_ext = RegisteredExtension.objects.get(
                            class_name=class_name)
                    except RegisteredExtension.DoesNotExist:
                        registered_ext = RegisteredExtension(
                            class_name=class_name,
                            name=entrypoint.dist.project_name
                        )
                        registered_ext.save()

                ext_class.registration = registered_ext

            if (registered_ext.enabled and
                not ext_class.id in self._extension_instances):
                self.__init_extension(ext_class)

        # At this point, if we're reloading, it's possible that the user
        # has removed some extensions. Go through and remove any that we
        # can no longer find.
        for class_name in self._extension_classes.keys():
            if class_name not in found_extensions:
                if class_name in self._extension_instances:
                    self.disable_extension(class_name)

                del self._extension_classes[class_name]

    def __init_extension(self, ext_class):
        assert ext_class.id not in self._extension_instances
        extension = ext_class()
        extension.extension_manager = self
        self._extension_instances[extension.id] = extension

        if extension.is_configurable:
            self.__install_admin_urls(extension)

        extension.info.enabled = True

        return extension

    def __uninit_extension(self, extension):
        extension.shutdown()

        if extension.admin_urlpatterns:
            for urlpattern in extension.admin_urlpatterns:
                self._admin_ext_resolver.url_patterns.remove(urlpattern)

        extension.info.enabled = False
        del self._extension_instances[extension.id]

    def __install_extension(self, ext_class):
        """
        Performs any installation necessary for an extension.
        This will install the contents of htdocs into the
        EXTENSIONS_MEDIA_ROOT directory.
        """
        import pkg_resources

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

    def __uninstall_extension(self, extension):
        """
        Performs any uninstallation necessary for an extension.
        This will uninstall the contents of
        EXTENSIONS_MEDIA_ROOT/extension-name/.
        """
        ext_path = extension.info.htdocs_path
        ext_path_exists = os.path.exists(ext_path)

        if ext_path_exists:
            shutil.rmtree(ext_path, ignore_errors=True)

    def __install_admin_urls(self, extension):
        urlconf = extension.admin_urlconf

        if hasattr(urlconf, "urlpatterns"):
            # Note that we're adding to the resolve list on the root of the
            # install, and prefixing it with the admin extensions path.
            # The reason we're not just making this a child of our extensions
            # urlconf is that everything in there gets passed an
            # extension_manager variable, and we don't want to force extensions
            # to handle this.
            prefix = self.get_absolute_url()

            extension.admin_urlpatterns = patterns('',
                (r'^%s%s/config/' % (prefix, extension.id),
                 include(urlconf.__name__)))

            self._admin_ext_resolver.url_patterns.extend(
                extension.admin_urlpatterns)


def get_extension_managers():
    return _extension_managers
