from __future__ import unicode_literals

try:
    from django.apps import AppConfig
except ImportError:
    # Django < 1.7
    AppConfig = object


class DBAppConfig(AppConfig):
    name = 'djblets.db'
    label = 'djblets_db'
