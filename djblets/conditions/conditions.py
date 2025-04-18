"""Conditions and sets of conditions."""

from __future__ import annotations

import logging
from typing import Any, Iterable, Iterator, Optional, TYPE_CHECKING

from django.utils.translation import gettext as _
from typing_extensions import Final, NotRequired, TypedDict

from djblets.conditions.errors import (ConditionChoiceNotFoundError,
                                       ConditionOperatorNotFoundError,
                                       InvalidConditionModeError,
                                       InvalidConditionValueError)

if TYPE_CHECKING:
    from djblets.conditions.choices import (BaseConditionChoice,
                                            ConditionChoices)
    from djblets.conditions.operators import BaseConditionOperator
    from djblets.conditions.values import ValueStateCache
    from djblets.util.typing import KwargsDict


logger = logging.getLogger(__name__)


class ConditionData(TypedDict):
    """Serialization data for conditions.

    Version Added:
        5.3
    """

    #: The ID of the registered condition choice.
    choice: str

    #: The ID of the registered condition operator.
    op: str

    #: The value stored for the condition.
    value: NotRequired[Any]


class ConditionSetData(TypedDict):
    """Serialization data for condition sets.

    Version Added:
        5.3
    """

    #: The list of serialized conditions in the set.
    conditions: list[ConditionData]

    #: The matching mode for the condition set.
    mode: NotRequired[str]


class Condition:
    """A condition used to match state to a choice, operator, and value.

    Conditions store a choice, operator, and value (depending on the operator).
    Callers can query whether a value fulfills a given condition, making it
    easy for users to compose sets of rules safely for controlling behavior
    in an application without having to write any code.

    Generally, queries will be made against a :py:class:`ConditionSet`, instead
    of an individual Condition.

    Version Changed:
        5.3:
        Added support for Python type hints.
    """

    ######################
    # Instance variables #
    ######################

    #: The choice stored for this condition.
    choice: BaseConditionChoice

    #: The operator stored for this condition.
    operator: BaseConditionOperator

    #: The raw (serialized) value for this condition.
    #:
    #: This is used internally, and won't usually be needed by a caller.
    raw_value: Any

    #: The value stored for this condition.
    value: Any

    @classmethod
    def deserialize(
        cls,
        choices: ConditionChoices,
        data: ConditionData,
        condition_index: Optional[int] = None,
        choice_kwargs: KwargsDict = {},
    ) -> Condition:
        """Deserialize a condition from serialized data.

        This expects data serialized by :py:meth:`serialize`.

        Args:
            choices (djblets.conditions.choices.ConditionChoices):
                Possible choices for the condition.

            data (dict):
                Serialized data representing this condition.

            condition_index (int, optional):
                The index of the condition within the set of conditions.
                This is used for exceptions to help identify which condition
                failed during deserialization.

        Returns:
            djblets.conditions.conditions.Condition:
            The deserialized condition.

        Raises:
            djblets.conditions.errors.ConditionChoiceNotFoundError:
                The choice ID referenced in the data was missing or did not
                match a valid choice.

            djblets.conditions.errors.ConditionOperatorNotFoundError:
                The operator ID referenced in the data was missing or did not
                match a valid operator for the choice.

            djblets.conditions.errors.InvalidConditionValueError:
                The value was missing from the payload data or was not valid
                for the choice and operator.
        """
        # Sanity-check that we have the data we expect.
        try:
            choice_id = data['choice']
        except KeyError:
            logger.debug('Condition.deserialize: Missing "choice" key for '
                         'condition %r',
                         data)

            raise ConditionChoiceNotFoundError(
                _('A choice is required.'),
                condition_index=condition_index)

        try:
            operator_id = data['op']
        except KeyError:
            logger.debug('Condition.deserialize: Missing "op" key for '
                         'condition %r',
                         data)

            raise ConditionOperatorNotFoundError(
                _('An operator is required.'),
                condition_index=condition_index)

        # Load the choice.
        try:
            choice = choices.get_choice(choice_id, choice_kwargs=choice_kwargs)
        except ConditionChoiceNotFoundError as e:
            logger.debug('Condition.deserialize: Invalid "choice" value '
                         '"%s" for condition %r',
                         choice_id, data)

            raise ConditionChoiceNotFoundError(
                str(e),
                choice_id=choice_id,
                condition_index=condition_index)

        # Load the operator.
        try:
            operator = choice.get_operator(operator_id)
        except ConditionOperatorNotFoundError as e:
            logger.debug('Condition.deserialize: Invalid "op" value "%s" '
                         'for condition %r',
                         operator_id, data)

            raise ConditionOperatorNotFoundError(
                str(e),
                operator_id=operator_id,
                condition_index=condition_index)

        # Load the value.
        raw_value: Any = None
        value: Any = None

        if operator.value_field is not None:
            try:
                raw_value = data['value']
                value = operator.value_field.deserialize_value(raw_value)
            except KeyError:
                logger.debug('Condition.deserialize: Missing "value" value '
                             'for condition %r',
                             data)

                raise InvalidConditionValueError(
                    _('A value is required.'),
                    condition_index=condition_index)
            except InvalidConditionValueError as e:
                logger.debug('Condition.deserialize: Invalid "value" value '
                             '%r for condition %r',
                             raw_value, data)

                e.condition_index = condition_index

                raise

        return cls(choice=choice,
                   operator=operator,
                   value=value,
                   raw_value=raw_value)

    def __init__(
        self,
        choice: BaseConditionChoice,
        operator: BaseConditionOperator,
        value: Any = None,
        raw_value: Any = None,
    ) -> None:
        """Initialize the condition.

        Args:
            choice (djblets.conditions.choices.BaseConditionChoice):
                The choice for this condition.

            operator (djblets.conditions.operators.BaseConditionOperator):
                The operator for this condition.

            value (object, optional):
                The value for this condition.

            raw_value (object, optional):
                The raw (serialized) value for this condition.
        """
        self.choice = choice
        self.operator = operator
        self.value = value

        if raw_value is None:
            self.raw_value = value
        else:
            self.raw_value = raw_value

    def matches(
        self,
        value: Any,
        value_state_cache: Optional[ValueStateCache] = None,
    ) -> bool:
        """Return whether a value matches the condition.

        Args:
            value (object):
                The value to match against.

            value_state_cache (dict):
                An optional dictionary used to cache common computable data
                that might be shared across instances of one or more
                conditions.

        Returns:
            bool:
            ``True`` if the value fulfills the condition. ``False`` if it
            does not.
        """
        if value_state_cache is None:
            value_state_cache = {}

        return self.choice.matches(operator=self.operator,
                                   match_value=value,
                                   condition_value=self.value,
                                   value_state_cache=value_state_cache)

    def serialize(self) -> ConditionData:
        """Serialize the condition to a JSON-serializable dictionary.

        Returns:
            dict:
            A dictionary representing the condition. It can be safely
            serialized to JSON.
        """
        choice_id = self.choice.choice_id
        operator_id = self.operator.operator_id

        assert choice_id is not None
        assert operator_id is not None

        data: ConditionData = {
            'choice': choice_id,
            'op': operator_id,
        }

        if self.operator.value_field is not None:
            if self.value is None:
                value = None
            else:
                value = self.operator.value_field.serialize_value(self.value)

            data['value'] = value

        return data

    # Make this serializable in a DjbletsJSONEncoder.
    to_json = serialize


