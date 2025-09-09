"""Helpers for unit tests working with features."""

from __future__ import annotations

from typing import Dict, Union

from django.test.utils import TestContextDecorator
from typing_extensions import TypeAlias

from djblets.features.feature import Feature
from djblets.features.registry import get_features_registry


#: A type mapping feature instances or IDs to enabled flags.
#:
#: Version Added:
#:     3.3
FeatureStates: TypeAlias = Dict[Union[Feature, str], bool]


class override_feature_checks(TestContextDecorator):
    """Override multiple features for a test.

    Version Changed:
        5.3:
        Changed from a pure context manager to a class that can act either as a
        context manager or a decorator for test methods.

    Version Changed:
        1.0.13:
        ``feature_states`` now accepts a
        :py:class:`~djblets.features.feature.Feature` instance as a key.

    Example:
        .. code-block:: python

           from myproject.features import my_feature_3

           feature_states = {
               'my-feature-1': True,
               'my-feature-2': False,
               my_feature_3: True,
           }

           with override_feature_checks(feature_states):
               # Your test code here.
    """

    ######################
    # Instance variables #
    ######################

    #: The desired feature states.
    feature_states: FeatureStates

    #: The old states, to restore once finished.
    _old_state: list[dict[str, object]]

    def __init__(
        self,
        feature_states: FeatureStates,
    ) -> None:
        """Initialize the override.

        Args:
            feature_states (dict):
                A dictionary of feature IDs or instances to booleans
                (representing whether the feature is enabled).
        """
        super().__init__()

        self.feature_states = feature_states
        self._old_states = []

    def enable(self) -> None:
        """Enable the feature overrides."""
        registry = get_features_registry()
        old_state: list[dict[str, object]] = []

        for feature_or_id, enabled in self.feature_states.items():
            feature: Feature | None

            if isinstance(feature_or_id, Feature):
                feature = feature_or_id
            else:
                feature = registry.get_feature(feature_or_id)
                assert feature is not None

            old_state.append({
                'feature': feature,
                'func': feature.is_enabled,
            })

            setattr(feature, 'is_enabled',
                    lambda _is_enabled=enabled, **kwargs: _is_enabled)

        self._old_state = old_state

    def disable(self) -> None:
        """Disable the feature overrides."""
        for feature_info in self._old_state:
            setattr(feature_info['feature'], 'is_enabled',
                    feature_info['func'])

        self._old_state = []


class override_feature_check(override_feature_checks):
    """Override a feature for a test.

    Unit tests can make use of this context manager to ensure that a specific
    feature has a particular enabled/disabled state before executing any code
    dependent on that feature.

    Only the provided feature will be modified, with all other feature logic
    falling back to the default behavior for the configured feature checker.

    Version Changed:
        5.3:
        Changed from a pure context manager to a class that can act either as a
        context manager or a decorator for test methods.

    Example:
        .. code-block:: python

           from myproject.features import my_feature_2

           with override_feature_check('my-feature', enabled=False):
               # Your test code here.

           with override_feature_check(my_feature_2, enabled=True):
               # Your test code here.
    """

    def __init__(
        self,
        feature_id: Feature | str,
        enabled: bool,
    ) -> None:
        """Initialize the override.

        Args:
            feature_id (str or djblets.features.feature.Feature):
                The ID or instance of the feature to override.

            enabled (bool):
                The enabled state for the feature.
        """
        super().__init__({
            feature_id: enabled,
        })
