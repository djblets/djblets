"""Utility functions for working with template-related caches."""

from __future__ import unicode_literals

try:
    # Django >= 1.6, <= 1.8
    from django.template.base import libraries
except ImportError:
    libraries = None

try:
    # Django >= 1.7, <= 1.8
    from django.template.base import get_templatetags_modules
except ImportError:
    # Django >= 1.9
    get_templatetags_modules = None

try:
    # Django >= 1.8
    from django.template import Engine, engines
except ImportError:
    # Django >= 1.7, <= 1.8
    Engine = None
    engines = None


def clear_template_tag_caches():
    """Clear the template tags caches.

    This allows changes to the list of available template tags to be reflected
    in any new templates by emptying all the caches and forcing the available
    list of tags to be rebuilt.
    """
    if libraries is not None:
        # Django >= 1.6, <= 1.8
        libraries.clear()

    try:
        # Django == 1.6
        #
        # We'll import templatetags_modules here because we want the most
        # recent copy of templatetags_modules.
        from django.template.base import templatetags_modules

        del(templatetags_modules[:])
    except ImportError:
        if get_templatetags_modules is not None:
            # Django >= 1.7, <= 1.8
            get_templatetags_modules.cache_clear()

        if engines:
            # Django >= 1.8
            engines._engines.clear()
            Engine.get_default.cache_clear()


def clear_template_caches():
    """Clear the templates caches.

    This clears any caches for template parse trees and related state, forcing
    templates to be re-parsed and re-rendered.
    """
    if engines is not None:
        # Django >= 1.8
        template_loaders = []

        for engine in engines.all():
            template_loaders += engine.engine.template_loaders
    else:
        # Django >= 1.6, <= 1.7
        #
        # We need to import this here in order to get the latest copy
        # of this variable.
        from django.template.loader import template_source_loaders

        template_loaders = template_source_loaders or []

    for template_loader in template_loaders:
        try:
            template_loader.reset()
        except AttributeError:
            pass
