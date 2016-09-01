"""Base support and standard choices for conditions."""

from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from djblets.conditions.errors import (ConditionChoiceConflictError,
                                       ConditionChoiceNotFoundError)
from djblets.conditions.operators import (AnyOperator,
                                          ConditionOperators,
                                          ContainsOperator,
                                          DoesNotContainOperator,
                                          DoesNotMatchRegexOperator,
                                          EndsWithOperator,
                                          GreaterThanOperator,
                                          IsNotOneOfOperator,
                                          IsNotOperator,
                                          IsOneOfOperator,
                                          IsOperator,
                                          LessThanOperator,
                                          MatchesRegexOperator,
                                          StartsWithOperator,
                                          UnsetOperator)
from djblets.conditions.values import (ConditionValueBooleanField,
                                       ConditionValueCharField,
                                       ConditionValueIntegerField,
                                       ConditionValueModelField,
                                       ConditionValueMultipleModelField)
from djblets.registries.registry import (ALREADY_REGISTERED,
                                         ATTRIBUTE_REGISTERED, DEFAULT_ERRORS,
                                         NOT_REGISTERED, OrderedRegistry,
                                         UNREGISTER)


class BaseConditionChoice(object):
    """Base class for a choice for a condition.

    A choice is the primary option in a condition. It generally corresponds to
    an object or attribute that would be matched, and contains a human-readable
    name for the choice, a list of operators that pertain to the choice, and
    the default type of field that a user will be using to select a value.

    Attributes:
        extra_state (dict):
            Extra state provided to the choice during construction as keyword
            arguments. This can be useful for condition choices that need more
            advanced logic around value field construction or matching.
    """

    #: The ID of the choice.
    #:
    #: This must be unique within a
    #: :py:class:`~djblets.conditions.conditions.ConditionSet`.
    choice_id = None

    #: The displayed name for the choice.
    name = None

    #: The operators for this choice.
    #:
    #: This must be set to an instance of
    #: :py:class:`~djblets.conditions.operators.ConditionOperators`.
    operators = None

    #: The default field type used to prompt and render fields.
    #:
    #: This value will be the default for all operators, unless otherwise
    #: overridden.
    #:
    #: This must be set to an instance of a
    #: :py:class:`~djblets.conditions.values.BaseConditionValueField` subclass
    #: or a function returning an instance.
    #:
    #: If it's a function, it must accept a ``**kwargs``, for future expansion.
    default_value_field = None

    #: The keyword argument required for condition matching.
    #:
    #: This is the name of the keyword argument that must be provided in order
    #: for this choice to be considered for matching. By default, this expects
    #: a ``value=`` keyword argument to be passed to
    #: :py:meth:`Condition.match
    #: <djblets.conditions.conditions.Condition.match>`, but choices can
    #: specify another name instead.
    #:
    #: This allows multiple choices with different expected values to be used
    #: in the same :py:class:`~djblets.conditions.conditions.ConditionSet`.
    value_kwarg = 'value'

    def __init__(self, **kwargs):
        """Initialize the condition choice.

        Args:
            **kwargs (dict):
                Additional data used for the condition choice. These will be
                available as :py:attr:`extra_state`.
        """
        self.extra_state = kwargs

    def get_operator(self, operator_id):
        """Return an operator instance from this choice with the given ID.

        Instances are not cached. Repeated calls will construct new instances.

        Args:
            operator_id (unicode):
                The ID of the operator to retrieve.

        Returns:
            djblets.conditions.operators.BaseConditionOperator:
            The operator instance matching the ID.

        Raises:
            djblets.conditions.errors.ConditionOperatorNotFoundError:
                No operator was found that matched the given ID.
        """
        return self.operators.get_operator(operator_id, self)

    def get_operators(self):
        """Return a generator for all operator instances for this choice.

        This is a convenience around iterating through all operator classes and
        constructing an instance for each.

        Instances are not cached. Repeated calls will construct new instances.

        Yields:
            djblets.conditions.operators.BaseConditionOperator:
                The operator instance.
        """
        for operator_cls in self.operators:
            yield operator_cls(self)

    def get_match_value(self, value, value_state_cache=None, **kwargs):
        """Return a normalized value used for matching.

        This will take the value provided to the parent
        :py:class:`~djblets.conditions.conditions.Condition` and return either
        that value or some related value.

        It's common for ``value`` to actually be an object, such as a database
        model. In this case, this function may want to return an attribute
        (such as a text attribute) from the object, or an object related to
        this object.

        By default, the value is returned directly.

        Args:
            value (object):
                The value provided to match against.

            value_state_cache (dict):
                An dictionary used to cache common computable data
                that might be shared across instances of one or more
                conditions.

                This can be assumed to be a valid dictionary when called
                in normal usage through condition matching.

            **kwargs (dict):
                Extra keyword arguments passed, for future expansion.

        Returns:
            object:
            The value that this choice's operators will match against.
        """
        return value

    def matches(self, operator, match_value, condition_value,
                value_state_cache, **kwargs):
        """Return whether a value matches this choice and operator.

        This is called internally be
        :py:meth:`~djblets.conditions.conditions.Condition`. It should not
        be called manually.

        Args:
            operator (djblets.conditions.operators.BaseConditionOperator):
                The operator that will perform the match, given this choice's
                match value and the provided condition value.

            match_value (object):
                The value to match against the operator and condition value.
                This will be normalized before being passed to the operator
                for matching.

            condition_value (object):
                The optional value stored in the condition, which the
                operator will use for the match.

            value_state_cache (dict):
                An optional dictionary used to cache common computable data
                that might be shared across instances of one or more
                conditions.

            **kwargs (dict):
                Unused keyword arguments.

        Returns:
            bool:
            ``True`` if the value fulfills this choice and operator.
            ``False`` if it does not.
        """
        return operator.matches(
            match_value=self.get_match_value(
                match_value,
                value_state_cache=value_state_cache),
            condition_value=condition_value)


