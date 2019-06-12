from __future__ import unicode_literals

from django.conf.urls import include, url


def build_integration_urlpatterns(list_view_cls, config_form_view_cls,
                                  namespace=None):
    """Build URL patterns for integration pages.

    This will produce a set of URL patterns for the integration administration
    pages that take advantage of the specialized views provided. These can
    be used in a :file:`urls.py`, either returned as a ``urlpatterns``
    variable or included using :py:func:`~django.conf.urls.include`.

    Args:
        list_view_cls (type, optional):
            The view responsible for listing available integrations. This
            should be a subclass of
            :py:class:`~djblets.integrations.views.BaseIntegrationListView`.

            If ``None``, the integration list URL will not be provided in the
            URL patterns. Consumers should define their own
            ``integration-list`` URL with the appropriate namespace in order to
            handle any URL reversing that may occur.

        config_form_view_cls (type):
            The view responsible for configuring an integration. This should
            be a subclass of
            :py:class:`~djblets.integrations.views.
            BaseIntegrationConfigFormView`.

            If ``None``, the integration configuration URLs will not be
            provided in the URL patterns. This *will* break the integrations
            list URL unless consumers provide their own
            ``integration-add-config`` and ``integration-change-config`` URL
            registrations.

        namespace (unicode, optional):
            The namespace to use for all URL names.

            For legacy reasons, this is an empty string. If embedding into
            other parts of the app, this should be changed. For instance,
            you may want the admin version to use ``admin``.
    """
    urlpatterns = []

    if list_view_cls is not None:
        urlpatterns.append(
            url('^$',
                list_view_cls.as_view(),
                name='integration-list'))

    if config_form_view_cls is not None:
        urlpatterns.append(
            url('^(?P<integration_id>[A-Za-z0-9_\.]+)/configs/', include([
                url('^add/$',
                    config_form_view_cls.as_view(),
                    name='integration-add-config'),
                url('^(?P<config_id>[0-9]+)/$',
                    config_form_view_cls.as_view(),
                    name='integration-change-config'),
            ])))

    return [
        url('', include(urlpatterns,
                        namespace=namespace)),
    ]
