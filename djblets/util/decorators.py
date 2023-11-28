"""Miscellaneous, useful decorators."""

from functools import update_wrapper, wraps
from inspect import getfullargspec

from django import template
from django.template import TemplateSyntaxError, Variable
from django.utils.functional import cached_property as django_cached_property


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


def blocktag(*args, **kwargs):
    """Creates a block template tag with beginning/end tags.

    This does all the hard work of creating a template tag that can
    parse the arguments passed in and then parse all nodes between a
    beginning and end tag (such as myblock/endmyblock).

    By default, the end tag is prefixed with "end", but that can be
    changed by passing ``end_prefix="end_"`` or similar to @blocktag.

    blocktag will call the wrapped function with `context`  and `nodelist`
    parameters, as well as any parameters passed to the tag. It will
    also ensure that a proper error is raised if too many or too few
    parameters are passed.

    Args:
        end_prefix (unicode, optional):
            The prefix for the end tag. This defaults to ``'end'``, but
            template tags using underscores in the name might want to change
            this to ``'end_'``.

        resolve_vars (bool, optional):
            Whether to automatically resolve all variables provided to the
            template tag. By default, variables are resolved. Template tags
            can turn this off if they want to handle variable parsing
            manually.

    Returns:
        callable:
        The resulting template tag function.

    Example:
        .. code-block:: python

            @register.tag
            @blocktag
            def divify(context, nodelist, div_id=None):
                s = "<div"

                if div_id:
                    s += " id='%s'" % div_id

                return s + ">" + nodelist.render(context) + "</div>"
    """
    class BlockTagNode(template.Node):
        def __init__(self, tag_name, tag_func, nodelist, args):
            self.tag_name = tag_name
            self.tag_func = tag_func
            self.nodelist = nodelist
            self.args = args

        def render(self, context):
            if kwargs.get('resolve_vars', True):
                args = [Variable(var).resolve(context) for var in self.args]
            else:
                args = self.args

            return self.tag_func(context, self.nodelist, *args)

    def _blocktag_func(tag_func):
        def _setup_tag(parser, token):
            bits = token.split_contents()
            tag_name = bits[0]
            del(bits[0])

            argspec = getfullargspec(tag_func)
            params = argspec.args
            varargs = argspec.varargs
            defaults = argspec.defaults

            max_args = len(params) - 2  # Ignore context and nodelist
            min_args = max_args - len(defaults or [])

            if len(bits) < min_args or (not varargs and len(bits) > max_args):
                if not varargs and min_args == max_args:
                    raise TemplateSyntaxError(
                        "%r tag takes %d arguments." % (tag_name, min_args))
                else:
                    raise TemplateSyntaxError(
                        "%r tag takes %d to %d arguments, got %d." %
                        (tag_name, min_args, max_args, len(bits)))

            nodelist = parser.parse((('%s%s' % (end_prefix, tag_name)),))
            parser.delete_first_token()
            return BlockTagNode(tag_name, tag_func, nodelist, bits)

        update_wrapper(_setup_tag, tag_func)

        return _setup_tag

    end_prefix = kwargs.get('end_prefix', 'end')

    if len(args) == 1 and callable(args[0]):
        # This is being called in the @blocktag form.
        return _blocktag_func(args[0])
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
