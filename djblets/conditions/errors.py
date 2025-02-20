"""Error classes for conditions."""

from __future__ import annotations

from typing import Optional

from djblets.registries.errors import AlreadyRegisteredError, ItemLookupError


class ConditionChoiceConflictError(AlreadyRegisteredError):
    """A condition choice conflicts with another registered choice."""


class ConditionChoiceNotFoundError(ItemLookupError):
    """A condition choice was not found.

    Version Changed:
        5.3:
        Added support for Python type hints.
    """

    ######################
    # Instance variables #
    ######################

    #: The ID of the choice that could not be found.
    choice_id: Optional[str]

    #: The index of the condition this error applies to within the set.
    condition_index: Optional[int]

    def __init__(
        self,
        message: str,
        condition_index: Optional[int] = None,
        choice_id: Optional[str] = None,
    ) -> None:
        """Initialize the error.

        Args:
            message (str):
                The error message.

            condition_index (int, optional):
                The index of the condition this error applies to within
                the condition set.

            choice_id (str, optional):
                The ID of the choice that could not be found.
        """
        super().__init__(message)

        self.condition_index = condition_index
        self.choice_id = choice_id


class ConditionOperatorConflictError(AlreadyRegisteredError):
    """A condition operator conflicts with another registered operator."""


class ConditionOperatorNotFoundError(ItemLookupError):
    """A condition operator was not found.

    Version Changed:
        5.3:
        Added support for Python type hints.
    """

    ######################
    # Instance variables #
    ######################

    #: The index of the condition this error applies to within the set.
    condition_index: Optional[int]

    #: The ID of the operator that could not be found.
    operator_id: Optional[str]

    def __init__(
        self,
        message: str,
        condition_index: Optional[int] = None,
        operator_id: Optional[str] = None,
    ) -> None:
        """Initialize the error.

        Args:
            message (str):
                The error message.

            condition_index (int, optional):
                The index of the condition this error applies to within
                the condition set.

            operator_id (str, optional):
                The ID of the operator that could not be found.
        """
        super().__init__(message)

        self.condition_index = condition_index
        self.operator_id = operator_id


class InvalidConditionModeError(ValueError):
    """The condition mode provided was invalid."""


class InvalidConditionValueError(ValueError):
    """The condition value provided was invalid.

    Version Changed:
        5.3:
        Added support for Python type hints.
    """

    ######################
    # Instance variables #
    ######################

    #: The error code.
    #:
    #: This will generally correspond to a form validation error code.
    code: Optional[str]

    #: The index of the condition this error applies to within the set.
    condition_index: Optional[int]

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        condition_index: Optional[int] = None,
    ) -> None:
        """Initialize the error.

        Args:
            message (str):
                The error message.

            code (str, optional):
                The error code. This will generally correspond to a form
                validation error code.

            condition_index (int, optional):
                The index of the condition this error applies to within
                the condition set.
        """
        super().__init__(message)

        self.code = code
        self.condition_index = condition_index
