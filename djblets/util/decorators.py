"""Miscellaneous, useful decorators."""

from __future__ import annotations

import inspect
from functools import update_wrapper, wraps
from typing import TYPE_CHECKING, overload

from django import template
from djblets.deprecation import RemovedInDjblets70Warning
from django.template.library import parse_bits
from django.utils.functional import cached_property as django_cached_property

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from typing import Any, Concatenate, ParamSpec, TypeAlias, TypeVar

    from django.template import Context, Node, NodeList
    from django.template.base import FilterExpression, Parser, Token

    _P = ParamSpec('_P')
    _R = TypeVar('_R')
    _TagFunc: TypeAlias = Callable[Concatenate[Context, NodeList, _P], _R]
    _TagCompiler: TypeAlias = Callable[[Parser, Token], Node]


# The decorator decorator.  This is copyright unknown, verbatim from
# http://wiki.python.org/moin/PythonDecoratorLibrary
def simple_decorator(decorator):
    """This decorator can be used to turn simple functions
       into well-behaved decorators, so long as the decorators
       are fairly simple. If a decorator expects a function and
       returns a function (no descriptors), and if it doesn't
       modify function attributes or docstring, then it is
       eligible to use this. Simply apply @simple_decorator to
       your decorator and it will automatically preserve the
       docstring and function attributes of functions to which
       it is applied."""
    def new_decorator(f):
        g = decorator(f)
        update_wrapper(g, f)
        return g
    # Now a few lines needed to make simple_decorator itself
    # be a well-behaved decorator.
    update_wrapper(new_decorator, decorator)
    return new_decorator


def augment_method_from(klass):
    """Augments a class's method with new decorators or documentation.

    This is useful when a class needs to add new decorators or new
    documentation to a parent class's method, without changing the behavior
    or burying the existing decorators.

    The methods using this decorator can provide code to run at the end of
    the parent function. Usually, though, it will just have an empty body
    of ``pass``.
    """
    def _dec(func):
        @wraps(func)
        def _call(*args, **kwargs):
            try:
                f = augmented_func(*args, **kwargs)
            finally:
                func(*args, **kwargs)

            return f

        augmented_func = getattr(klass, func.__name__)

        # Go beyond what @wraps does. Choose a suitable docstring depending
        # on which is set, and combine dictionaries with `func` taking
        # priority.
        _call.__doc__ = func.__doc__ or augmented_func.__doc__
        _call.__dict__.update(augmented_func.__dict__)
        _call.__dict__.update(func.__dict__)

        real_func = _call.__dict__.get('_augmented_func', augmented_func)
        _call.__dict__['_augmented_func'] = real_func

        return _call

    return _dec


