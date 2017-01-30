from __future__ import unicode_literals

from django.conf.urls import include, url


def build_integration_urlpatterns(list_view_cls, config_form_view_cls):
    """Build URL patterns for integration pages.

    This will produce a set of URL patterns for the integration administration
    pages that take advantage of the specialized views provided. These can
    be used in a :file:`urls.py`, either returned as a ``urlpatterns``
    variable or included using :py:func:`~django.conf.urls.include`.

    Args:
        list_view_cls (type):
            The view responsible for listing available integrations. This
            should be a subclass of
            :py:class:`~djblets.integrations.views.BaseIntegrationListView`.

        list_view_cls (type):
            The view responsible for configuring an integration. This should
            be a subclass of
            :py:class:`~djblets.integrations.views.BaseIntegrationConfigFormView`.
    """
    configs_urlpatterns = [
        url('^add/$', config_form_view_cls.as_view(),
            name='integration-add-config'),
        url('^(?P<config_id>[0-9]+)/$', config_form_view_cls.as_view(),
            name='integration-change-config'),
    ]

    return [
        url('^$', list_view_cls.as_view(), name='integration-list'),
        url('^(?P<integration_id>[A-Za-z0-9_\.]+)/configs/',
            include(configs_urlpatterns)),
    ]
