"""Extension models."""

from django.db import models

from djblets.db.fields import JSONField
from djblets.extensions.errors import InvalidExtensionError


class RegisteredExtension(models.Model):
    """Extension registration info.

    An extension that was both installed and enabled at least once. This
    may contain settings for the extension.

    This does not contain full information for the extension, such as the
    author or description. That is provided by the Extension object itself.
    """
    class_name = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=32)
    enabled = models.BooleanField(default=False)
    installed = models.BooleanField(default=False)
    settings = JSONField()

    def __str__(self):
        return self.name

    def get_extension_class(self):
        """Retrieves the python object for the extensions class."""
        if not hasattr(self, '_extension_class'):
            cls = None

            try:
                # Import the function here to avoid a mutual
                # dependency.
                from djblets.extensions.manager import get_extension_managers

                for manager in get_extension_managers():
                    try:
                        cls = manager.get_installed_extension(self.class_name)
                        break
                    except InvalidExtensionError:
                        continue
            except Exception:
                return None

            self._extension_class = cls

        return self._extension_class

    extension_class = property(get_extension_class)

    class Meta:
        # Djblets 0.9+ sets an app label of "djblets_extensions" on
        # Django 1.7+, which would affect the table name. We need to retain
        # the old name for backwards-compatibility.
        db_table = 'extensions_registeredextension'
