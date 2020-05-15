from __future__ import unicode_literals

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404
from django.utils import six
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView

from djblets.integrations.mixins import NeedsIntegrationManagerMixin
from djblets.util.templatetags.djblets_images import build_srcset


class IntegrationListContextViewMixin(NeedsIntegrationManagerMixin):
    """A mixin for views that display lists of integrations.

    This allows for custom views that display details on the available
    integrations and all configurations.
    """

    def get_integration_js_view_data(self):
        """Return data for a JavaScript view for the page.

        This will include the list of available integrations IDs, a mapping of
        integration IDs to details, and a list of all configurations.

        Returns:
            dict:
            The data for the JavaScript view.
        """
        integration_manager = self.get_integration_manager()
        integrations_map = {}
        integration_ids = []
        configs = []

        for integration in integration_manager.get_integrations():
            integration_ids.append(integration.integration_id)
            integrations_map[integration.integration_id] = {
                'addURL': self.get_add_config_url(integration),
                'description': integration.description,
                'iconSrc': integration.icon_static_urls['1x'],
                'iconSrcSet': build_srcset(integration.icon_static_urls),
                'id': integration.integration_id,
                'name': integration.name,
            }

        queryset = (
            self.get_configs_queryset()
            .only('enabled', 'integration_id', 'pk', 'name')
        )

        for config in queryset:
            integration_id = config.integration_id

            if integration_id in integrations_map:
                configs.append({
                    'editURL': self.get_edit_config_url(config),
                    'enabled': config.enabled,
                    'id': config.pk,
                    'integrationID': integration_id,
                    'name': config.name,
                })

        return {
            'configs': sorted(
                configs,
                key=lambda config:
                    (integrations_map[config['integrationID']]['name'],
                     config['name'])),
            'csrfToken': self.request.META['CSRF_COOKIE'],
            'integrationIDs': sorted(
                integration_ids,
                key=lambda integration_id:
                    integrations_map[integration_id]['name']),
            'integrationsMap': integrations_map,
        }

    def get_add_config_url(self, integration):
        """Return the URL for adding a new configuration.

        This can be overridden by subclasses to return a URL for another
        namespace or to add additional keyword arguments for the lookup.

        Args:
            integration (djblets.integrations.integration.Integration):
                The integration to add configurations for.

        Returns:
            unicode:
            The Add Configuration URL for the integration.
        """
        return reverse(
            'integration-add-config',
            kwargs={
                'integration_id': integration.integration_id,
            })

    def get_edit_config_url(self, config):
        """Return the URL for editing a configuration.

        This can be overridden by subclasses to return a URL for another
        namespace or to add additional keyword arguments for the lookup.

        Args:
            config (djblets.integrations.models.BaseIntegrationConfig):
                The configuration to return the URL for.

        Returns:
            unicode:
            The URL for editing the configuration.
        """
        return reverse(
            'integration-change-config',
            kwargs={
                'integration_id': config.integration.integration_id,
                'config_id': config.pk,
            })

    def get_configs_queryset(self):
        """Return a queryset for integration configs.

        Subclasses can override this to provide a more strict query to filter
        down the configurations.

        Returns:
            django.db.models.query.QuerySet:
            A queryset for fetching integration configurations.
        """
        return self.get_integration_manager().config_model.objects.all()


