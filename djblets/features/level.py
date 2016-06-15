from __future__ import unicode_literals


class FeatureLevel(object):
    """Possible stability levels for features."""

    #: The feature is completely unavailable.
    #:
    #: Feature checkers will not be consulted in this case.
    UNAVAILABLE = 0

    #: The feature is experimental.
    #:
    #: A feature checker must enable this feature.
    EXPERIMENTAL = 10

    #: The feature is in beta.
    #:
    #: A feature checker must enable this feature.
    BETA = 50

    #: The feature is stable and will always be enabled.
    STABLE = 100
