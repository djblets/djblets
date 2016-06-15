from __future__ import unicode_literals

from djblets.features.checkers import get_feature_checker
from djblets.features.level import FeatureLevel
from djblets.features.registry import get_features_registry


class Feature(object):
    """A feature in a product that can dynamically be turned on/off.

    Feature subclasses are used to provide dynamic access to a given feature in
    a product. The feature may appear off for most users but on for a select
    few, or only on in a development server, for instance.

    Whether a feature is enabled is controlled by the :py:attr:`stability level
    <level>` of the feature and by the :py:class:`feature checker
    <djblets.features.checkers.BaseFeatureChecker>`. It will be enabled if
    :py:attr:`level` is :py:attr:`~FeatureLevel.STABLE` or if the feature
    checker returns that the feature is enabled.

    Consuming applications are expected to subclass this and define the
    information on the feature, and choose a feature checker to use.
    """

    #: The unique ID/slug of the feature.
    feature_id = None

    #: The name of the feature.
    name = None

    #: A summary of the feature.
    summary = None

    #: Stability level of the feature.
    level = FeatureLevel.EXPERIMENTAL

    def __init__(self, register=True):
        """Initialize the feature.

        Subclasses that wish to provide special initialization should instead
        override :py:meth:`initialize`.

        Args:
            register (bool, optional):
                Whether to register this feature instance. This should
                generally be ``True`` for all callers, except in special cases
                (like unit tests).

        Raises:
            djblets.features.errors.FeatureConflictError:
                The feature ID on this class conflicts with another feature.
        """
        if register:
            get_features_registry().register(self)

    def initialize(self):
        """Initialize the feature.

        Subclasses that wish to initialize feature logic within the class (such
        as connecting to signals) should do so by overriding this method.

        This will always be called when instantiating the subclass, or when
        re-registering an unregistered feature class using the
        :py:data:`~djblets.features.registry.features` registry.
        """
        pass

    def shutdown(self):
        """Shut down the feature.

        Subclasses that wish to provide special shutdown logic within the class
        (such as disconnecting from signals) should do so by overriding this
        method.

        This is called when unregistering the feature through the
        :py:data:`~djblets.features.registry.features` registry.
        """
        pass

    def is_enabled(self, **kwargs):
        """Return whether the feature is enabled for the given requirements.

        This will return a boolean indicating if the feature is enabled.

        If :py:attr:`level` is :py:attr:`~FeatureLevel.STABLE`, it will always
        be enabled. Otherwise, if :py:attr:`level` is not
        :py:attr:`~FeatureLevel.UNAVAILABLE`, the configured feature checker
        will be used instead.

        Callers can pass additional keyword arguments to this method, which
        the feature checker can use when determining if the feature is enabled.
        For example, a :py:class:`~django.http.HttpRequest` instance, or a
        :py:class:`~django.contrib.auth.models.User`.

        Args:
            **kwargs (dict):
                Additional keyword arguments to pass to the feature checker.

        Returns:
            bool:
            A boolean value indicating if the feature is enabled for the given
            conditions.
        """
        if self.level <= FeatureLevel.UNAVAILABLE:
            return False

        checker = get_feature_checker()
        assert checker

        return (self.level >= checker.min_enabled_level or
                checker.is_feature_enabled(self.feature_id, **kwargs))
