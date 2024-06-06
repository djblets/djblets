"""Support for handling deprecations.

The version-specific objects in this module are not considered stable between
releases, and may be removed at any point.

Version Changed:
    4.0:
    Projects should now use :pypi:`housekeeping` to manage their own
    deprecations, instead of using this module.
"""

from __future__ import annotations

from typing import Any, Callable, Optional, Type

from housekeeping import (
    BasePendingRemovalWarning,
    BaseRemovedInWarning,
    deprecated_arg_value as djblets_deprecated_arg_value,
    deprecate_non_keyword_only_args as djblets_deprecate_non_keyword_only_args,
    func_moved)
from housekeeping.functions import _FuncT
from housekeeping.helpers import LazyObject


class BaseRemovedInProductVersionWarning(BaseRemovedInWarning):
    """Base class for product deprecation warnings.

    This can be used by consumers of Djblets to provide similar deprecation
    functionality, making use of deprecation utility functions.

    Deprecated:
        4.0:
        Consumers should subclass :py:class:`housekeeping.BaseRemovedInWarning`
        instead. This class will be removed in Djblets 6.

    Version Added:
        3.2
    """


class PendingRemovalInDjbletsWarning(BasePendingRemovalWarning):
    """Pending deprecation for code in Djblets.

    Version Added:
        4.0
    """

    # Don't warn that we're subclassing BaseRemovedInProductVersionWarning,
    # which is needed to continue being able to catch warnings in a generic
    # fashion. This can be removed in Djblets 6.
    housekeeping_skip_warning = True

    product = 'Djblets'


class BaseRemovedInDjbletsVersionWarning(BaseRemovedInProductVersionWarning):
    """Base class for a Djblets deprecation warning.

    All version-specific deprecation warnings inherit from this, allowing
    callers to check for Djblets deprecations without being tied to a specific
    version.
    """

    product = 'Djblets'


class RemovedInDjblets60Warning(BaseRemovedInDjbletsVersionWarning):
    """Deprecations for features scheduled for removal in Djblets 6.0.

    Note that this class will itself be removed in Djblets 6.0. If you need to
    check against Djblets deprecation warnings, please see
    :py:class:`BaseRemovedInDjbletsVersionWarning`.
    """

    version = '6.0'


class RemovedInDjblets70Warning(BaseRemovedInDjbletsVersionWarning):
    """Deprecations for features scheduled for removal in Djblets 7.0.

    Note that this class will itself be removed in Djblets 7.0. If you need to
    check against Djblets deprecation warnings, please see
    :py:class:`BaseRemovedInDjbletsVersionWarning`.
    """

    version = '7.0'


#: An alias for the next release of Djblets where features would be removed.
RemovedInNextDjbletsVersionWarning = RemovedInDjblets60Warning


@func_moved(RemovedInDjblets60Warning,
            new_func=djblets_deprecated_arg_value)
def deprecated_arg_value(
    owner_name: str,
    value: Any,
    old_arg_name: str,
    new_arg_name: Optional[str] = None,
    warning_cls: Type[BaseRemovedInWarning] = BaseRemovedInWarning,
) -> LazyObject:
    """Wrap a value in a lazy object to warn when used.

    Deprecated:
        4.0:
        Consumers should use :py:func:`housekeeping.deprecated_arg_value`
        instead.

    Version Changed:
        3.2:
        Specifying a :py:class:`BaseRemovedInProductVersionWarning` subclass
        will now result in product/version information in the warning message.

    Args:
        owner_name (str):
            The name of the owner of this argument.

        value (object):
            The argument value.

        old_arg_name (str):
            The name of the argument that was deprecated.

        new_arg_name (str, optional):
            The optional name of the argument to use in the deprecated
            argument's place, if one is available.

        warning_cls (type, optional):
            The class to use for the warning. This should be
            :py:exc:`DeprecationWarning`, :py:exc:`PendingDeprecationWarning`,
            or a subclass of one.

            If a :py:class:`BaseRemovedInProductVersionWarning` subclass is
            provided, the error message will include warning information.
            This is recommended and may be required in a future version.

    Returns:
        django.utils.functional.SimpleLazyObject:
        The value wrapped in a lazy object. The first time it is accessed,
        a warning will be emitted.
    """
    return djblets_deprecated_arg_value(warning_cls=warning_cls,
                                        owner_name=owner_name,
                                        value=value,
                                        old_name=old_arg_name,
                                        new_name=new_arg_name)


@func_moved(RemovedInDjblets60Warning,
            new_func=djblets_deprecate_non_keyword_only_args)
def deprecate_non_keyword_only_args(
    warning_cls: Type[BaseRemovedInProductVersionWarning],
    message: Optional[str] = None,
) -> Callable[[_FuncT], _FuncT]:
    """Deprecate calls passing keyword-only arguments as positional arguments.

    This decorator allows code transitioning to keyword-only arguments to
    continue working when passing values as positional arguments.

    Upon the first call, it will record information about the signature of the
    function and then compare that to any future calls. If any positional
    argument values are passed to keyword-only arguments, the arguments will
    be rewritten to work correctly, and a deprecation warning will be emitted.

    Deprecated:
        4.0:
        Consumers should use
        :py:func:`housekeeping.deprecate_non_keyword_only_args`
        instead.

    Version Added:
        3.2

    Args:
        warning_cls (type):
            The specific deprecation warning class to use. This must be a
            subclass of :py:exc:`DeprecationWarning`.

        message (str, optional):
            An optional message to use instead of the default.

    Returns:
        callable:
        The function decorator.

    Raises:
        AssertionError:
            The function being called does not provide keyword-only arguments.
    """
    return djblets_deprecate_non_keyword_only_args(warning_cls=warning_cls,
                                                   message=message)
