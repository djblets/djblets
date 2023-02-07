"""Support for handling deprecations.

The version-specific objects in this module are not considered stable between
releases, and may be removed at any point.

The base objects are considered stable.
:py:class:`BaseRemovedInProductVersionWarning` and the utility functions can
be used by consumers to manage their own deprecations.
"""

from __future__ import annotations

import inspect
import warnings
from functools import wraps
from typing import (Any, Callable, Dict, List, Optional, Tuple, Type, TypeVar,
                    cast)

from django.utils.functional import SimpleLazyObject


_FuncT = TypeVar('_FuncT', bound=Callable[..., Any])


class BaseRemovedInProductVersionWarning(DeprecationWarning):
    """Base class for product deprecation warnings.

    This can be used by consumers of Djblets to provide similar deprecation
    functionality, making use of deprecation utility functions.

    Version Added:
        3.2
    """

    #: The product in which this warning pertains to.
    #:
    #: Version Added:
    #:     3.2
    #:
    #: Type:
    #:     str
    product: str = ''

    #: The version in which this warning pertains to.
    #:
    #: Version Added:
    #:     3.2
    #:
    #: Type:
    #:     str
    version: str = ''

    @classmethod
    def warn(cls, message, stacklevel=2):
        """Emit the deprecation warning.

        This is a convenience function that emits a deprecation warning using
        this class, with a suitable default stack level. Callers can provide
        a useful message and a custom stack level.

        Version Added:
            3.0

        Args:
            message (str):
                The message to show in the deprecation warning.

            stacklevel (int, optional):
                The stack level for the warning.
        """
        warnings.warn(message, cls, stacklevel=stacklevel + 1)


class BaseRemovedInDjbletsVersionWarning(BaseRemovedInProductVersionWarning):
    """Base class for a Djblets deprecation warning.

    All version-specific deprecation warnings inherit from this, allowing
    callers to check for Djblets deprecations without being tied to a specific
    version.
    """

    product = 'Djblets'


class RemovedInDjblets40Warning(BaseRemovedInDjbletsVersionWarning):
    """Deprecations for features scheduled for removal in Djblets 4.0.

    Note that this class will itself be removed in Djblets 4.0. If you need to
    check against Djblets deprecation warnings, please see
    :py:class:`BaseRemovedInDjbletsVersionWarning`. Alternatively, you can use
    the alias for this class, :py:data:`RemovedInNextDjbletsVersionWarning`.
    """

    version = '4.0'


class RemovedInDjblets50Warning(BaseRemovedInDjbletsVersionWarning):
    """Deprecations for features scheduled for removal in Djblets 5.0.

    Note that this class will itself be removed in Djblets 5.0. If you need to
    check against Djblets deprecation warnings, please see
    :py:class:`BaseRemovedInDjbletsVersionWarning`. Alternatively, you can use
    the alias for this class, :py:data:`RemovedInNextDjbletsVersionWarning`.
    """

    version = '5.0'


#: An alias for the next release of Djblets where features would be removed.
RemovedInNextDjbletsVersionWarning = RemovedInDjblets40Warning


