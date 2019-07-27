"""Forms, fields, and widgets for gathering and displaying consent."""

from __future__ import unicode_literals

from django import forms
from django.contrib import messages
from django.forms.widgets import MultiWidget, Widget
from django.utils import timezone
from django.utils.html import format_html_join
from django.utils.translation import ugettext_lazy as _

from djblets.privacy.consent import (Consent,
                                     get_consent_requirements_registry,
                                     get_consent_tracker)
from djblets.util.compat.django.template.loader import render_to_string


class ConsentRequirementWidget(Widget):
    """A widget for displaying and gathering consent information.

    This presents the consent requirement in an easy-to-digest form, and
    makes it easy for users to choose to allow or block the thing requiring
    consent.

    This is meant to be used with :py:class:`ConsentRequirementField`.
    """

    def __init__(self, consent_requirement=None, attrs=None):
        """Initialize the widget.

        Args:
            consent_requirement (djblets.privacy.consent.base.
                                 ConsentRequirement, optional):
                The consent requirement information. If not provided, this
                must be directly set on the instance before rendering the
                widget.

            attrs (dict, optional):
                HTML attributes for the widget. This is used only to set an
                ``id`` attribute for the field.
        """
        super(ConsentRequirementWidget, self).__init__(attrs=attrs)

        self.consent_requirement = consent_requirement

    def render(self, name, value, attrs=None):
        """Render the widget.

        Args:
            name (unicode):
                The base name used for the ``<input>`` elements. Specific
                names will be composed from this.

            value (unicode):
                The current value for the field.

            attrs (dict, optional):
                HTML attributes for the widget. This is used only to set an
                ``id`` attribute for the field.

        Returns:
            django.utils.safestring.SafeText:
            The rendered HTML for the widget.
        """
        if attrs is None:
            attrs = {}

        return render_to_string(
            'privacy/consent/consent_widget.html',
            context={
                'ALLOW': ConsentRequirementField.ALLOW,
                'BLOCK': ConsentRequirementField.BLOCK,
                'consent_requirement': self.consent_requirement,
                'icons': self.consent_requirement.icons,
                'id': attrs.get('id', ''),
                'name': name,
                'value': value,
            })

    def value_from_datadict(self, data, files, name):
        """Return the field value from the submitted form data.

        Args:
            data (dict):
                The submitted form data.

            files (dict, unused):
                The submitted files data.

            name (unicode):
                The base name for the form fields.

        Returns:
            unicode:
            A value for the fields. This will be one of
            :py:attr:`ConsentRequirementField.ALLOW`,
            :py:attr:`ConsentRequirementField.BLOCK`, or ``None``.
        """
        return data.get('%s_choice' % name)