class ConditionChoiceMatchListItemsMixin(object):
    """Mixin to match against each item in a list instead of the list itself.

    This allows a condition choice to perform an operator match against each
    item a value, instead of performing the match against the value itself.
    It's useful for choices that want to offer, for instance, a string-based
    operator against a list of filenames.

    By default, the match will be considered successful if any item in the
    list matches, and will be considered unsuccessful if no items match.
    Consumers of the mixin can set :py:attr:`require_match_all_items` to
    ``True`` to require all items in the list to match.
    """

    #: Whether all items must match for the choice's match to be successful.
    #:
    #: By default, the match is successful if any item in the list matches.
    #: If ``True``, all items must match.
    require_match_all_items = False

    def matches(self, operator, match_value, condition_value,
                value_state_cache, **kwargs):
        """Return whether a value matches this choice and operator.

        This is called internally be
        :py:meth:`~djblets.conditions.conditions.Condition`. It should not
        be called manually.

        Args:
            operator (djblets.conditions.operators.BaseConditionOperator):
                The operator that will perform the match, given this choice's
                match value and the provided condition value.

            match_value (object):
                The value to match against the operator and condition value.
                This will be normalized before being passed to the operator
                for matching.

            condition_value (object):
                The optional value stored in the condition, which the
                operator will use for the match.

            value_state_cache (dict):
                An optional dictionary used to cache common computable data
                that might be shared across instances of one or more
                conditions.

            **kwargs (dict):
                Unused keyword arguments.

        Returns:
            bool:
            ``True`` if the value fulfills this choice and operator.
            ``False`` if it does not.
        """
        match_value = self.get_match_value(
            match_value,
            value_state_cache=value_state_cache)

        if not match_value:
            return False

        if self.require_match_all_items:
            check_results = all
        else:
            check_results = any

        return check_results(
            operator.matches(match_value=match_item_value,
                             condition_value=condition_value)
            for match_item_value in match_value
        )