def deprecated_arg_value(
    owner_name: str,
    value: Any,
    old_arg_name: str,
    new_arg_name: Optional[str] = None,
    warning_cls: Type[DeprecationWarning] = DeprecationWarning,
) -> SimpleLazyObject:
    """Wrap a value in a lazy object to warn when used.

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
    def _warn_on_use():
        if new_arg_name:
            if issubclass(warning_cls, BaseRemovedInProductVersionWarning):
                warning_cls.warn(
                    'The "%s" argument for "%s" has been deprecated '
                    'and will be removed in %s %s. Use "%s" instead.'
                    % (old_arg_name, owner_name, warning_cls.product,
                       warning_cls.version, new_arg_name))
            else:
                warnings.warn(
                    'The "%s" argument for "%s" has been deprecated '
                    'and will be removed in a future version. Use "%s" '
                    'instead.'
                    % (old_arg_name, owner_name, new_arg_name),
                    warning_cls)
        else:
            if issubclass(warning_cls, BaseRemovedInProductVersionWarning):
                warning_cls.warn(
                    'The "%s" argument for "%s" has been deprecated '
                    'and will be removed in %s %s.'
                    % (old_arg_name, owner_name, warning_cls.product,
                       warning_cls.version))
            else:
                warnings.warn(
                    'The "%s" argument for "%s" has been deprecated '
                    'and will be removed in a future version.'
                    % (old_arg_name, owner_name),
                    warning_cls)

        return value

    return SimpleLazyObject(_warn_on_use)


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
    def _get_argspec_info(
        func: _FuncT,
    ) -> Tuple[List[str], int]:
        """Return cached signature and keyword-only argument index information.

        This will compute a signature for the provided function and determine
        the index of the first keyword-only argument. These values will be
        cached on the function for future lookup, so additional calls don't
        incur a penalty.

        Args:
            func (callable):
                The decorated function to inspect.

        Returns:
            tuple:
            Information on the signature:

            Tuple:
                0 (list of str):
                    The list of parameter names for the function.

                1 (int):
                    The index of the first keyword-only argument.

        Raises:
            AssertionError:
                The function being called does not provide keyword-only
                arguments.
        """
        args_cache: Dict[str, Any]
        param_names: List[str]
        first_kwonly_arg_index: int

        try:
            args_cache = getattr(func, '_djblets_dep_kwonly_args_cache')
        except AttributeError:
            args_cache = {}
            setattr(func, '_djblets_dep_kwonly_args_cache', args_cache)

        if args_cache:
            param_names = args_cache['param_names']
            first_kwonly_arg_index = args_cache['first_kwonly_i']
        else:
            sig = inspect.signature(func)
            first_kwonly_arg_index = -1
            param_names = []
            i = 0

            # This is guaranteed to be in the correct order.
            for param in sig.parameters.values():
                if param.kind not in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                    param_names.append(param.name)

                    if (param.kind == param.KEYWORD_ONLY and
                        first_kwonly_arg_index == -1):
                        first_kwonly_arg_index = i

                    i += 1

            assert first_kwonly_arg_index != -1, (
                '@deprecate_non_keyword_only_args cannot be used on '
                'functions that do not contain keyword-only arguments.')

            args_cache.update({
                'first_kwonly_i': first_kwonly_arg_index,
                'param_names': param_names,
            })

        return param_names, first_kwonly_arg_index

    def _check_call(
        func: _FuncT,
        args: Tuple,
        kwargs: Dict,
    ) -> Tuple[Tuple, Dict]:
        """Check arguments to a call and modify if necessary.

        This will check if there are any positional arguments being passed as
        keyword arguments. If found, they'll be converted to keyword arguments
        and a warning will be emitted.

        Args:
            func (callable):
                The function being decorated.

            args (tuple):
                The caller-provided positional arguments.

            kwargs (dict):
                The caller-provided keyword arguments.

        Returns:
            tuple:
            A tuple of:

            Tuple:
                0 (tuple):
                    Positional arguments to pass to ``func``.

                1 (dict):
                    Keyword arguments to pass to ``func``.
        """
        param_names, first_kwonly_arg_index = _get_argspec_info(func)
        num_args = len(args)

        if num_args <= first_kwonly_arg_index:
            # The call doesn't have to be modified.
            return args, kwargs

        # Figure out which we need to move over to keyword-only
        # arguments.
        new_args: List = []
        new_kwargs: Dict[str, Any] = kwargs.copy()
        moved_args: List[str] = []
        i = 0

        for param_name in param_names:
            if param_name not in kwargs:
                if i < first_kwonly_arg_index:
                    new_args.append(args[i])
                elif i < num_args:
                    # This must be converted to a keyword argument.
                    new_kwargs[param_name] = args[i]
                    moved_args.append(param_name)
                else:
                    # We've handled all positional arguments. We're done.
                    break

                i += 1

        new_args += args[i:]

        warning_cls.warn(
            message or (
                'Positional argument(s) %s must be passed as keyword '
                'arguments when calling %s(). This will be required in '
                '%s %s.'
                % (
                    ', '.join(
                        '"%s"' % _arg_name
                        for _arg_name in moved_args
                    ),
                    func.__qualname__,
                    warning_cls.product,
                    warning_cls.version,
                )
            ),
            stacklevel=3)

        return tuple(new_args), new_kwargs

    def _dec(
        func: _FuncT,
    ) -> _FuncT:
        """Return the decorator for the function.

        Args:
            func (callable):
                The function being decorated.

        Returns:
            callable:
            The decorator for the function configured via the outer
            function's arguments.
        """
        @wraps(func)
        def _call(*args, **kwargs) -> Any:
            new_args, new_kwargs = _check_call(func, args, kwargs)

            return func(*new_args, **new_kwargs)

        return cast(_FuncT, _call)

    return _dec