class MultiConsentRequirementsWidget(MultiWidget):
    """A widget for displaying and gathering multiple consent information.

    This adds a :py:class:`ConsentRequirementWidget` for each consent
    requirement provided to the widget.

    This is meant to be used with :py:class:`MultiConsentRequirementsField`.
    """

    def __init__(self, consent_requirements, attrs=None):
        """Initialize the widget.

        Args:
            consent_requirements (list of djblets.privacy.consent.base.
                                  ConsentRequirement):
                The list of consent requirements.

            attrs (dict, optional):
                HTML attributes for the widget. This is used only to set an
                ``id`` attribute for the field.
        """
        self.consent_requirements = consent_requirements

        super(MultiConsentRequirementsWidget, self).__init__(
            widgets=[
                ConsentRequirementWidget(consent_requirement=requirement)
                for requirement in consent_requirements
            ],
            attrs=attrs)

    def render(self, name, value, attrs=None):
        """Render the widget.

        Args:
            name (unicode):
                The base name used for the ``<input>`` elements. Specific
                names will be composed from this.

            value (list of unicode):
                The current values for the fields.

            attrs (dict, optional):
                HTML attributes for the widget. This is used only to set a
                base ``id`` attribute for the fields.

        Returns:
            django.utils.safestring.SafeText:
            The rendered HTML for the widget.
        """
        if not isinstance(value, list):
            value = self.decompress(value)

        final_attrs = self.build_attrs(attrs)
        field_id = final_attrs.get('id')
        output = []

        for i, widget in enumerate(self.widgets):
            consent_requirement = widget.consent_requirement
            requirement_id = consent_requirement.requirement_id

            try:
                widget_value = value[i]
            except IndexError:
                widget_value = None

            if field_id:
                final_attrs = dict(final_attrs,
                                   id='%s_%s' % (field_id, requirement_id))

            rendered = widget.render('%s_%s' % (name, requirement_id),
                                     widget_value, final_attrs)
            output.append((rendered,))

        return format_html_join('', '{0}', output)

    def value_from_datadict(self, data, files, name):
        """Return the field values from the submitted form data.

        Args:
            data (dict):
                The submitted form data.

            files (dict, unused):
                The submitted files data.

            name (unicode):
                The base name for the form fields.

        Returns:
            list of unicode:
            A list of values for all the fields, in the order of the list of
            consent requirements provided to the widget. Each item will be
            one of :py:attr:`ConsentRequirementField.ALLOW`,
            :py:attr:`ConsentRequirementField.BLOCK`, or ``None``.
        """
        return [
            widget.value_from_datadict(
                data,
                files,
                '%s_%s' % (name, widget.consent_requirement.requirement_id))
            for widget in self.widgets
        ]

    def decompress(self, value):
        """Decompress a list of values for the widget.

        This is required by the parent class, and is responsible for taking the
        provided data and returning a list of values that can be used for the
        sub-widgets.

        Args:
            value (list):
                The list of values (or ``None``) to normalize and return.

        Returns:
            list of unicode:
            The resulting list of values. This may be empty.
        """
        return value or []


class ConsentRequirementField(forms.ChoiceField):
    """A form field for displaying and gathering consent information.

    This presents the consent requirement in an easy-to-digest form, and
    makes it easy for users to choose to allow or block the thing requiring
    consent.

    The cleaned result from this field is a
    :py:class:`~djblets.privacy.consent.base.ConsentData` instance, which
    can be recorded directly in the tracker.
    """

    ALLOW = 'allow'
    BLOCK = 'block'

    CHOICES = (
        (ALLOW, _('Allow')),
        (BLOCK, _('Block')),
    )

    widget = ConsentRequirementWidget

    default_error_messages = {
        'required': _('You must choose Allow or Block to continue.'),
    }

    def __init__(self, consent_requirement, user=None, consent_source=None,
                 extra_consent_data=None, **kwargs):
        """Initialize the field.

        Args:
            consent_requirement (djblets.privacy.consent.base.
                                 ConsentRequirement):
                The consent requirement information.

            user (django.contrib.auth.models.User, optional):
                The user viewing the form. If provided, the default value
                for the field will be based on the choice already made by
                the user, if any.

            consent_source (unicode, optional):
                The source to record in the consent audit trail for the
                consent choice saved in this field.

            extra_consent_data (dict, optional):
                Extra information to record in the consent audit trail for
                the consent choice saved in this field.

            **kwargs (dict):
                Additional keyword arguments to pass to the parent class.
        """
        super(ConsentRequirementField, self).__init__(
            choices=self.CHOICES,
            label='',
            required=True,
            **kwargs)

        self.consent_requirement = consent_requirement
        self.consent_source = consent_source
        self.extra_consent_data = extra_consent_data
        self.widget.consent_requirement = consent_requirement

        if user and user.is_authenticated():
            self.set_initial_from_user(user)

    def set_initial_from_user(self, user):
        """Set the initial state of the field based on a user's prior consent.

        This is called automatically if passing a user to the constructor.
        Otherwise, it should be called manually when setting up a form.

        Args:
            user (django.contrib.auth.models.User):
                The user viewing the form.
        """
        assert user
        assert user.is_authenticated()

        self.initial = self.consent_requirement.get_consent(user)

    def prepare_value(self, value):
        """Prepare a value for use in the field.

        This will convert a :py:class:`~djblets.privacy.consent.base.Consent`
        value to a value suitable for use in the field.

        Args:
            value (djblets.privacy.consent.base.Consent):
                The value to convert.

        Returns:
            unicode:
            A valid value for use in the field.
        """
        return {
            Consent.GRANTED: self.ALLOW,
            Consent.DENIED: self.BLOCK,
        }.get(value)

    def clean(self, value):
        """Clean and return a value from submitted form data.

        Args:
            value (unicode):
                A value submitted by the client.

        Returns:
            djblets.privacy.consent.base.ConsentData:
            The cleaned consent data value, or ``None`` if a suitable value was
            not provided.
        """
        value = super(ConsentRequirementField, self).clean(value)

        # Validators should have already caught this.
        assert value in (self.ALLOW, self.BLOCK)

        return self.consent_requirement.build_consent_data(
            source=self.consent_source,
            extra_data=self.extra_consent_data,
            granted=(value == self.ALLOW))


