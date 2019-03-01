from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _

from djblets.forms.forms import KeyValueForm


class IntegrationConfigForm(KeyValueForm):
    """Base class for an integration settings form.

    This makes it easy to provide a basic form for manipulating the settings
    of an integration configuration. It takes care of loading/saving the
    values and prompting the user for a name.

    Integrations should subclass this and provide additional fields that they
    want to display to the user. They must provide a :py:class:`Meta` class
    containing the fieldsets they want to display.

    Applications can subclass this to provide additional special fields that
    should be made available to integrations. Integrations would then need
    to subclass that specialized form. Applications that want to do this will
    likely need to modify :py:attr:`model_fields`.
    """

    #: A list of fields on the model that should not be saved in settings.
    model_fields = ('name', 'enabled')

    #: The fieldset containing basic information on the configuration.
    #:
    #: Subclasses can override this to provide additional fields, styling, or
    #: a description.
    basic_info_fieldset = (None, {
        'fields': ('name', 'enabled'),
        'description': _(
            'Start by giving this configuration a name so you can easily '
            'identify it later. You can also mark this configuration as '
            'enabled or disabled.'
        ),
    })

    enabled = forms.BooleanField(
        label=_('Enable this integration'),
        initial=True,
        required=False)

    name = forms.CharField(
        label=_('Name'),
        required=True,
        widget=forms.widgets.TextInput(attrs={
            'size': 40,
        }))

    def __init__(self, integration, request, *args, **kwargs):
        """Initialize the form.

        Args:
            integration (djblets.integrations.integration.Integration):
                The integration being configured.

            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple):
                Positional arguments to pass to the form.

            **kwargs (dict):
                Keyword arguments to pass to the form.
        """
        self.integration = integration
        self.request = request

        self.build_fieldsets()

        super(IntegrationConfigForm, self).__init__(*args, **kwargs)

    @classmethod
    def build_fieldsets(cls):
        """Build the fieldsets used for the configuration form.

        By default, this will prepend :py:attr:`basic_info_fieldset` to
        the existing list of fieldsets on :py:class:`Meta` (if any).

        Subclasses can override this to provide more specialized
        customization of the form. Since this is working on a form class
        and not an instance, they should be careful to apply changes only
        once.
        """
        meta = getattr(cls, 'Meta', None)

        if meta:
            # Patch the list of fieldsets to contain the standard fieldset
            # for naming and enabling the configuration.
            fieldsets = getattr(meta, 'fieldsets', ())

            if not fieldsets or fieldsets[0] != cls.basic_info_fieldset:
                meta.fieldsets = (cls.basic_info_fieldset,) + fieldsets

    @property
    def config(self):
        """The configuration that's being edited.

        If this is a brand new configuration, this will be ``None`` until
        saved.

        Any value will be an instance of the subclass of
        :py:class:`~djblets.integrations.models.BaseIntegrationConfig` provided
        by the application supporting integrations.
        """
        return self.instance

    def get_key_value(self, key, default=None):
        """Return the value for a key.

        This will first look for the value from the
        :py:class:`~djblets.integrations.models.BaseIntegrationConfig`, and
        will then fall back to looking for the value in the configuration's
        :py:attr:`~djblets.integrations.models.BaseIntegrationConfig.settings`
        field.

        This is used internally by the parent class, and is not meant to be
        used directly.

        Args:
            key (unicode):
                The key in the configuration.

            default (object):
                The default value for the key, if not found.

        Returns:
            The value from the configuration.
        """
        if key in self.model_fields:
            return getattr(self.instance, key)
        else:
            return self.instance.get(key, default)

    def set_key_value(self, key, value):
        """Set the value for a key.

        This will first look for the key to set in the
        :py:class:`~djblets.integrations.models.BaseIntegrationConfig`. If
        it's there, that field's value will be set. Otherwise, it will fall
        back to setting the key in the configuration's
        :py:attr:`~djblets.integrations.models.BaseIntegrationConfig.settings`
        field.

        This is used internally by the parent class, and is not meant to be
        used directly.

        Args:
            key (unicode):
                The key in the configuration.

            value (object):
                The new value.
        """
        if key in self.model_fields:
            setattr(self.instance, key, value)
        else:
            self.instance.set(key, value)

    def create_instance(self):
        """Create an instance of a configuration.

        This is used internally by the parent class, and is not meant to be
        called by consumers of the form.

        Returns:
            djblets.integrations.models.BaseIntegrationConfig:
            A new integration configuration.
        """
        return self.integration.create_config()

    def save_instance(self):
        """Save the configuration.

        This is used internally by the parent class, and is not meant to be
        called by consumers of the form.
        """
        self.instance.integration_id = self.integration.integration_id
        self.instance.save()
