from __future__ import unicode_literals

try:
    from django.apps import AppConfig
except ImportError:
    # Django < 1.7
    AppConfig = object


class PipelineAppConfig(AppConfig):
    name = 'djblets.pipeline'
    label = 'djblets_pipeline'
