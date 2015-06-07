"""Standard views for displaying and interacting with configuration forms."""

from __future__ import unicode_literals

from django.http import Http404, HttpResponseBadRequest, HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.views.generic.base import TemplateView


class ConfigPagesView(TemplateView):
    """Base view for a set of configuration pages.

    This will render the page for managing a set of configuration sub-pages
    (:py:class:`djblets.configforms.pages.ConfigPage` subclasses).

    Subclasses are expected to provide :py:attr:`title` and
    :py:attr:`page_classes`, at a minimum.

    To dynamically compute pages, implement a :py:attr:`page_classes` method
    and decorate it with ``@property``.
    """

    #: The page title.
    title = None

    #: The title to display over the navigation sidebar.
    nav_title = None

    #: The element ID for the page's container.
    pages_id = 'config_pages'

    #: The template used to render the view.
    template_name = 'configforms/config.html'

    #: The base template that the default template should inherit from.
    base_template_name = 'base.html'

    #: The list of page subclasses to display.
    page_classes = []

    #: The list of CSS bundle names to include on the page.
    css_bundle_names = []

    #: The list of JavaScript bundle names to include on the page.
    js_bundle_names = []

    #: The optional Backbone model used for the view state.
    js_model_class = None

    #: The Backbone view used to render the main view.
    js_view_class = 'Djblets.Config.PagesView'

    #: The HTTP methods that this view will respond to.
    http_method_names = ['get', 'post']

    @method_decorator(csrf_protect)
    def dispatch(self, request, *args, **kwargs):
        self.pages = [
            page_cls(self, request, request.user)
            for page_cls in self.page_classes
        ]

        self.forms = {}

        # Store a mapping of form IDs to form instances, and check for
        # duplicates.
        for page in self.pages:
            for form in page.forms:
                # This should already be handled during form registration.
                assert form.form_id not in self.forms, \
                    'Duplicate form ID %s (on page %s)' % (
                        form.form_id, page.page_id)

                self.forms[form.form_id] = form

        return super(ConfigPagesView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """Handle HTTP post requests to the view.

        This will instantiate the form that the POST was targeting, validate
        the form, and then trigger its save if valid, reloading the page
        with the new state.

        Args:
            request (HttpRequest):
                The HTTP request from the client.

        Returns:
            HttpResponse:
                Either a redirect (if successfully posted), or a standard
                response with the page content.
        """
        form_id = request.POST.get('form_target')

        if form_id is None:
            return HttpResponseBadRequest()

        if form_id not in self.forms:
            return Http404

        # Replace the form in the list with a new instantiation containing
        # the form data. If we fail to save, this will ensure the error is
        # shown on the page.
        old_form = self.forms[form_id]
        page = old_form.page
        form_cls = old_form.__class__
        form = form_cls(page, request, request.user, request.POST)
        self.forms[form_id] = form

        # Replace the form in the page.
        for i, page_form in enumerate(page.forms):
            if page_form.form_id == form_id:
                page.forms[i] = form
                break

        if form.is_valid():
            form.save()

            return HttpResponseRedirect(request.path)

        # For our purposes, there's no difference between the handling of a
        # GET request and a POST request at this stage.
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Return extra context data to render in the template.

        Returns:
            dict: A dictionary of context data for the page.
        """
        return {
            'base_template_name': self.base_template_name,
            'page_title': self.title,
            'nav_title': self.nav_title or self.title,
            'pages_id': self.pages_id,
            'pages': self.pages,
            'css_bundle_names': self.css_bundle_names,
            'js_bundle_names': self.js_bundle_names,
            'js_model_class': self.js_model_class,
            'js_view_class': self.js_view_class,
            'js_model_data': self.get_js_model_data(),
            'js_view_data': self.get_js_view_data(),
            'forms': self.forms.values(),
        }

    def get_js_view_data(self):
        """Return custom options to pass to the JavaScript view.

        By default, this will return an empty dictionary. Subclasses can
        override to provide custom data.

        Returns:
            dict:
                A dictionary of options to pass to the View instance. By
                default, this will be empty.
        """
        return {}

    def get_js_model_data(self):
        """Return custom attributes to pass to the JavaScript model.

        If :py:attr:`js_model_class` is provided, the data returned from this
        function will be provided to the model when constructued.

        By default, this will return an empty dictionary. Subclasses can
        override to provide custom data.

        Returns:
            dict:
                A dictionary of attributes to pass to the Model instance. By
                default, this will be empty.
        """
        return {}
