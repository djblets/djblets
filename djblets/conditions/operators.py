"""Base support and standard operators for condition choices."""

from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from djblets.conditions.errors import (ConditionOperatorConflictError,
                                       ConditionOperatorNotFoundError)
from djblets.registries.registry import (ALREADY_REGISTERED,
                                         ATTRIBUTE_REGISTERED, DEFAULT_ERRORS,
                                         NOT_REGISTERED, OrderedRegistry,
                                         UNREGISTER)


class BaseConditionOperator(object):
    """Base class for an operator for a condition choice.

    An operator forms an expression along with a parent
    :py:class:`~djblets.conditions.choices.BaseConditionChoice` and an optional
    value. This expression can be used by the condition to determine if a
    caller-provided value satisfies the condition.

    Choices will usually have more than one operator registered. Depending on
    the operator, there may or may not be a field for a value.

    Attributes:
        choice (djblets.conditions.choices.BaseConditionChoice):
            The choice owning the instance of this operation.
    """

    #: The ID of the operator.
    #:
    #: This must be unique within a
    #: :py:class:`~djblets.conditions.choices.BaseConditionChoice`.
    operator_id = None

    #: The displayed name for the operator.
    name = None

    def __init__(self, choice):
        """Initialize the operator.

        Args:
            choice (djblets.conditions.choices.BaseConditionChoice):
                The choice owning the instance of this operator.
        """
        self.choice = choice

    @property
    def value_field(self):
        """The field type used to prompt and render fields.

        By default, this will use the default one for the choice. The field
        can be disabled by setting this to ``None``, or a different field can
        be used by setting it to an instance of a
        :py:class:`~djblets.conditions.values.BaseConditionValueField`
        subclass.
        """
        return self.choice.default_value_field

    @property
    def has_custom_value_field(self):
        """Whether the operator has a custom value field."""
        return self.value_field is not self.choice.default_value_field

    def matches(self, lookup_value, stored_value):
        """Return whether a value matches the operator and condition's value.

        This must be implemented by subclasses.

        Args:
            lookup_value (object):
                The caller's value to check against the state for this
                operator.

            condition_value (object):
                The value stored as part of the condition to check against.
                This will only be used if the operator has a value field
                associated.

        Returns:
            bool:
            ``True`` if the lookup value fulfills the condition. ``False`` if
            it does not.

        Raises:
            TypeError:
                Either the lookup or condition value or types was not
                compatible with the expression.
        """
        raise NotImplementedError


class ConditionOperators(OrderedRegistry):
    """Represents a list of operators for a condition choice.

    This stores a list of operators that can be used for condition choices.
    It can be used in one of two ways:

    1. Created dynamically, taking a list of :py:class:`BaseConditionOperator`
       subclasses as arguments.
    2. Subclassed, with :py:attr:`operator_classes` set to a list of
       :py:class:`BaseConditionOperator` subclasses.

    This works as a :py:ref:`registry <registry-guides>`, allowing additional
    choices to be added dynamically by extensions or other code.
    """

    #: A list of default operators.
    #:
    #: This is only used if a list of operators is not passed to the
    #: constructor.
    operator_classes = []

    lookup_attrs = ('operator_id',)
    lookup_error_class = ConditionOperatorNotFoundError
    already_registered_error_class = ConditionOperatorConflictError

    default_errors = dict(DEFAULT_ERRORS, **{
        ALREADY_REGISTERED: _(
            'Could not register condition operator %(item)s: This operator is '
            'already registered or its ID conflicts with another operator.'
        ),
        ATTRIBUTE_REGISTERED: _(
            'Could not register condition operator %(item)s: Another operator '
            '%(duplicate)s) is already registered with the same ID.'
        ),
        NOT_REGISTERED: _(
            'No operator was found matching "%(attr_value)s".'
        ),
        UNREGISTER: _(
            'Could not unregister condition operator %(item)s: This condition '
            'was not yet registered.'
        ),
    })

    def __init__(self, operators=[], *args, **kwargs):
        """Initialize the list of operators.

        Args:
            operators (list of type, optional):
                A list of :py:class:`BaseConditionOperator` subclasses. If this
                is provided, any value set for :py:attr:`operator_classes` will
                be ignored.
        """
        super(ConditionOperators, self).__init__(*args, **kwargs)

        self._operators = operators or self.operator_classes

    def get_operator(self, operator_id, choice):
        """Return an operator instance with the given ID.

        Args:
            operator_id (unicode):
                The ID of the operator to retrieve.

            choice (djblets.conditions.choices.BaseConditionChoice):
                The choice that will own this operator instance.

        Returns:
            BaseConditionOperator:
            The operator instance matching the ID.

        Raises:
            djblets.conditions.errors.ConditionOperatorNotFoundError:
                No operator was found that matched the given ID.
        """
        operator_cls = self.get('operator_id', operator_id)

        return operator_cls(choice)

    def get_defaults(self):
        """Return the default operators for the list.

        This is used internally by the parent registry classa, and is based on
        the list of operators provided to the constructor or the value for
        :py:attr:`operator_classes`.

        Returns:
            list of type:
            The default list of operators.
        """
        return self._operators
