"""Forms for Djblets' avatar support."""

from __future__ import unicode_literals

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from djblets.avatars.errors import AvatarServiceNotFoundError
from djblets.configforms.forms import ConfigPageForm
from djblets.registries.errors import ItemLookupError


class AvatarServiceConfigForm(ConfigPageForm):
    """An avatar service configuration form."""

    js_view_class = 'Djblets.Avatars.ServiceSettingsFormView'
    template_name = 'avatars/service_form.html'

    #: The avatar service ID of the associated service.
    avatar_service_id = None

    def __init__(self, *args, **kwargs):
        """Initialize the configuration form.

        Args:
            *args (tuple):
                Additional positional arguments for the superclass constructor.

            **kwargs (dict):
                Additional keyword arguments for the superclass constructor.

        Keyword Args:
            configuration (dict):
                The current configuration

            service (djblets.avatars.services.base.AvatarService):
                The avatar service instance that instantiated this form.
        """
        self.configuration = kwargs.pop('configuration')
        self.service = kwargs.pop('service')

        super(AvatarServiceConfigForm, self).__init__(*args, **kwargs)
        self.fields.pop('form_target')

    def get_extra_context(self):
        """Return extra rendering context.

        Returns:
            dict:
            Extra rendering context.
        """
        return {
            'avatar_service_id': self.avatar_service_id,
            'configuration': self.configuration,
        }


