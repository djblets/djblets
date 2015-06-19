from __future__ import unicode_literals

try:
    from django.apps import AppConfig
except ImportError:
    # Django < 1.7
    AppConfig = object


class UtilAppConfig(AppConfig):
    name = 'djblets.util'
    label = 'djblets_util'
