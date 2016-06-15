"""Registry for managing feature registrations."""

from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from djblets.features.errors import FeatureConflictError, FeatureNotFoundError
from djblets.registries.registry import (ALREADY_REGISTERED,
                                         ATTRIBUTE_REGISTERED, DEFAULT_ERRORS,
                                         RegistrationError, Registry,
                                         UNREGISTER)


FEATURE_DEFAULT_ERRORS = DEFAULT_ERRORS.copy()
FEATURE_DEFAULT_ERRORS.update({
    ALREADY_REGISTERED: _(
        'Could not register feature %(item)s: This feature is already '
        'registered or its ID conflicts with another feature.',
    ),
    ATTRIBUTE_REGISTERED: _(
        'Could not register feature %(item)s: Another feature (%(duplicate)s) '
        'is already registered with the same feature ID.',
    ),
    UNREGISTER: _(
        'Could not unregister feature %(item)s: This feature was not yet '
        'registered.',
    ),
})


_registry = None


class FeaturesRegistry(Registry):
    """A registry for instantiated features.

    This manages all instances of :py:class:`~djblets.features.feature.Feature`
    subclasses that the product has created, providing easy access to features
    for checking purposes.
    """

    lookup_attrs = ('feature_id',)
    default_errors = FEATURE_DEFAULT_ERRORS
    already_registered_error_class = FeatureConflictError
    lookup_error_class = FeatureNotFoundError

    def register(self, feature):
        """Register a feature instance.

        The feature's :py:meth:`~djblets.features.feature.Feature.initialize`
        method will be called once registered.

        Args:
            feature (djblets.features.feature.Feature):
                The feature to register.

        Raises:
            djblets.features.errors.FeatureConflictError:
                The feature's ID conflicts with another feature class.

            djblets.registries.errors.RegistrationError:
                The feature ID wasn't set on the class.
        """
        if not feature.feature_id:
            raise RegistrationError("The feature class's ID must be set.")

        feature.initialize()

        super(FeaturesRegistry, self).register(feature)

    def unregister(self, feature):
        """Unregister a feature instance.

        The feature's :py:meth:`~djblets.features.feature.Feature.shutdown`
        method will be called once unregistered.

        Args:
            feature (djblets.features.feature.Feature):
                The feature to unregister.

        Raises:
            djblets.features.errors.FeatureNotFoundError:
                Raised if the feature was not already registered.
        """
        super(FeaturesRegistry, self).unregister(feature)

        feature.shutdown()

    def get_feature(self, feature_id):
        """Return the feature instance with the given ID.

        Args:
            feature_id (unicode):
                The ID of the feature to return.

        Returns:
            djblets.features.feature.Feature:
            The feature instance matching the ID or ``None`` if not found.
        """
        try:
            return self.get('feature_id', feature_id)
        except FeatureNotFoundError:
            return None


def get_features_registry():
    """Return the global features registry.

    The first time this is called, a :py:class:`FeaturesRegistry` will be
    instantiated and cached for future calls.

    Returns:
        FeaturesRegistry:
        The features registry.
    """
    global _registry

    if _registry is None:
        _registry = FeaturesRegistry()

    return _registry