class MultiConsentRequirementsField(forms.MultiValueField):
    """A form field for displaying and gathering mulltiple consent information.

    This provides a :py:class:`ConsentRequirementField` for each consent
    requirement provided to the field (or all registered ones if an explicit
    list was not provided). It's handy for forms that offer all consent choices
    to the user.

    The cleaned result from this field is a list of
    :py:class:`~djblets.privacy.consent.base.ConsentData` instances, which
    can be recorded directly in the tracker.
    """

    default_error_messages = {
        'required': _('You must choose Allow or Block for all options to '
                      'continue.'),
    }

    widget = MultiConsentRequirementsWidget

    def __init__(self, consent_requirements=None, user=None,
                 consent_source=None, extra_consent_data=None,
                 *args, **kwargs):
        """Initialize the field.

        Args:
            consent_requirements (list of djblets.privacy.consent.base.
                                  ConsentRequirement, optional):
                The list of consent requirements to display. If not provided,
                all registered consent requirements will be used.

            user (django.contrib.auth.models.User, optional):
                The user viewing the form. If provided, the default options
                for each field will be based on the choices already made by
                the user.

            consent_source (unicode, optional):
                The source to record in the consent audit trail for anything
                saved in this field.

            extra_consent_data (dict, optional):
                Extra information to record in the consent audit trail for
                anything saved in this field.

            *args (tuple):
                Additional positional arguments to pass to the parent class.

            **kwargs (dict):
                Additional keyword arguments to pass to the parent class.
        """
        self.consent_requirements = (consent_requirements or
                                     list(get_consent_requirements_registry()))

        super(MultiConsentRequirementsField, self).__init__(
            fields=[
                ConsentRequirementField(consent_requirement,
                                        consent_source=consent_source,
                                        extra_consent_data=extra_consent_data)
                for consent_requirement in self.consent_requirements
            ],
            widget=self.widget(self.consent_requirements),
            *args, **kwargs)

        if user and user.is_authenticated():
            self.set_initial_from_user(user)

    def set_initial_from_user(self, user):
        """Set the initial state of the field based on a user's prior consent.

        This is called automatically if passing a user to the constructor.
        Otherwise, it should be called manually when setting up a form.

        Args:
            user (django.contrib.auth.models.User):
                The user viewing the form.
        """
        assert user
        assert user.is_authenticated()

        self.initial = [
            field.consent_requirement.get_consent(user)
            for field in self.fields
        ]

    def prepare_value(self, value):
        """Prepare a value for use in the field.

        This will convert a list of
        :py:class:`~djblets.privacy.consent.base.Consent` values given in the
        order of the field's list of requirements to values suitable for use
        in the field.

        Args:
            value (list of list djblets.privacy.consent.base.Consent):
                The list of values to convert.

        Returns:
            list of unicode:
            A list of values suitable for use in the field.
        """
        return [
            field.prepare_value(value[i])
            for i, field in enumerate(self.fields)
        ]

    def clean(self, value):
        """Clean and return values from submitted form data.

        Args:
            value (list of unicode):
                A list of values submitted by the client.

        Returns:
            list of djblets.privacy.consent.base.ConsentData:
            The list of cleaned consent data values.
        """
        consent_data_list = \
            super(MultiConsentRequirementsField, self).clean(value)

        # Set the timestamp to the same value on each entry.
        now = timezone.now()

        for consent_data in consent_data_list:
            consent_data.timestamp = now

        return consent_data_list

    def compress(self, data_list):
        """Compress cleaned values for the field.

        This is required by the parent class, and is responsible for taking a
        list of cleaned values and returning something that can be validated
        and returned. This implementation returns the data as-is.

        Args:
            data_list (list of djblets.privacy.consent.base.ConsentData):
                The list of cleaned data.

        Returns:
            list of djblets.privacy.consent.base.ConsentData:
            The list of data.
        """
        return data_list


