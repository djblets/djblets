import os
import pkg_resources
import shutil

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from djblets.extensions.models import RegisteredExtension


if not hasattr(settings, "EXTENSIONS_MEDIA_ROOT"):
    raise ImproperlyConfigured, \
          "settings.EXTENSIONS_MEDIA_ROOT must be defined"

if not os.path.exists(settings.EXTENSIONS_MEDIA_ROOT):
    raise ImproperlyConfigured, \
          "%s must exist and must be writable by the web server." % \
          settings.EXTENSIONS_MEDIA_ROOT


_extension_managers = []


class Extension(object):
    def __init__(self):
        self.hooks = set()

    def shutdown(self):
        for hook in self.hooks:
            hook.shutdown()


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

        self._extension_classes = {}
        self._extension_instances = {}

        self.__load_extensions()

        _extension_managers.append(self)

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

    def __load_extensions(self):
        # Preload all the RegisteredExtension objects
        registered_extensions = {}
        for registered_ext in RegisteredExtension.objects.all():
            registered_extensions[registered_ext.class_name] = registered_ext

        for entrypoint in pkg_resources.iter_entry_points(self.key):
            try:
                ext_class = entrypoint.load()
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

            if class_name in registered_extensions:
                registered_ext = registered_extensions[class_name]
            else:
                try:
                    registered_ext = RegisteredExtension(
                        class_name=class_name,
                        name=entrypoint.dist.project_name
                    )
                    registered_ext.save()
                except RegisteredExtension.DoesNotExist:
                    registered_ext = RegisteredExtension.objects.get(
                        class_name=class_name)

            ext_class.registration = registered_ext

            if registered_ext.enabled:
                self.__init_extension(ext_class)

    def __init_extension(self, ext_class):
        extension = ext_class()
        extension.extension_manager = self
        self._extension_instances[extension.id] = extension
        extension.info.enabled = True
        return extension

    def __uninit_extension(self, extension):
        extension.shutdown()
        extension.info.enabled = False
        del self._extension_instances[extension.id]

    def __install_extension(self, ext_class):
        """
        Performs any installation necessary for an extension.
        This will install the contents of htdocs into the
        EXTENSIONS_MEDIA_ROOT directory.
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


def get_extension_managers():
    return _extension_managers
