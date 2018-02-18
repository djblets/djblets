"""Utility functions for working with template contexts."""

from __future__ import unicode_literals

from django.core.exceptions import ImproperlyConfigured

try:
    # Django >= 1.8
    from django.template import engines as template_engines

    get_standard_processors = None
except ImportError:
    # Django <= 1.7
    from django.template.context import get_standard_processors

    template_engines = None


def get_default_template_context_processors(engine_name='django'):
    """Return all default template context processors for an engine.

    Args:
        engine_name (unicode):
            When run on Django 1.8 or higher, this specifies which template
            engine's context processors to return. On Django 1.7 and older,
            this is ignored.

    Returns:
        list of callable:
        The list of template context processors.

    Raises:
        django.core.exceptions.ImproperlyConfigured:
            The specified template engine wasn't valid on this version of
            Django.
    """
    if template_engines is None:
        return get_standard_processors()
    else:
        try:
            template_engine = template_engines[engine_name]
        except KeyError:
            raise ImproperlyConfigured(
                'The "%s" template engine must be defined.'
                % engine_name)

        return template_engine.engine.template_context_processors
