from django.db import models

from djblets.util.fields import JSONField


class RegisteredExtension(models.Model):
    """
    An extension that was both installed and enabled at least once. This
    may contain settings for the extension.

    This does not contain full information for the extension, such as the
    author or description. That is provided by the Extension object itself.
    """
    class_name = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=32)
    enabled = models.BooleanField(default=False)
    settings = JSONField()

    def __unicode__(self):
        return self.name
