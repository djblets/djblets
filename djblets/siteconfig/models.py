"""Database models for storing site configuration."""

from __future__ import unicode_literals

from django.contrib.sites.models import Site
from django.db import models
from django.utils import six
from django.utils.encoding import python_2_unicode_compatible

from djblets.cache.synchronizer import GenerationSynchronizer
from djblets.db.fields import JSONField
from djblets.siteconfig.managers import SiteConfigurationManager


_GLOBAL_DEFAULTS = {}
_DEFAULTS = {}


class SiteConfigSettingsWrapper(object):
    """Wraps the settings for a SiteConfiguration.

    This is used by the context processor for templates to wrap accessing
    settings data, properly returning defaults.
    """

    def __init__(self, siteconfig):
        """Initialize the wrapper.

        Args:
            siteconfig (SiteConfiguration):
                The site configuration to wrap.
        """
        self.siteconfig = siteconfig

    def __getattr__(self, name):
        """Return an attribute from the site configuration.

        If the attribute is not present in the site configuration's settings,
        the registered default will be returned.

        Args:
            name (unicode):
                The name of the attribute.

        Returns:
            unicode:
            The resulting value from the site configuration or the default.
        """
        return self.siteconfig.get(name)


@python_2_unicode_compatible
class SiteConfiguration(models.Model):
    """Stored version and settings data for a Django site.

    This stores dynamic settings for a site, along with version information,
    allowing the application to alter and apply/synchronize settings across
    threads, processes, and servers without restarting the server.

    Consumers should not create or fetch their own instance of this class
    through standard Django query functions. Instead, they should use
    :py:meth:`SiteConfiguration.objects.get_current()
    <djblets.siteconfig.managers.SiteConfigurationManager.get_current>`
    instead. See the documentation for that method for details on how to safely
    look up and use site configuration.
    """

    site = models.ForeignKey(Site,
                             related_name='config',
                             on_delete=models.CASCADE)
    version = models.CharField(max_length=20)

    #: A JSON dictionary field of settings stored for a site.
    settings = JSONField()

    objects = SiteConfigurationManager()

    @classmethod
    def add_global_defaults(cls, defaults_dict):
        """Add a dictionary of global defaults for settings.

        These defaults will be used when calling :py:meth:`get` for any setting
        not stored. Defaults registered for a specific site configuration take
        precedent over global defaults.

        Args:
            default_dict (dict):
                A dictionary of defaults, mapping siteconfig settings keys to
                JSON-serializable values.
        """
        _GLOBAL_DEFAULTS.update(defaults_dict)

    @classmethod
    def add_global_default(cls, key, default_value):
        """Add a global default value for a settings key.

        The default will be used when calling :py:meth:`get` for this key,
        if a value is not stored. Defaults registered for a specific site
        configuration take precedent over global defaults.

        Args:
            key (unicode):
                The settings key to set the default for.

            default_value (object):
                The value to set as the default.
        """
        cls.add_global_defaults({key: default_value})

    @classmethod
    def remove_global_default(self, key):
        """Remove a global default value for a settings key.

        Args:
            key (unicode):
                The settings key to remove the default for.
        """
        _GLOBAL_DEFAULTS.pop(key)

    @classmethod
    def clear_global_defaults(self):
        """Clear all default values for this site configuration.

        This will clear only global defaults. This will not affect defaults
        registered on specific site configurations.
        """
        _GLOBAL_DEFAULTS.clear()

    @classmethod
    def get_global_defaults(cls):
        """Return all global defaults for settings.

        Returns:
            dict:
            A dictionary of all registered global defaults for settings.
        """
        return _GLOBAL_DEFAULTS

    def __init__(self, *args, **kwargs):
        """Initialize the site configuration.

        Args:
            *args (tuple):
                Positional arguments to pass to the parent constructor.

            **kwargs (dict):
                Keyword arguments to pass to the parent constructor.
        """
        super(SiteConfiguration, self).__init__(*args, **kwargs)

        # Optimistically try to set the Site to the current site instance,
        # which either is cached now or soon will be. That way, we avoid
        # a lookup on the relation later.
        cur_site = Site.objects.get_current()

        if cur_site.pk == self.site_id:
            self.site = cur_site

        # Begin managing the synchronization of settings between all
        # SiteConfigurations.
        self._gen_sync = GenerationSynchronizer(
            '%s:siteconfig:%s:generation' % (self.site.domain, self.pk))

        self.settings_wrapper = SiteConfigSettingsWrapper(self)

    def get(self, key, default=None):
        """Return the value for a setting.

        If the setting is not found, the default value will be returned. This
        is represented by the default parameter, if passed in, or a global
        default (from :py:meth:`add_default`) if set.

        If no default is available, ``None`` will be returned.

        Args:
            key (unicode):
                The site configuration settings key.

            default (object, optional):
                The default value to return. If not provided, the registered
                default will be returned.

        Returns:
            object:
            The resulting value.
        """
        if default is None:
            try:
                default = _DEFAULTS[self.pk][key]
            except KeyError:
                default = _GLOBAL_DEFAULTS.get(key)

        return self.settings.get(key, default)

    def set(self, key, value):
        """Set a value for a setting.

        The setting will be stored locally until the model is saved, at which
        point it will be synchronized with other processes/servers.

        Args:
            key (unicode):
                The key for the setting.

            value (object):
                The JSON-serializable object to store.
        """
        self.settings[key] = value

    def add_defaults(self, defaults_dict):
        """Add a dictionary of defaults for settings.

        These defaults will be used when calling :py:meth:`get` for any setting
        not stored.  These will only be registered for this site configuration,
        and will not be registered for global defaults.

        Args:
            default_dict (dict):
                A dictionary of defaults, mapping siteconfig settings keys to
                JSON-serializable values.
        """
        _DEFAULTS.setdefault(self.pk, {}).update(defaults_dict)

    def add_default(self, key, default_value):
        """Add a default value for a settings key.

        The default will be used when calling :py:meth:`get` for this key,
        if a value is not stored. This will only be registered for this site
        configuration, and will not be registered for global defaults.

        Args:
            key (unicode):
                The settings key to set the default for.

            default_value (object):
                The value to set as the default.
        """
        self.add_defaults({key: default_value})

    def remove_default(self, key):
        """Remove a default value on this site configuration.

        This will remove only defaults registered on this site configuration.
        This does not affect global defaults.

        Args:
            key (unicode):
                The settings key to remove the default for.
        """
        try:
            del _DEFAULTS[self.pk][key]
        except KeyError:
            pass

    def clear_defaults(self):
        """Clear all default values for this site configuration.

        This will clear only defaults registered on this site configuration.
        This does not affect global defaults.
        """
        _DEFAULTS[self.pk] = {}

    def get_defaults(self):
        """Return all defaults for this site configuration.

        This will return only defaults registered on this site configuration.
        The result does not include global defaults.

        Returns:
            dict:
            A dictionary of all registered defaults for settings.
        """
        return _DEFAULTS.get(self.pk, {})

    def is_expired(self):
        """Return whether or not this SiteConfiguration is expired.

        If the configuration is expired, it will need to be reloaded before
        accessing any settings.

        Returns:
            bool:
            Whether or not the current state is expired.
        """
        return self._gen_sync.is_expired()

    def save(self, clear_caches=True, **kwargs):
        """Save the site configuration to the database.

        By default, saving will clear the caches across all processes/servers
        using this site configuration, causing them to be re-fetched on the
        next request.

        Args:
            clear_caches (bool, optional):
                Whether to clear the caches. This is ``True`` by default.

            **kwargs (dict):
                Additional keyword arguments to pass to the parent method.
        """
        self._gen_sync.mark_updated()

        if clear_caches:
            # The cached siteconfig might be stale now. We'll want a refresh.
            # Also refresh the Site cache, since callers may get this from
            # Site.config.
            SiteConfiguration.objects.clear_cache()
            Site.objects.clear_cache()

        super(SiteConfiguration, self).save(**kwargs)

    def __str__(self):
        """Return a string version of the site configuration.

        The returned string will list the associated site's domain and the
        stored application version.

        Returns:
            unicode:
            The string representation of the site configuration.
        """
        return "%s (version %s)" % (six.text_type(self.site), self.version)

    class Meta:
        # Djblets 0.9+ sets an app label of "djblets_siteconfig" on
        # Django 1.7+, which would affect the table name. We need to retain
        # the old name for backwards-compatibility.
        db_table = 'siteconfig_siteconfiguration'