class AvatarSettingsForm(ConfigPageForm):
    """The avatar settings form.

    This allows users to select the avatar service they wish to use and, if
    necessary, configure it (e.g., by uploading an avatar).
    """

    form_id = 'avatar'
    form_title = _('Avatar')

    js_view_class = 'Djblets.Avatars.SettingsFormView'
    js_model_class = 'Djblets.Avatars.Settings'
    template_name = 'avatars/settings_form.html'

    #: The avatar service registry. Subclasses must override this.
    avatar_service_registry = None

    avatar_service_id = forms.ChoiceField(
        label=_('Avatar Service'),
        required=True)

    @property
    def is_multipart(self):
        """Whether or not the form is multi-part.

        The form is multi-part when there is an enabled avatar service that has
        a multi-part configuration form.

        Returns:
            bool:
            Whether or not the form is multi-part.
        """
        for service in self.avatar_service_registry.configurable_services:
            if service.config_form_class.is_multipart:
                return True

        return False

    @property
    def js_bundle_names(self):
        """Yield the bundle names necessary.

        Each avatar service can specify a configuration form that may
        specify JS bundles. Since those forms are not registered through the
        page, we must add them this way.

        Yields:
            unicode: The names of the JS bundles to load on the page.
        """
        yield 'djblets-utils'
        yield 'djblets-avatars-config'

        for service in self.avatar_service_registry.configurable_services:
            for bundle in service.config_form_class.js_bundle_names:
                yield bundle

    @property
    def css_bundle_names(self):
        """Yield the CSS bundle names.

        Each avatar service can specify a configuration form that may
        specify CSS bundles. Since those forms are not registered through the
        page, we must add them this way.

        Yields:
            unicode: The names of the CSS bundles to load on the page.
        """
        yield 'djblets-avatars-config'

        for service in self.avatar_service_registry.configurable_services:
            for bundle in service.config_form_class.css_bundle_names:
                yield bundle

    def __init__(self, *args, **kwargs):
        """Initialize the form.

        Args:
            *args (tuple):
                Additional Positional arguments.

            **kwargs (dict):
                Additional keyword arguments.
        """
        super(AvatarSettingsForm, self).__init__(*args, **kwargs)

        self.settings_manager = \
            self.avatar_service_registry.settings_manager_class(self.user)

        avatar_service_id = self.fields['avatar_service_id']
        avatar_service_id.choices = [
            (service.avatar_service_id, service.name)
            for service in self.avatar_service_registry.enabled_services
            if not service.hidden
        ]
        avatar_service = self.avatar_service_registry.for_user(self.user)

        if avatar_service:
            avatar_service_id.initial = avatar_service.avatar_service_id

        if self.request.method == 'POST':
            kwargs['files'] = self.request.FILES

        self.avatar_service_forms = {
            service.avatar_service_id: service.get_configuration_form(
                self.user, *args, **kwargs)
            for service in self.avatar_service_registry.configurable_services
        }

    def clean_avatar_service_id(self):
        """Clean the avatar_service_id field.

        This ensures that the value corresponds to a valid and enabled
        avatar service.

        Returns:
            unicode:
            The avatar service ID.

        Raises:
            django.core.exceptions.ValidationError:
                Raised when the avatar service ID is invalid.
        """
        avatar_service_id = self.cleaned_data['avatar_service_id']

        try:
            avatar_service = self.avatar_service_registry.get(
                'avatar_service_id', avatar_service_id)
        except AvatarServiceNotFoundError:
            avatar_service = None
        else:
            if not self.avatar_service_registry.is_enabled(avatar_service):
                avatar_service = None

        if avatar_service is None or avatar_service.hidden:
            raise ValidationError(_('Invalid service ID'))

        return avatar_service_id

    def clean(self):
        """Clean the form.

        This will clean the avatar service configuration form of the selected
        avatar service (if it is configurable) and raise an exception if it is
        not valid.

        This will cache any sub-form errors so that they can be rendered to the
        user when rendering the form.

        Returns:
            dict:
            The form's cleaned data.

        Raises:
            ValidationError:
                Raised when the form for the selected avatar service is
                invalid.
        """
        super(AvatarSettingsForm, self).clean()

        avatar_service_id = self.cleaned_data['avatar_service_id']
        avatar_service = self.avatar_service_registry.get_avatar_service(
            avatar_service_id)

        if avatar_service.is_configurable():
            avatar_service_form = self.avatar_service_forms[avatar_service_id]

            if not avatar_service_form.is_valid():
                raise ValidationError(_('The avatar service is improperly '
                                        'configured.'))

        return self.cleaned_data

    def save(self):
        """Save the avatar settings.

        This method attempts to save
        """
        try:
            old_avatar_service = (
                self.avatar_service_registry
                .get_avatar_service(
                    self.settings_manager.avatar_service_id)
            )
        except ItemLookupError:
            old_avatar_service = None

        if old_avatar_service and old_avatar_service.is_configurable():
            old_avatar_service.cleanup(self.user)
            self.settings_manager.configuration.pop(
                old_avatar_service.avatar_service_id)

        avatar_service_id = self.cleaned_data['avatar_service_id']
        new_avatar_service = (
            self.avatar_service_registry
            .get_avatar_service(avatar_service_id)
        )
        self.settings_manager.avatar_service_id = avatar_service_id

        if new_avatar_service.is_configurable():
            avatar_service_form = self.avatar_service_forms[avatar_service_id]
            self.settings_manager.configuration[avatar_service_id] = \
                avatar_service_form.save()

        self.settings_manager.save()

    def get_extra_context(self):
        """Return the extra context for rendering the form.

        Returns:
            dict:
            The extra rendering context.
        """
        service = self.avatar_service_registry.for_user(self.user)

        return {
            'current_avatar_service': service,
            'avatar_services': self.avatar_service_registry.enabled_services,
        }

    def get_js_model_data(self):
        """Return the JS model data for the form.

        Returns:
            dict:
            A dictionary of the model data for the form.
        """
        service = self.avatar_service_registry.for_user(
            self.user,
            allow_consent_checks=False)

        return {
            'configuration': self.settings_manager.configuration,
            'serviceID': service.avatar_service_id,
            'services': {
                service.avatar_service_id: {
                    'isConfigurable': service.is_configurable(),
                }
                for service in self.avatar_service_registry.enabled_services
            },
        }
