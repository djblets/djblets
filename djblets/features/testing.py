"""Helpers for unit tests working with features."""

from __future__ import unicode_literals

from contextlib import contextmanager

from django.utils import six

from djblets.features.registry import get_features_registry


@contextmanager
def override_feature_checks(feature_states):
    """Override multiple features for a test.

    Unit tests can make use of this context manager to ensure that one or more
    features have particular enabled/disabled states before executing any code
    dependent on those features.

    Only the provided features will be modified, with all other feature logic
    falling back to the default behavior for the configured feature checker.

    Args:
        feature_states (dict):
            A dictionary of feature IDs to booleans (representing whether the
            feature is enabled).

    Example:
        .. code-block:: python

           feature_states = {
               'my-feature-1': True,
               'my-feature-2': False,
           }

           with override_feature_checks(feature_states):
               # Your test code here.
    """
    registry = get_features_registry()
    old_state = []

    for feature_id, enabled in six.iteritems(feature_states):
        feature = registry.get_feature(feature_id)

        old_state.append({
            'feature': feature,
            'func': feature.is_enabled,
        })

        feature.is_enabled = \
            lambda _is_enabled=enabled, **kwargs: _is_enabled

    yield

    for feature_info in old_state:
        feature_info['feature'].is_enabled = feature_info['func']


@contextmanager
def override_feature_check(feature_id, enabled):
    """Override a feature for a test.

    Unit tests can make use of this context manager to ensure that a specific
    feature has a particular enabled/disabled state before executing any code
    dependent on that feature.

    Only the provided feature will be modified, with all other feature logic
    falling back to the default behavior for the configured feature checker.

    Args:
        feature_id (unicode):
            The ID of the feature to override.

        enabled (bool):
            The enabled state for the feature.

    Example:
        .. code-block:: python

           with override_feature_check('my-feature', enabled=False):
               # Your test code here.
    """
    with override_feature_checks({feature_id: enabled}):
        yield
