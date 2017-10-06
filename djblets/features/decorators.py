"""Feature-related decorators."""

from __future__ import unicode_literals

from functools import wraps

from django.http import HttpResponseNotFound


def _404(*args, **kwargs):
    return HttpResponseNotFound()


def feature_required(feature, not_enabled_view=None):
    """Require a feature to execute a view.

    If the feature is not enabled, the ``not_enabled_view`` will be called
    instead.

    Args:
        feature (djblets.features.feature.Feature):
            The feature that must be enabled.

        not_enabled_view (callable):
            The view that will be called when the feature is not enabled. This
            defaults to a view that returns an :http:`404`.

    Returns:
        callable:
        The decorator.
    """
    if not_enabled_view is None:
        not_enabled_view = _404

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not feature.is_enabled():
                return not_enabled_view(*args, **kwargs)

            return f(*args, **kwargs)

        return decorated

    return decorator
