"""App configuration for djblets.privacy."""

from __future__ import unicode_literals

try:
    from django.apps import AppConfig
except ImportError:
    # Django < 1.7
    AppConfig = object


class PrivacyAppConfig(AppConfig):
    """Default app configuration for djblets.privacy."""

    name = 'djblets.privacy'
    label = 'djblets_privacy'
