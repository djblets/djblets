"""Database models for integration configuration."""

from __future__ import unicode_literals

from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from djblets.db.fields import JSONField
from djblets.integrations.mixins import NeedsIntegrationManagerMixin


@python_2_unicode_compatible
class BaseIntegrationConfig(NeedsIntegrationManagerMixin, models.Model):
    """Base class for stored configuration for a particular integration.

    This contains configuration settings for a given instance of an
    integration, along with state indicating if that integration is to be
    enabled and user-specified identifying information.

    This is meant to be subclassed, in order to provide additional state
    that may be needed by an application.
    """

    integration_id = models.CharField(max_length=255, db_index=True)
    time_added = models.DateTimeField(default=timezone.now)
    last_updated = models.DateTimeField(default=timezone.now)
    name = models.CharField(max_length=255, blank=True, null=True)
    enabled = models.BooleanField(default=False, db_index=True)
    settings = JSONField(default={})
    extra_data = JSONField(default={})

    @property
    def integration(self):
        """The integration for the configuration."""
        return self.get_integration_manager().get_integration(
            self.integration_id)

    def get(self, key, default=None):
        """Return the setting for a given key.

        This will return the setting's stored value, or its default value for
        the integration if unset in these settings. If the setting isn't set
        in either place, the provided default will be returned instead.

        Args:
            key (unicode):
                The settings key.

            default (object):
                The default value, if not available elsewhere.

        Returns:
            The resulting value from settings, or the default value if not
            found.
        """
        try:
            return self.settings[key]
        except KeyError:
            return self.integration.default_settings.get(key, default)

    def set(self, key, value):
        """Set a value for the given settings key.

        This is equivalent to setting the value through the standard dictionary
        operators.

        Args:
            key (unicode):
                The key to set.

            value (object):
                The settings value.
        """
        self.settings[key] = value

    def __str__(self):
        """Return a string representation of this configuration.

        Returns:
            unicode:
            The string representation.
        """
        try:
            integration_name = self.integration.name
        except Exception:
            integration_name = self.integration_id

        return _('%(config_name)s (%(integration_name)s)') % {
            'config_name': self.name,
            'integration_name': integration_name,
        }

    class Meta:
        abstract = True
        verbose_name = _('Integration configuration')
        verbose_name_plural = _('Integration configurations')
