"""Base support for configuration forms."""

from __future__ import unicode_literals

import warnings

from django import forms
from django.template.context import RequestContext
from django.utils import six
from django.utils.translation import ugettext_lazy as _

from djblets.util.compat.django.template.loader import render_to_string


class ConfigPageForm(forms.Form):
    """Base class for a form on a ConfigPage.

    Consumers can subclass ConfigPageForm and register it on a
    :py:class:`djblets.configforms.pages.ConfigPage`. It will be shown
    whenever the user navigates to that page.

    A form will generally be shown as a box with a title and a save button,
    though this is customizable.

    A standard form presents fields that can be filled out and posted. More
    advanced forms can supply their own template or even their own JavaScript
    models, views, and CSS.
    """

    #: The unique ID of the form.
    #:
    #: This must be unique across all ConfigPages at a given URL.
    form_id = None

    #: The displayed title for the form.
    form_title = None

    #: The label for the save button.
    #:
    #: This can be set to ``None`` to disable the button.
    save_label = _('Save')

    #: The template used to render the form.
    template_name = 'configforms/config_page_form.html'

    #: The list of CSS bundle names to include on the page.
    css_bundle_names = []

    #: The list of JavaScript bundle names to include on the page.
    js_bundle_names = []

    #: The optional Backbone model used for the configuration form state.
    js_model_class = None

    #: The optional Backbone view used to render the form.
    js_view_class = None

    form_target = forms.CharField(
        required=False,
        widget=forms.HiddenInput)

    def __init__(self, page, request, user, *args, **kwargs):
        """Initialize the form.

        Args:
            page (ConfigPage):
                The page this form resides on.

            request (HttpRequest):
                The HTTP request from the client.

            user (User):
                The user who is viewing the page.
        """
        super(ConfigPageForm, self).__init__(*args, **kwargs)

        self.page = page
        self.request = request
        self.user = user

        self.fields['form_target'].initial = self.form_id
        self.load()

    def set_initial(self, field_values):
        """Set the initial fields for the form based on provided data.

        This can be used during :py:meth:`load` to fill in the fields based on
        data from the database or another source.

        Args:
            field_values (dict):
                The initial field data to set on the form.
        """
        for field, value in six.iteritems(field_values):
            self.fields[field].initial = value

    def is_visible(self):
        """Return whether the form should be visible.

        This can be overridden to hide forms based on certain criteria.

        Returns:
            bool:
            ``True`` if the form should be rendered on the page (default),
            or ``False`` otherwise.
        """
        return True

    def get_js_model_data(self):
        """Return data to pass to the JavaScript Model during instantiation.

        If :py:attr:`js_model_class` is provided, the data returned from this
        function will be provided to the model when constructed.

        Returns:
            dict:
            A dictionary of attributes to pass to the Model instance. By
            default, it will be empty.
        """
        return {}

    def get_js_view_data(self):
        """Return data to pass to the JavaScript View during instantiation.

        If :py:attr:`js_view_class` is provided, the data returned from this
        function will be provided to the view when constructed.

        Returns:
            dict:
            A dictionary of options to pass to the View instance. By default,
            it will be empty.
        """
        return {}

    def render(self):
        """Render the form to a string.

        :py:attr:`template_name` will be used to render the form. The
        template will be passed ``form`` (this form's instance) and
        ``page`` (the parent :py:class:`ConfigPage`).

        Subclasses can override this to provide additional rendering logic.

        Returns:
            unicode: The rendered form as HTML.
        """
        context = dict({
            'form': self,
            'page': self.page,
        }, **self.get_extra_context())

        return render_to_string(template_name=self.template_name,
                                context=context,
                                request=self.request)

    def get_extra_context(self):
        """Return extra rendering context.

        Subclasses can override this to provide additional rendering context.

        Returns:
            dict:
            The additional rendering context. By default, it is empty.
        """
        return {}

    def load(self):
        """Load data for the form.

        By default, this does nothing. Subclasses can override this to
        load data into the fields based on data from the database or
        from another source.
        """
        pass

    def save(self):
        """Save the form data.

        Subclasses must override this to save data from the fields into
        the database.

        Returns:
            django.http.HttpResponse:
            An HTTP response to return from the view after saving, or ``None``
            to be returned to the
            :py:class:`~djblets.configforms.views.ConfigPagesView`.
        """
        raise NotImplementedError
