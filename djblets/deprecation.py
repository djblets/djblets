"""Internal support for handling deprecations in Djblets.

The version-specific objects in this module are not considered stable between
releases, and may be removed at any point. The base objects are considered
stable.
"""

import warnings

from django.utils.functional import SimpleLazyObject


class BaseRemovedInDjbletsVersionWarning(DeprecationWarning):
    """Base class for a Djblets deprecation warning.

    All version-specific deprecation warnings inherit from this, allowing
    callers to check for Djblets deprecations without being tied to a specific
    version.
    """

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


class RemovedInDjblets40Warning(BaseRemovedInDjbletsVersionWarning):
    """Deprecations for features scheduled for removal in Djblets 4.0.

    Note that this class will itself be removed in Djblets 4.0. If you need to
    check against Djblets deprecation warnings, please see
    :py:class:`BaseRemovedInDjbletsVersionWarning`. Alternatively, you can use
    the alias for this class, :py:data:`RemovedInNextDjbletsVersionWarning`.
    """


class RemovedInDjblets50Warning(BaseRemovedInDjbletsVersionWarning):
    """Deprecations for features scheduled for removal in Djblets 5.0.

    Note that this class will itself be removed in Djblets 5.0. If you need to
    check against Djblets deprecation warnings, please see
    :py:class:`BaseRemovedInDjbletsVersionWarning`. Alternatively, you can use
    the alias for this class, :py:data:`RemovedInNextDjbletsVersionWarning`.
    """


#: An alias for the next release of Djblets where features would be removed.
RemovedInNextDjbletsVersionWarning = RemovedInDjblets40Warning


def deprecated_arg_value(owner_name, value, old_arg_name, new_arg_name=None,
                         warning_cls=DeprecationWarning):
    """Wrap a value in a lazy object to warn when used.

    Args:
        owner_name (unicode):
            The name of the owner of this argument.

        value (object):
            The argument value.

        old_arg_name (unicode):
            The name of the argument that was deprecated.

        new_arg_name (unicode, optional):
            The optional name of the argument to use in the deprecated
            argument's place, if one is available.

        warning_cls (type, optional):
            The class to use for the warning. This should be
            :py:exc:`DeprecationWarning`, :py:exc:`PendingDeprecationWarning`,
            or a subclass of one.

    Returns:
        django.utils.functional.SimpleLazyObject:
        The value wrapped in a lazy object. The first time it is accessed,
        a warning will be emitted.
    """
    def _warn_on_use():
        if new_arg_name:
            warnings.warn('The "%s" argument for "%s" has been deprecated '
                          'and will be removed in a future version. Use "%s" '
                          'instead.'
                          % (old_arg_name, owner_name, new_arg_name),
                          warning_cls)
        else:
            warnings.warn('The "%s" argument for "%s" has been deprecated '
                          'and will be removed in a future version.'
                          % (old_arg_name, owner_name),
                          warning_cls)

        return value

    return SimpleLazyObject(_warn_on_use)
