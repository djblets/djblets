"""Integrations template tags."""

from __future__ import unicode_literals

from django import template


register = template.Library()


@register.simple_tag
def render_integration_config_status(integration, config):
    """Render the integration configuration's status.

    Args:
        integration (djblets.integrations.integrations.Integration):
            The integration to which the config belongs.

        config (djblets.integrations.models.IntegrationConfig):
            The configuration whose status is to be rendered.

    Returns:
        django.utils.safestring.SafeText:
        The rendered HTML.
    """
    return integration.render_config_status(config)
