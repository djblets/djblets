"""Error classes for conditions."""

from __future__ import unicode_literals

from djblets.registries.errors import AlreadyRegisteredError, ItemLookupError


class ConditionChoiceConflictError(AlreadyRegisteredError):
    """A condition choice conflicts with another registered choice."""


class ConditionChoiceNotFoundError(ItemLookupError):
    """A condition choice was not found."""

    def __init__(self, message, condition_index=None, choice_id=None):
        """Initialize the error.

        Args:
            message (unicode):
                The error message.

            condition_index (int, optional):
                The index of the condition this error applies to within
                the condition set.

            choice_id (unicode, optional):
                The ID of the choice that could not be found.
        """
        super(ConditionChoiceNotFoundError, self).__init__(message)

        self.condition_index = condition_index
        self.choice_id = choice_id


class ConditionOperatorConflictError(AlreadyRegisteredError):
    """A condition operator conflicts with another registered operator."""


class ConditionOperatorNotFoundError(ItemLookupError):
    """A condition operator was not found."""

    def __init__(self, message, condition_index=None, operator_id=None):
        """Initialize the error.

        Args:
            message (unicode):
                The error message.

            condition_index (int, optional):
                The index of the condition this error applies to within
                the condition set.

            choice_id (unicode, optional):
                The ID of the operator that could not be found.
        """
        super(ConditionOperatorNotFoundError, self).__init__(message)

        self.condition_index = condition_index
        self.operator_id = operator_id


class InvalidConditionModeError(ValueError):
    """The condition mode provided was invalid."""


class InvalidConditionValueError(ValueError):
    """The condition value provided was invalid."""

    def __init__(self, message, code=None, condition_index=None):
        """Initialize the error.

        Args:
            message (unicode):
                The error message.

            code (unicode, optional):
                The error code. This will generally correspond to a form
                validation error code.

            condition_index (int, optional):
                The index of the condition this error applies to within
                the condition set.
        """
        super(InvalidConditionValueError, self).__init__(message)

        self.code = code
        self.condition_index = condition_index
