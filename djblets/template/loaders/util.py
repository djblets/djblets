from __future__ import unicode_literals

from contextlib import contextmanager

import django.template.loader


@contextmanager
def add_template_loader(template_loader):
    """Temporarily add a template source loaders.

    Args:
        template_loader (django.template.loader.BaseLoader):
            The template loader to use.
    """
    old_loaders = django.template.loader.template_source_loaders

    if old_loaders is None:
        django.template.loader.template_source_loaders = (template_loader,)
    else:
        django.template.loader.template_source_loaders = (
            old_loaders + (template_loader,))
    try:
        yield
    finally:
        django.template.loader.template_source_loaders = old_loaders


@contextmanager
def replace_template_loaders(template_loaders):
    """Temporarily replace the template loaders.

    Args:
        template_loaders (list):
            A list of :py:class:`django.template.loader.BaseLoader` instances.
    """
    old_loaders = django.template.loader.template_source_loaders

    django.template.loader.template_source_loaders = template_loaders

    try:
        yield
    finally:
        django.template.loader.template_source_loaders = old_loaders
