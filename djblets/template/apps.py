from __future__ import unicode_literals

try:
    from django.apps import AppConfig
except ImportError:
    # Django < 1.7
    AppConfig = object


class TemplateAppConfig(AppConfig):
    name = 'djblets.template'
    label = 'djblets_template'
