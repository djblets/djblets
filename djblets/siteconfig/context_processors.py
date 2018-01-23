"""Template context processors for SiteConfiguration information."""

from __future__ import unicode_literals

import logging

from django.conf import settings

from djblets.siteconfig.models import SiteConfiguration


logger = logging.getLogger(__name__)


def siteconfig(request):
    """Return context variables for accessing site configuration data.

    This will provide templates with a ``siteconfig`` variable, representing
    the current :py:class:`~djblets.siteconfig.models.SiteConfiguration` for
    the installation, and ``siteconfig_settings``, representing all settings on
    the current configuration.

    ``siteconfig_settings`` is preferred over accessing
    :py:attr:`siteconfig.settings
    <djblets.siteconfig.models.SiteConfiguration.settings>`, as it will
    properly handle returning default values.

    Args:
        request (django.http.HttpRequest):
            The current HTTP request.

    Returns:
        dict:
        A dictionary with ``siteconfig`` and ``siteconfig_settings`` keys.
    """
    try:
        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig_settings = siteconfig.settings_wrapper
    except Exception as e:
        logger.exception('Unable to load SiteConfiguration: %s', e)

        siteconfig = None
        siteconfig_settings = None

    return {
        'siteconfig': siteconfig,
        'siteconfig_settings': siteconfig_settings,
    }


def settings_vars(request):
    """Return context variables for accessing Django settings.

    This will provide templates with a ``settings`` variable, which represents
    the Django settings object.

    Args:
        request (django.http.HttpRequest):
            The current HTTP request.

    Returns:
        dict:
        A dictionary with a ``settings`` key.
    """
    return {'settings': settings}
