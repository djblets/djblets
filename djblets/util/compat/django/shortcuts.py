"""Compatibility functions for django.shortcuts.

Note that this module is not considered API-stable. Changes may be made that
remove or alter functionality in the future. Please use at your own risk.
"""

from __future__ import unicode_literals

from django.http import HttpResponse

from djblets.util.compat.django.template.loader import render_to_string


# TODO: Remove render() once we no longer support a version of Django prior
#       to 1.10.

def render(request, template_name, context=None, content_type=None,
           status=None, using=None):
    """Render a template name to a response.

    This provides compatibility for the :py:func:`django.shortcuts.loader`
    across Django 1.6 on up.

    Args:
        request (django.http.HttpRequest):
            The HTTP request from the client.

        template_name (unicode):
            The name of the template to render.

        context (dict, optional):
            The template context.

        content_type (unicode, optional);
            An optional content type to set for the response.

        status (int, optional):
            An optional HTTP status code to set for the response.

        using (unicode, optional):
            The optional template render backend to use to render this
            template. This is ignored for Django 1.6.

    Returns:
        django.http.HttpResponse:
        The resulting HTTP response.
    """
    content = render_to_string(template_name=template_name,
                               context=context,
                               request=request,
                               using=using)

    return HttpResponse(content,
                        content_type=content_type,
                        status=status)
