"""Utility functions for working with template-related caches."""

from django.template import Engine, engines


def clear_template_tag_caches():
    """Clear the template tags caches.

    This allows changes to the list of available template tags to be reflected
    in any new templates by emptying all the caches and forcing the available
    list of tags to be rebuilt.
    """
    engines._engines.clear()
    Engine.get_default.cache_clear()


def clear_template_caches():
    """Clear the templates caches.

    This clears any caches for template parse trees and related state, forcing
    templates to be re-parsed and re-rendered.
    """
    template_loaders = []

    for engine in engines.all():
        template_loaders += engine.engine.template_loaders

    for template_loader in template_loaders:
        template_loader.reset()