class ConditionSet:
    """A set of conditions used to match state and define rules.

    Condition sets own multiple conditions, and are given a mode indicating
    how to query state against those conditions. They're also responsible
    for serializing and deserializing all data around a set of conditions to
    a JSON-serializable format.

    If using :py:attr:`MODE_ALL`, then all conditions must be satisfied for a
    condition set to pass.  If using :py:attr:`MODE_ANY`, then only one
    condition must be satisfied.

    Version Changed:
        5.3:
        Added support for Python type hints.
    """

    #: Always match without conditions.
    MODE_ALWAYS: Final[str] = 'always'

    #: All conditions must match a value to satisfy the condition set.
    MODE_ALL: Final[str] = 'all'

    #: Any condition may match a value to satisfy the condition set.
    MODE_ANY: Final[str] = 'any'

    #: A set of all the valid modes.
    CONDITIONS: Final = (MODE_ALWAYS, MODE_ALL, MODE_ANY)

    #: The default mode.
    DEFAULT_MODE: Final = MODE_ALL

    ######################
    # Instance variables #
    ######################

    #: The list of conditions that comprise this set.
    conditions: list[Condition]

    #: The matching mode for the condition set.
    #:
    #: This is one of :py:attr:`MODE_ALL` or :py:attr:`MODE_ANY`.
    mode: str

    @classmethod
    def deserialize(
        cls,
        choices: ConditionChoices,
        data: ConditionSetData,
        choice_kwargs: KwargsDict = {},
    ) -> ConditionSet:
        """Deserialize a set of conditions from serialized data.

        This expects data serialized by :py:meth:`deserialize`.

        Args:
            choices (djblets.conditions.choices.ConditionChoices):
                Possible choices for the condition set.

            data (dict):
                Serialized data representing this condition set.

        Returns:
            djblets.conditions.conditions.ConditionSet:
            The deserialized condition set.

        Raises:
            djblets.conditions.errors.ConditionChoiceNotFoundError:
                The choice ID referenced in the data was missing or did not
                match a valid choice in a condition.

            djblets.conditions.errors.ConditionOperatorNotFoundError:
                The operator ID referenced in the data was missing or did not
                match a valid operator for the choice in a condition.

            djblets.conditions.errors.InvalidConditionValueError:
                The value was missing from the payload data or was not valid
                for the choice and operator in a condition.

            djblets.conditions.errors.InvalidConditionModeError:
                The stored match mode was missing or was not a valid mode.
        """
        mode = data.get('mode')

        if mode not in cls.CONDITIONS:
            logger.debug('ConditionSet.deserialize: Invalid "mode" value '
                         '"%s" for condition set %r',
                         mode, data)

            raise InvalidConditionModeError(
                _('"%s" is not a valid condition mode.')
                % mode)

        return cls(mode, [
            Condition.deserialize(choices, condition_data, i, choice_kwargs)
            for i, condition_data in enumerate(data.get('conditions', []))
        ])

    def __init__(
        self,
        mode: str = DEFAULT_MODE,
        conditions: list[Condition] = [],
    ) -> None:
        """Initialize the condition set.

        Args:
            mode (str, optional):
                The match mode. This defaults to :py:attr:`MODE_ALL`.

            conditions (list, optional):
                The conditions that make up this set. This defaults to an
                empty list.

        Raises:
            djblets.conditions.errors.InvalidConditionModeError:
                The match mode is not a valid mode.
        """
        if mode not in self.CONDITIONS:
            raise InvalidConditionModeError(
                _('"%s" is not a valid condition mode.')
                % mode)

        self.mode = mode
        self.conditions = conditions

    def matches(self, **values) -> bool:
        """Check if a value matches the condition set.

        Depending on the mode of the condition set, this will either require
        all conditions to match, or only one.

        Args:
            **values (dict):
                Values to match against. By default, condition choices
                will match against a single ``value`` keyword argument, but
                more specialized uses might take into account one or more
                other keyword arguments.

        Returns:
            bool:
            ``True`` if the value fulfills the condition set. ``False`` if it
            does not.
        """
        if self.mode == self.MODE_ALWAYS:
            match_conditions = lambda x: True
        elif self.mode == self.MODE_ALL:
            match_conditions = self._match_all
        elif self.mode == self.MODE_ANY:
            match_conditions = any
        else:
            # We shouldn't be here, unless someone set the mode to a bad value
            # after creating the condition set.
            raise ValueError('Invalid condition mode %r' % self.mode)

        return match_conditions(self._get_condition_results(self.conditions,
                                                            values))

    def serialize(self) -> ConditionSetData:
        """Serialize the condition set to a JSON-serializable dictionary.

        Returns:
            dict:
            A dictionary representing the condition set. It can be safely
            serialized to JSON.
        """
        return {
            'mode': self.mode,
            'conditions': [
                condition.serialize()
                for condition in self.conditions
            ],
        }

    # Make this serializable in a DjbletsJSONEncoder.
    to_json = serialize

    def _get_condition_results(
        self,
        conditions: list[Condition],
        values: KwargsDict,
    ) -> Iterator[bool]:
        """Yield the results from each condition match.

        This will iterate through all the conditions, running a match against
        the provided values, yielding each result.

        If a condition expects a particular value that's not provided in
        ``values``, it will evaluate as a false match.

        Args:
            conditions (list of djblets.conditions.condition.Condition):
                The conditions to iterate through.

            values (dict):
                The dictionary of values to match against.

        Yields:
            bool:
            The result of each condition match.
        """
        value_state_cache: ValueStateCache = {}

        for condition in conditions:
            value_kwarg = condition.choice.value_kwarg

            if value_kwarg in values:
                yield condition.matches(values[value_kwarg],
                                        value_state_cache=value_state_cache)
            else:
                yield False

    def _match_all(
        self,
        results: Iterable[bool],
    ) -> bool:
        """Return whether all results are truthy and the list is non-empty.

        This works similarly to :py:func:`all`, but will return ``False`` if
        the provided list is empty.

        Args:
            results (generator):
                The condition results to iterate through.

        Returns:
            bool:
            ``True`` if there are condition results present and they all
            evaluate to ``True``. ``False`` otherwise.
        """
        found = False

        for result in results:
            if not result:
                return False

            found = True

        return found