class BaseConditionBooleanChoice(BaseConditionChoice):
    """Base class for a standard boolean-based condition choice.

    This is a convenience for choices that cover boolean values.
    """

    operators = ConditionOperators([
        IsOperator,
    ])

    default_value_field = ConditionValueBooleanField()


class BaseConditionIntegerChoice(BaseConditionChoice):
    """Base class for a standard integer-based condition choice.

    This is a convenience for choices that are based on integers. It provides
    some standard operators that work well with integers for checking.
    """

    operators = ConditionOperators([
        IsOperator,
        IsNotOperator,
        GreaterThanOperator,
        LessThanOperator,
    ])

    default_value_field = ConditionValueIntegerField()


class BaseConditionStringChoice(BaseConditionChoice):
    """Base class for a standard string-based condition choice.

    This is a convenience for choices that are based on strings. It provides
    some standard operators that work well with strings for checking.
    """

    operators = ConditionOperators([
        IsOperator,
        IsNotOperator,
        ContainsOperator,
        DoesNotContainOperator,
        StartsWithOperator,
        EndsWithOperator,
        MatchesRegexOperator,
        DoesNotMatchRegexOperator,
    ])

    default_value_field = ConditionValueCharField()


class ModelQueryChoiceMixin(object):
    """A mixin for choices that want to allow for custom querysets.

    This allows subclasses to either define a :py:attr:`queryset` or
    define a more complex queryset by overriding :py:meth:`get_queryset`.
    """

    #: The queryset used for the choice.
    queryset = None

    def get_queryset(self):
        """Return the queryset used for the choice.

        By default, this returns :py:attr:`queryset`. It can be overridden
        to return a more dynamic queryset.

        Returns:
            django.db.query.QuerySet:
            The queryset for the choice.
        """
        if self.queryset is None:
            raise ValueError('%s.queryset cannot be None!'
                             % self.__class__.__name__)

        return self.queryset


class BaseConditionModelChoice(ModelQueryChoiceMixin, BaseConditionChoice):
    """Base class for a standard model-based condition choice.

    This is a convenience for choices that are based on a single model. It
    provides some standard operators that work well with comparing models.

    Subclasses should provide a :py:attr:`queryset` attribute, or override
    :py:meth:`get_queryset` to provide a more dynamic queryset.
    """

    operators = ConditionOperators([
        UnsetOperator,
        IsOperator,
        IsNotOperator,
    ])

    def default_value_field(self, **kwargs):
        """Return the default value field for this choice.

        This will call out to :py:meth:`get_queryset` before returning the
        field, allowing subclasses to simply set :py:attr:`queryset` or to
        perform more dynamic queries before constructing the form field.

        Args:
            **kwargs (dict):
                Extra keyword arguments for this function, for future
                expansion.

        Returns:
            djblets.conditions.values.ConditionValueMultipleModelField:
            The form field for the value.
        """
        return ConditionValueModelField(queryset=self.get_queryset)


class BaseConditionRequiredModelChoice(BaseConditionModelChoice):
    """Base class for a model-based condition that requires a value.

    This is simply a variation on :py:class:`BaseConditionModelChoice` that
    doesn't include a :py:class:`~djblets.conditions.operators.UnsetOperator`.
    """

    operators = ConditionOperators([
        IsOperator,
        IsNotOperator,
    ])


