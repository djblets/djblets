"""Utility functions for working with template contexts."""

from django.core.exceptions import ImproperlyConfigured
from django.template import engines


def get_default_template_context_processors(engine_name='django'):
    """Return all default template context processors for an engine.

    Args:
        engine_name (unicode):
            This specifies which template engine's context processors to
            return.

    Returns:
        list of callable:
        The list of template context processors.

    Raises:
        django.core.exceptions.ImproperlyConfigured:
            The specified template engine wasn't valid on this version of
            Django.
    """
    try:
        template_engine = engines[engine_name]
    except KeyError:
        raise ImproperlyConfigured(
            'The "%s" template engine must be defined.'
            % engine_name)

    return template_engine.engine.template_context_processors