class BaseIntegrationListView(IntegrationListContextViewMixin,
                              TemplateView):
    """Base class for a view that lists available integrations.

    This view handles the display of all available integrations, along with
    any existing configurations.

    This is meant to be subclassed to either fine-tune the queries for
    configurations (for instance, by limiting to a particular user or
    organization) or to add access control.
    """

    #: The name of the template used for the page.
    #:
    #: This must be provided if subclassing this yourself.
    template_name = None

    @method_decorator(login_required)
    @method_decorator(csrf_protect)
    def dispatch(self, *args, **kwargs):
        """Handle the request to the view.

        This will first check to make sure the user is logged in.

        Args:
            *args (tuple):
                Arguments to pass to the view.

            **kwargs (dict):
                Keyword arguments to pass to the view.

        Returns:
            django.http.HttpResponse:
            The resulting HTTP response.
        """
        return super(BaseIntegrationListView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        """Return context data for the template.

        By default, this returns a dictionary with a sole ``integrations``
        key, which contains data on each available integration and all
        saved configurations.

        Args:
            **kwargs (dict):
                Any arguments captured in the URL.

        Returns:
            dict:
            A dictionary of context data for the template.
        """
        context = super(BaseIntegrationListView, self).get_context_data(
            **kwargs)
        context['integrationViewData'] = self.get_integration_js_view_data()

        return context


class BaseAdminIntegrationListView(BaseIntegrationListView):
    """Base class for an admin view that lists available integrations.

    This builds upon :py:class:`BaseIntegrationListView`, adding access
    checks to ensure that only administrators can access it.
    """

    template_name = 'integrations/admin/integration_list.html'

    @method_decorator(staff_member_required)
    def dispatch(self, *args, **kwargs):
        """Handle the request to the view.

        This will first check to make sure the user is logged in and is a
        staff member.

        Args:
            *args (tuple):
                Arguments to pass to the view.

            **kwargs (dict):
                Keyword arguments to pass to the view.

        Returns:
            django.http.HttpResponse:
            The resulting HTTP response.
        """
        return super(BaseAdminIntegrationListView, self).dispatch(
            *args, **kwargs)


class BaseIntegrationConfigFormView(NeedsIntegrationManagerMixin,
                                    FormView):
    """Base class for a view that manages an integration configuration.

    This view handles the display of a form for either creating a new
    integration configuration or updating an existing one.

    This is meant to be subclassed to either fine-tune the queries for
    configurations (for instance, by limiting to a particular user or
    organization) or to add access control.
    """

    #: The name of the template used for the page.
    #:
    #: This must be provided if subclassing this yourself.
    template_name = None

    @method_decorator(login_required)
    @method_decorator(csrf_protect)
    def dispatch(self, request, *args, **kwargs):
        """Handle the request to the view.

        This will first check to make sure the user is logged in. It then
        looks up the appropriate configuration ID from the URL before passing
        it on to the view.

        Args:
            *args (tuple):
                Positional arguments to pass to the view.

            **kwargs (dict):
                Keyword arguments to pass to the view.

        Returns:
            django.http.HttpResponse:
            The resulting HTTP response.

        Raises:
            django.http.Http404:
                The integration or configuration with the given ID was not
                found.
        """
        integration_mgr = self.get_integration_manager()
        self.integration_mgr = integration_mgr

        self.integration = integration_mgr.get_integration(
            kwargs['integration_id'])

        if not self.integration:
            raise Http404

        if 'config_id' in kwargs:
            try:
                self.config = integration_mgr.get_integration_configs(
                    integration_cls=self.integration.__class__,
                    pk=kwargs['config_id'],
                    **self.get_config_query_kwargs(**kwargs))[0]
            except IndexError:
                raise Http404
        else:
            self.config = None

        return super(BaseIntegrationConfigFormView, self).dispatch(
            request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        """Handle HTTP DELETE requests.

        This will delete the integration configuration.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple):
                Positional arguments passed to the view.

            **args (dict):
                Keyword arguments passed to the view.

        Returns:
            django.http.HttpResponse:
            The resulting HTTP response.
        """
        self.config.delete()

        return HttpResponse(status=204)

    def get_config_query_kwargs(self, **kwargs):
        """Return query arguments for fetching an integration configuration.

        This can be subclassed to return additional arguments used when
        fetching configurations, based on the needs of the application. For
        example, limiting it by user or organization.

        By default, this doesn't return any additional query arguments.

        Args:
            **kwargs (dict):
                Any arguments captured in the URL.

        Returns:
            dict:
            Additional query arguments as a dictionary. This will be turned
            into keyword arguments for a filter query.
        """
        return {}

    def get_context_data(self, **kwargs):
        """Return context data for the configuration page.

        Args:
            **kwargs (dict):
                Additional keyword arguments that may be passed to this
                function by the parent views.

        Returns:
            dict:
            The context to provide on the page.
        """
        data = super(BaseIntegrationConfigFormView, self).get_context_data(
            **kwargs)
        data['success_url'] = self.get_success_url()

        return data

    def get_form_kwargs(self):
        """Return keyword arguments to pass to the form.

        This will, by default, provide ``integration`` and configuration
        ``instance`` keyword arguments to the form during initialization,
        along with the ``request``.

        Subclases can override it with additional arguments if needed.

        Returns:
            dict:
            A dictionary of keyword arguments to pass to the form.
        """
        form_kwargs = \
            super(BaseIntegrationConfigFormView, self).get_form_kwargs()
        form_kwargs.update({
            'integration': self.integration,
            'request': self.request,
            'instance': self.config,
        })

        return form_kwargs

    def get_success_url(self):
        """Return the URL to redirect to when successfully saving the form.

        This defaults to returning back to the integrations page. Consumers
        that have special values to fill out in the URL will need to
        override this.

        Returns:
            unicode:
            The URL to redirect to.
        """
        return reverse('integration-list')

    def get_form_class(self):
        """Return the class used for the configuration form.

        This will return whatever class is specified for that integration.

        This function is used internally by Django's generic views framework.
        It should not be overridden.

        Returns:
            djblets.integrations.forms.IntegrationConfigForm:
            The form sublass used for integration configuration.
        """
        return self.integration.config_form_cls

    def form_valid(self, form):
        """Handle the saving of a valid configuration form

        This will save the configuration and then perform a redirect to the
        success URL, defined by :py:meth:`get_success_url`.

        Args:
            form (djblets.integrations.forms.IntegrationConfigForm):
                The form to save.

        Returns:
            django.http.HttpResponse:
            An HTTP response redirecting to the success URL.
        """
        self.object = form.save()

        return super(BaseIntegrationConfigFormView, self).form_valid(form)


class BaseAdminIntegrationConfigFormView(BaseIntegrationConfigFormView):
    """Base class for an admin view that manages an integration configuration.

    This builds upon :py:class:`BaseIntegrationConfigFormView`, adding access
    checks to ensure that only administrators can access it.
    """

    template_name = 'integrations/admin/configure_integration.html'

    @method_decorator(staff_member_required)
    def dispatch(self, *args, **kwargs):
        """Handle the request to the view.

        This will first check to make sure the user is logged in and is a
        staff member.

        Args:
            *args (tuple):
                Arguments to pass to the view.

            **kwargs (dict):
                Keyword arguments to pass to the view.

        Returns:
            django.http.HttpResponse:
            The resulting HTTP response.
        """
        return super(BaseAdminIntegrationConfigFormView, self).dispatch(
            *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Return context data for the configuration page.

        Args:
            **kwargs (dict):
                Additional keyword arguments that may be passed to this
                function by the parent views.

        Returns:
            dict:
            The context to provide on the page.
        """
        data = (
            super(BaseAdminIntegrationConfigFormView, self)
            .get_context_data(**kwargs)
        )
        data.update({
            'opts': self.integration_mgr.config_model._meta,
            'original': self.config,
            'show_delete_link': self.config is not None,
            'show_save': True,
        })

        return data