class BaseConditionModelMultipleChoice(ModelQueryChoiceMixin,
                                       BaseConditionChoice):
    """Base class for a standard multi-model-based condition choice.

    This is a convenience for choices that are based on comparing against
    multiple instances of models. It provides some standard operators that work
    well with comparing sets of models.

    Subclasses should provide a :py:attr:`queryset` attribute, or override
    :py:meth:`get_queryset` to provide a more dynamic queryset.
    """

    operators = ConditionOperators([
        AnyOperator.with_overrides(name=_('Any')),
        UnsetOperator.with_overrides(name=_('None')),
        IsOneOfOperator,
        IsNotOneOfOperator,
    ])

    def default_value_field(self, **kwargs):
        """Return the default value field for this choice.

        This will call out to :py:meth:`get_queryset` before returning the
        field, allowing subclasses to simply set :py:attr:`queryset` or to
        perform more dynamic queries before constructing the form field.

        Args:
            **kwargs (dict):
                Extra keyword arguments for this function, for future
                expansion.

        Returns:
            djblets.conditions.values.ConditionValueMultipleModelField:
            The form field for the value.
        """
        return ConditionValueMultipleModelField(queryset=self.get_queryset)


class ConditionChoices(OrderedRegistry):
    """Represents a list of choices for conditions.

    This stores a list of choices that can be used for conditions. It can be
    used in one of two ways:

    1. Created dynamically, taking a list of :py:class:`BaseConditionChoice`
       subclasses as arguments.
    2. Subclassed, with :py:attr:`choice_classes` set to a list of
       :py:class:`BaseConditionChoice` subclasses.

    This works as a :py:ref:`registry <registry-guides>`, allowing additional
    choices to be added dynamically by extensions or other code.
    """

    #: A list of default choices.
    #:
    #: This is only used if a list of choices is not passed to the constructor.
    choice_classes = []

    lookup_attrs = ('choice_id',)
    lookup_error_class = ConditionChoiceNotFoundError
    already_registered_error_class = ConditionChoiceConflictError

    default_errors = dict(DEFAULT_ERRORS, **{
        ALREADY_REGISTERED: _(
            'Could not register condition choice %(item)s: This choice is '
            'already registered or its ID conflicts with another choice.'
        ),
        ATTRIBUTE_REGISTERED: _(
            'Could not register condition choice %(item)s: Another choice '
            '(%(duplicate)s) is already registered with the same ID.'
        ),
        NOT_REGISTERED: _(
            'No condition choice was found matching "%(attr_value)s".'
        ),
        UNREGISTER: _(
            'Could not unregister condition choice %(item)s: This condition '
            'was not yet registered.'
        ),
    })

    def __init__(self, choices=[]):
        """Initialize the list of choices.

        Args:
            choices (list of type, optional):
                A list of :py:class:`BaseConditionChoice` subclasses. If this
                is provided, any value set for :py:attr:`choice_classes` will
                be ignored.
        """
        super(ConditionChoices, self).__init__()

        self._choices = choices or self.choice_classes

    def get_choice(self, choice_id, choice_kwargs={}):
        """Return a choice instance with the given ID.

        Instances are not cached. Repeated calls will construct new instances.

        Args:
            choice_id (unicode):
                The ID of the choice to retrieve.

            choice_kwargs (dict):
                Keyword arguments to pass to the choice's constructor.

        Returns:
            BaseConditionChoice:
            The choice instance matching the ID.

        Raises:
            djblets.conditions.errors.ConditionChoiceNotFoundError:
                No choice was found that matched the given ID.
        """
        choice_cls = self.get('choice_id', choice_id)

        return choice_cls(**choice_kwargs)

    def get_choices(self, choice_kwargs={}):
        """Return a generator for all choice instances.

        This is a convenience around iterating through all choice classes and
        constructing an instance for each.

        Instances are not cached. Repeated calls will construct new instances.

        Args:
            choice_kwargs (dict):
                Keyword arguments to pass to each choice's constructor.

        Yields:
            BaseConditionChoice:
            The choice instance.
        """
        for choice_cls in self:
            yield choice_cls(**choice_kwargs)

    def get_defaults(self):
        """Return the default choices for the list.

        This is used internally by the parent registry class, and is based on
        the list of choices provided to the constructor or the value for
        :py:attr:`choice_classes`.

        Returns:
            list of type:
            The default list of choices.
        """
        return self._choices
