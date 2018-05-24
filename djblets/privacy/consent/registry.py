"""Registry for things that require consent from a user."""

from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from djblets.privacy.consent.errors import (ConsentRequirementConflictError,
                                            ConsentRequirementNotFoundError)
from djblets.registries.registry import (ALREADY_REGISTERED,
                                         ATTRIBUTE_REGISTERED,
                                         DEFAULT_ERRORS,
                                         OrderedRegistry,
                                         UNREGISTER)


_registry = None


class ConsentRequirementsRegistry(OrderedRegistry):
    """A registry for managing aspects of a product requiring consent.

    Each requirement in the registry requires consent by the user before the
    action or processing for that requirement is allowed to occur.
    """

    lookup_attrs = ('requirement_id',)
    already_registered_error_class = ConsentRequirementConflictError
    lookup_error_class = ConsentRequirementNotFoundError

    default_errors = dict(DEFAULT_ERRORS, **{
        ALREADY_REGISTERED: _(
            'Could not register consent requirement %(item)s: This '
            'requirement is already registered or its ID conflicts with '
            'another consent requirement.',
        ),
        ATTRIBUTE_REGISTERED: _(
            'Could not register consent requirement %(item)s: Another '
            'requirement (%(duplicate)s) is already registered with the '
            'same ID.',
        ),
        UNREGISTER: _(
            'Could not unregister consent requirement %(item)s: This '
            'requirement was not yet registered.',
        ),
    })

    def get_consent_requirement(self, requirement_id):
        """Return a consent requirement with the given ID.

        Args:
            requirement_id (unicode):
                The consent requirement ID to look up.

        Returns:
            djblets.privacy.consent.base.BaseConsentRequirement:
            The resulting consent requirement, if found. If a requirement
            with this ID could not be found, this will return ``None``.
        """
        try:
            return self.get('requirement_id', requirement_id)
        except ConsentRequirementNotFoundError:
            return None


def get_consent_requirements_registry():
    """Return the registry for managing consent requirements.

    Returns:
        ConsentRequirementsRegistry:
        The registry for consent requirements.
    """
    global _registry

    if _registry is None:
        _registry = ConsentRequirementsRegistry()

    return _registry
