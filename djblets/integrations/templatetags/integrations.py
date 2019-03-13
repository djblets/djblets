"""Integrations template tags."""

from __future__ import unicode_literals

import warnings

from django import template

from djblets.deprecation import RemovedInDjblets20Warning


register = template.Library()


@register.simple_tag
def render_integration_config_status(integration, config):
    """Render the integration configuration's status.

    This is deprecated and no longer returns anything.

    Deprecated:
        1.0.11:
        This method no longer serves any purpose, due to major UI
        changes. It now returns an empty string.

    Args:
        integration (djblets.integrations.integrations.Integration, unused):
            The integration to which the config belongs.

        config (djblets.integrations.models.IntegrationConfig, unused):
            The configuration whose status is to be rendered.

    Returns:
        unicode:
        An empty string.
    """
    warnings.warn('{% render_integration_config_status %} is deprecated and '
                  'should no longer be called.',
                  RemovedInDjblets20Warning)

    return integration.render_config_status(config)
