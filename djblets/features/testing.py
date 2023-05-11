"""Helpers for unit tests working with features."""

from contextlib import contextmanager
from typing import Dict, Generator, List, Optional, Union

from typing_extensions import TypeAlias

from djblets.features.feature import Feature
from djblets.features.registry import get_features_registry


#: A type mapping feature instances or IDs to enabled flags.
#:
#: Version Added:
#:     3.3
FeatureStates: TypeAlias = Dict[Union[Feature, str], bool]


@contextmanager
def override_feature_checks(
    feature_states: FeatureStates,
) -> Generator[None, None, None]:
    """Override multiple features for a test.

    Unit tests can make use of this context manager to ensure that one or more
    features have particular enabled/disabled states before executing any code
    dependent on those features.

    Only the provided features will be modified, with all other feature logic
    falling back to the default behavior for the configured feature checker.

    Version Change:
        1.0.13:
        ``feature_states`` now accepts a
        :py:class:`~djblets.features.feature.Feature` instance as a key.

    Args:
        feature_states (dict):
            A dictionary of feature IDs or instances to booleans (representing
            whether the feature is enabled).

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
    registry = get_features_registry()
    old_state: List[Dict[str, object]] = []

    for feature_or_id, enabled in feature_states.items():
        feature: Optional[Feature]

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

    try:
        yield
    finally:
        for feature_info in old_state:
            setattr(feature_info['feature'], 'is_enabled',
                    feature_info['func'])


@contextmanager
def override_feature_check(
    feature_id: Union[Feature, str],
    enabled: bool,
) -> Generator[None, None, None]:
    """Override a feature for a test.

    Unit tests can make use of this context manager to ensure that a specific
    feature has a particular enabled/disabled state before executing any code
    dependent on that feature.

    Only the provided feature will be modified, with all other feature logic
    falling back to the default behavior for the configured feature checker.

    Args:
        feature_id (str or djblets.features.feature.Feature):
            The ID or instance of the feature to override.

        enabled (bool):
            The enabled state for the feature.

    Example:
        .. code-block:: python

           from myproject.features import my_feature_2

           with override_feature_check('my-feature', enabled=False):
               # Your test code here.

           with override_feature_check(my_feature_2, enabled=True):
               # Your test code here.
    """
    with override_feature_checks({feature_id: enabled}):
        yield
