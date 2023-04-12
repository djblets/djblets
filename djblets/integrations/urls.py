"""URL helpers for integrations."""

from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING, Tuple, Type, Union

from django.urls import include, path, re_path

from djblets.integrations.views import (BaseIntegrationConfigFormView,
                                        BaseIntegrationListView)

if TYPE_CHECKING:
    # This requires django-stubs.
    from django.urls import _AnyURL


def build_integration_urlpatterns(
    *,
    list_view_cls: Type[BaseIntegrationListView],
    config_form_view_cls: Type[BaseIntegrationConfigFormView],
    namespace: Optional[str] = None,
    app_name: Optional[str] = None,
) -> List[_AnyURL]:
    """Build URL patterns for integration pages.

    This will produce a set of URL patterns for the integration administration
    pages that take advantage of the specialized views provided. These can
    be used in a :file:`urls.py`, either returned as a ``urlpatterns``
    variable or included using :py:func:`~django.conf.urls.include`.

    Version Changed:
        3.2:
        * Added the optional ``app_name`` argument.
        * Keyword arguments are now expected, and will be required in
          Djblets 4.

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

        namespace (str, optional):
            The namespace to use for all URL names.

            For legacy reasons, this is an empty string. If embedding into
            other parts of the app, this should be changed. For instance,
            you may want the admin version to use ``admin``.

        app_name (str, optional):
            An optional app name to assign to the URLs.

            This is required by Django when using ``namespace`` starting in
            Django 3.x.

            Version Added:
                3.2

    Returns:
        list:
        The list of URL patterns.
    """
    include_target: Union[List[_AnyURL], Tuple[List[_AnyURL], str]]
    urlpatterns: List[_AnyURL] = []

    if list_view_cls is not None:
        urlpatterns.append(
            path('', list_view_cls.as_view(), name='integration-list'))

    if config_form_view_cls is not None:
        urlpatterns.append(
            re_path(r'^(?P<integration_id>[A-Za-z0-9_\.]+)/configs/', include([
                path('add/',
                     config_form_view_cls.as_view(),
                     name='integration-add-config'),
                path('<int:config_id>/',
                     config_form_view_cls.as_view(),
                     name='integration-change-config'),
            ])))

    if app_name:
        include_target = (urlpatterns, app_name)
    else:
        include_target = urlpatterns

    return [
        path('', include(include_target, namespace=namespace)),
    ]