class _BlockTagNode(template.Node):
    """Node used to render block tags.

    This is an internal class returned by :py:func:`blocktag`, used to
    interface with a provided function for processing a block of nodes.
    It is not subject to any API stability guarantees.

    Version Added:
        5.3:
        This was moved out from inside of :py:func:`blocktag`.
    """

    ######################
    # Instance variables #
    ######################

    #: The list of nodes inside the block to process.
    node_list: NodeList

    #: Whether to resolve variables passed to the template tag.
    resolve_vars: bool

    #: The positional argument bits passed to the template tag.
    tag_args: Sequence[FilterExpression]

    #: The function to call to handle the block's contents.
    tag_func: _TagFunc

    #: The positional keyword bits passed to the template tag.
    tag_kwargs: Mapping[str, FilterExpression]

    def __init__(
        self,
        *,
        tag_func: _TagFunc,
        nodelist: NodeList,
        tag_args: Sequence[FilterExpression],
        tag_kwargs: Mapping[str, FilterExpression],
        resolve_vars: bool,
    ) -> None:
        """Initialize the node.

        Args:
            tag_func (callable):
                The function to call to handle the block's contents.

            nodelist (django.template.NodeList):
                The list of nodes inside the block to process.

            tag_args (list of str):
                The positional argument bits passed to the template tag.

            tag_kwargs (list of str):
                The positional keyword bits passed to the template tag.

            resolve_vars (bool, optional):
                Whether to resolve variables passed to the template tag.
        """
        self.tag_func = tag_func
        self.nodelist = nodelist
        self.tag_args = tag_args
        self.tag_kwargs = tag_kwargs
        self.resolve_vars = resolve_vars

    def render(
        self,
        context: Context,
    ) -> str:
        """Render the contents of the block.

        This will resolve any variables, if requested, and pass everything
        to the wrapped function.

        Args:
            context (django.template.Context):
                The current template context.

        Returns:
            str:
            The resulting rendered content.
        """
        tag_args = self.tag_args
        tag_kwargs = self.tag_kwargs

        if self.resolve_vars:
            tag_args = [
                var.resolve(context)
                for var in tag_args
            ]

            tag_kwargs = {
                name: var.resolve(context)
                for name, var in tag_kwargs.items()
            }
        else:
            tag_args = [
                var.token
                for var in tag_args
            ]

            tag_kwargs = {
                name: var.token
                for name, var in tag_kwargs.items()
            }

        return self.tag_func(context, self.nodelist, *tag_args, **tag_kwargs)


@overload
def blocktag(
    func: _TagFunc[_P, _R],
) -> _TagCompiler:
    ...


@overload
def blocktag(
    *,
    end_prefix: str = 'end',
    resolve_vars: bool = True,
) -> Callable[[_TagFunc[_P, _R]], _TagCompiler]:
    ...


def blocktag(
    func: (_TagFunc[_P, _R] | None) = None,
    *args,
    end_prefix: str = 'end',
    name: (str | None) = None,
    resolve_vars: bool = True,
    **kwargs,
) -> Any:
    """Create a block template tag with beginning/end tags.

    This does all the hard work of creating a template tag that can
    parse the arguments passed in and then parse all nodes between a
    beginning and end tag (such as ``myblock``/``endmyblock``).

    Both positional and keyword arguments (``name=value``) are supported,
    in any order.

    By default, the end tag is prefixed with "end", but that can be
    changed by passing ``end_prefix="end_"`` or similar to ``@blocktag``.

    blocktag will call the wrapped function with ``context`` and ``nodelist``
    parameters, as well as any parameters passed to the tag. It will
    also ensure that a proper error is raised if too many or too few
    parameters are passed.

    Version Changed:
        5.3:
        * Keyword arguments are now supported using ``name=value`` format.
        * The decorated function now supports keyword-only arguments.
        * Template filters are now supported for arguments.
        * Added the ``name`` argument.
        * Arbitrary arguments are deprecated and support will be removed
          in Djblets 7.

    Args:
        tag_func (callable, optional):
            The function being decorated.

            This is only set if no other arguments are provided.

        *args (tuple, unused):
            Extra positional arguments.

            This is ignored.

            Deprecated:
                7.1:
                This will be removed in Djblets 7.

        end_prefix (str, optional):
            The prefix for the end tag. This defaults to ``'end'``, but
            template tags using underscores in the name might want to change
            this to ``'end_'``.

        name (str, optional):
            An explicit name for the template tag.

            If not provided, the function name will be used.

            Version Added:
                5.3

        resolve_vars (bool, optional):
            Whether to automatically resolve all variables provided to the
            template tag. By default, variables are resolved. Template tags
            can turn this off if they want to handle variable parsing
            manually.

        **kwargs (dict, unused):
            Extra keyword arguments.

            This is ignored.

            Deprecated:
                7.1:
                This will be removed in Djblets 7.

    Returns:
        callable:
        The resulting template tag function.

    Example:
        .. code-block:: python

            @register.tag
            @blocktag
            def divify(context, nodelist, div_id=None, *,
                       css_class='my-class'):
                s = format_html('<div class="{}"', my_class)

                if div_id:
                    s += format_html(' id="{}"', div_id)

                return s + '>' + nodelist.render(context) + '</div>'
    """
    def _blocktag_func(
        tag_func: _TagFunc[_P, _R],
    ) -> _TagCompiler:
        (
            params,
            varargs,
            varkw,
            defaults,
            kwonly,
            kwonly_defaults,
            *_unused,
        ) = inspect.getfullargspec(inspect.unwrap(tag_func))

        tag_name = name or tag_func.__name__
        end_tag_name = f'{end_prefix}{tag_name}'

        @wraps(tag_func)
        def _setup_tag(
            parser: Parser,
            token: Token,
        ) -> _BlockTagNode:
            bits = token.split_contents()
            tag_args, tag_kwargs = parse_bits(
                parser,
                bits[1:],    # Skip the tag name.
                params[2:],  # Skip the context and nodelist params.
                varargs,
                varkw,
                defaults,
                kwonly,
                kwonly_defaults,
                takes_context=False,
                name=tag_name,
            )

            # Parse the contents of the block into a list of nodes.
            nodelist = parser.parse(((end_tag_name),))
            parser.delete_first_token()

            # Return our node for handling this list.
            return _BlockTagNode(
                tag_func=tag_func,
                nodelist=nodelist,
                tag_args=tag_args,
                tag_kwargs=tag_kwargs,
                resolve_vars=resolve_vars,
            )

        update_wrapper(_setup_tag, tag_func)

        return _setup_tag

    if args:
        RemovedInDjblets70Warning.warn(
            '@blocktag no longer takes extra positional arguments. This '
            'will be removed in Djblets 7.'
        )

    if kwargs:
        RemovedInDjblets70Warning.warn(
            '@blocktag no longer takes extra keyword arguments. This '
            'will be removed in Djblets 7.'
        )

    if func is not None:
        # This is being called in the @blocktag form.
        return _blocktag_func(func)
    else:
        # This is being called in the @blocktag(...) form.
        return _blocktag_func