class ConsentFormMixin(object):
    """A mixin for forms that present registered consent requirements.

    This can be mixed into a form to provide consent field initialization and
    saving.
    """

    #: The name of the consent field.
    consent_field_name = 'consent'

    def __init__(self, *args, **kwargs):
        """Initialize the form.

        Args:
            *args (tuple):
                Positional arguments passed to the form.

            **kwargs (dict):
                Keyword arguments passed to the form.
        """
        super(ConsentFormMixin, self).__init__(*args, **kwargs)

        self.fields[self.consent_field_name] = \
            MultiConsentRequirementsField(
                label='',
                user=self.get_consent_user(),
                consent_source=self.get_consent_source(),
                extra_consent_data=self.get_extra_consent_data())

    def get_consent_user(self):
        """Return the user deciding on consent.

        This must be implemented by subclasses.

        Returns:
            django.contrib.auth.models.User:
            The user deciding on consent.
        """
        raise NotImplementedError

    def get_consent_source(self):
        """Return a source to record in the consent audit trail.

        This must be implemented by subclasses.

        Returns:
            unicode:
            The source to record for each consent entry.
        """
        raise NotImplementedError

    def get_extra_consent_data(self):
        """Return extra data to record in the consent audit trail.

        By default, this just returns an empty dictionary.

        Returns:
            dict:
            Extra data to record for each consent entry.
        """
        return {}

    def save_consent(self, user):
        """Save the consent information recorded in the form.

        Args:
            user (django.contrib.auth.models.User):
                The user who made the consent decisions.
        """
        assert self.is_valid()
        assert user
        assert user.is_authenticated()

        get_consent_tracker().record_consent_data_list(
            user,
            self.cleaned_data[self.consent_field_name])


class ConsentConfigPageFormMixin(ConsentFormMixin):
    """A mixin for config forms that present registered consent requirements.

    This can be mixed into a config form to provide consent field
    initialization and saving. It would be used instead of
    :py:class:`ConsentFormMixin`.
    """

    form_id = 'privacy_consent'
    form_title = _('Privacy Consent')

    def save(self):
        """Save the form.

        This will save the consent information from the field.
        """
        self.save_consent(self.request.user)

        messages.add_message(
            self.request, messages.INFO,
            _('Your choices have been saved. You can make changes to these '
              'at any time.'))

    def get_consent_user(self):
        """Return the user deciding on consent.

        Returns:
            django.contrib.auth.models.User:
            The user deciding on consent.
        """
        return self.request.user

    def get_consent_source(self):
        """Return a source to record in the consent audit trail.

        By default, this returns the absolute URL for the page.

        Returns:
            unicode:
            The source to record for each consent entry.
        """
        return self.request.build_absolute_uri()
