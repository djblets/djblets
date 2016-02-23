"""Compatibility tags for django-pipeline <= 1.3.

django-pipeline 1.5 renamed the old ``compressed_css` and ``compressed_js``
template tags to ``stylesheet`` and ``javascript``. While this change makes a
lot of sense, it's possible that third-party users will still have templates
relying on the old names.
"""
from __future__ import unicode_literals

from django import template
from pipeline.templatetags.pipeline import javascript, stylesheet


register = template.Library()


register.tag('compressed_css', stylesheet)
register.tag('compressed_js', javascript)
