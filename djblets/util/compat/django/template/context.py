# TODO: Remove this file once we no longer support a verison of Django
#       prior to 1.7.
#
"""Compatibility functions for working with template contexts."""

from __future__ import unicode_literals

from django.template.context import Context


def flatten_context(context):
    """Flatten a template context into a dictionary.

    Django 1.7 introduced :py:meth:`Context.flatten
    <django.template.Context.flatten>`, which converts a template context into
    a dictionary. However, this doesn't exist on Django 1.6. This compatibility
    function ensures equivalent functionality on both.
    """
    assert isinstance(context, Context)

    if hasattr(context, 'flatten'):
        # Django >= 1.7
        return context.flatten()
    else:
        # Django == 1.6
        new_dict = {}

        for d in context.dicts:
            new_dict.update(d)

        return new_dict
