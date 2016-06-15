"""Feature switch support for applications.

This module contains convenience imports for:

* :py:class:`~djblets.features.feature.Feature`
* :py:class:`~djblets.features.feature.FeatureLevel`
* :py:class:`~djblets.features.registry.get_features_registry`
"""

from __future__ import unicode_literals

from djblets.features.feature import Feature, FeatureLevel
from djblets.features.registry import get_features_registry


__all__ = [
    'Feature',
    'FeatureLevel',
    'get_features_registry',
]