class cached_property(django_cached_property):
    """Decorator for creating a read-only property that caches a value.

    This is a drop-in replacement for Django's
    :py:class:`~django.utils.functional.cached_property` that retains the
    docstring and attributes of the original method.

    While Django 1.8+ does retain the docstring, it does not retain the
    attributes.
    """

    def __init__(self, func):
        """Initialize the property.

        Args:
            func (callable):
                The function that will be called when this property is
                accessed. The property will have its name, documentation,
                and other attributes.
        """
        super(cached_property, self).__init__(func)

        update_wrapper(self, func)


def optional_decorator(decorator, predicate):
    """Optionally apply a decorator given a predicate function.

    Args:
        decorator (callable):
            The decorator to conditionally apply.

        predicate (callable):
            The predicate used to determine when ``decorator`` should be used.
            The arguments provided to the decorated function will be passed to
            this function.

    Returns:
        callable:
        A decorator that, when applied to a function, will call the function
        decorated with ``decorator`` when ``predicate()`` returns ``True``.
        Otherwise it will call the original function.

    Example:
        .. code-block:: python

           from djblets.util.decorators import (optional_decorator,
                                                simple_decorator)

           def predicate(verbose)
               return verbose

           @simple_decorator
           def decorator(f):
               def decorated(verbose):
                   print('Hello from the decorator')
                   return f(verbose)

           @optional_decorator(decorator, predicate)
           def f(x):
                print('Hello from f()')

           # Prints "Hello from the decorator" and "Hello from f()"
           f(verbose=True)

           # Prints "Hello from f()"
           f(verbose=False)
    """
    def _decorator(view):
        with_decorator = decorator(view)

        @wraps(view)
        def decorated(*args, **kwargs):
            if predicate(*args, **kwargs):
                return with_decorator(*args, **kwargs)

            return view(*args, **kwargs)

        return decorated

    return _decorator
