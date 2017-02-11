"""Base support for configuration pages."""

from __future__ import unicode_literals

from django.template.context import RequestContext
from django.template.loader import render_to_string


class ConfigPage(object):
    """Base class for a page of configuration forms.

    Each ConfigPage is represented in the main page by an entry in the
    navigation sidebar. When the user has navigated to that page, all visible
    :py:class:`djblets.configforms.forms.ConfigPageForm` subclasses owned by
    the ConfigPage will be displayed.
    """

    #: The unique ID of the page.
    #:
    #: This must be unique across all ConfigPages at a given URL.
    page_id = None

    #: The displayed title for the page.
    #:
    #: This will show up in the navigation sidebar.
    page_title = None

    #: The list of form subclasses to display on the page.
    form_classes = None

    #: The template used to render the page.
    template_name = 'configforms/config_page.html'

    def __init__(self, config_view, request, user):
        """Initialize the page.

        Args:
            config_view (ConfigPagesView):
                The view that manages this ConfigPage.

            request (HttpRequest):
                The HTTP request from the client.

            user (User):
                The user who is viewing the page.
        """
        self.config_view = config_view
        self.request = request
        self.forms = [
            form
            for form in (
                form_cls(self, request, user)
                for form_cls in self.form_classes
            )
            if form.is_visible()
        ]

    def is_visible(self):
        """Return whether the page should be visible.

        Visible pages are shown in the sidebar and can be navigated to.

        By default, a page is visible if at least one of its forms are
        also visible.

        Returns:
            bool:
                ``True`` if the page will be rendered, or ``False`` otherwise.
        """
        for form in self.forms:
            if form.is_visible():
                return True

        return False

    def render(self):
        """Render the page to a string.

        :py:attr:`template_name` will be used to render the page. The
        template will be passed ``page`` (this page's instance) and
        ``forms`` (the list of :py:class:`ConfigPageForm` instances to
        render).

        Subclasses can override this to provide additional rendering logic.

        Returns:
            unicode: The rendered page as HTML.
        """
        return render_to_string(
            self.template_name,
            RequestContext(self.request, {
                'page': self,
                'forms': self.forms,
            }))
