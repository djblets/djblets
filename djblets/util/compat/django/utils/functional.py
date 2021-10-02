"""Backports of functionality from Django 1.11's django.utils.functional.

Note that this module is not considered API-stable. Changes may be made that
remove or alter functionality in the future. Please use at your own risk.
"""

# TODO: Remove this file once we no longer support a version of Django
#       prior to 1.11.x.
#
# Much of this is a subset of Django 1.11.16's django/utils/functional.py.
#
# Copyright (c) Django Software Foundation and individual contributors.  All
# rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     1. Redistributions of source code must retain the above copyright notice,
#     this list of conditions and the following disclaimer.
#
#     2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
#     3. Neither the name of Django nor the names of its contributors may be
#     used to endorse or promote products derived from this software without
#     specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import unicode_literals

import copy
import operator

import django
from django.utils import six
from django.utils.functional import empty, new_method_proxy


if django.VERSION[:3] >= (1, 11, 16):
    from django.utils.functional import (LazyObject, SimpleLazyObject,
                                         unpickle_lazyobject)
else:
    class LazyObject(object):
        """
        A wrapper for another class that can be used to delay instantiation of the
        wrapped class.

        By subclassing, you have the opportunity to intercept and alter the
        instantiation. If you don't need to do that, use SimpleLazyObject.
        """

        # Avoid infinite recursion when tracing __init__ (#19456).
        _wrapped = None

        def __init__(self):
            # Note: if a subclass overrides __init__(), it will likely need to
            # override __copy__() and __deepcopy__() as well.
            self._wrapped = empty

        __getattr__ = new_method_proxy(getattr)

        def __setattr__(self, name, value):
            if name == "_wrapped":
                # Assign to __dict__ to avoid infinite __setattr__ loops.
                self.__dict__["_wrapped"] = value
            else:
                if self._wrapped is empty:
                    self._setup()
                setattr(self._wrapped, name, value)

        def __delattr__(self, name):
            if name == "_wrapped":
                raise TypeError("can't delete _wrapped.")
            if self._wrapped is empty:
                self._setup()
            delattr(self._wrapped, name)

        def _setup(self):
            """
            Must be implemented by subclasses to initialize the wrapped object.
            """
            raise NotImplementedError('subclasses of LazyObject must provide a _setup() method')

        # Because we have messed with __class__ below, we confuse pickle as to what
        # class we are pickling. We're going to have to initialize the wrapped
        # object to successfully pickle it, so we might as well just pickle the
        # wrapped object since they're supposed to act the same way.
        #
        # Unfortunately, if we try to simply act like the wrapped object, the ruse
        # will break down when pickle gets our id(). Thus we end up with pickle
        # thinking, in effect, that we are a distinct object from the wrapped
        # object, but with the same __dict__. This can cause problems (see #25389).
        #
        # So instead, we define our own __reduce__ method and custom unpickler. We
        # pickle the wrapped object as the unpickler's argument, so that pickle
        # will pickle it normally, and then the unpickler simply returns its
        # argument.
        def __reduce__(self):
            if self._wrapped is empty:
                self._setup()
            return (unpickle_lazyobject, (self._wrapped,))

        # Overriding __class__ stops __reduce__ from being called on Python 2.
        # So, define __getstate__ in a way that cooperates with the way that
        # pickle interprets this class. This fails when the wrapped class is a
        # builtin, but it's better than nothing.
        def __getstate__(self):
            if self._wrapped is empty:
                self._setup()
            return self._wrapped.__dict__

        def __copy__(self):
            if self._wrapped is empty:
                # If uninitialized, copy the wrapper. Use type(self), not
                # self.__class__, because the latter is proxied.
                return type(self)()
            else:
                # If initialized, return a copy of the wrapped object.
                return copy.copy(self._wrapped)

        def __deepcopy__(self, memo):
            if self._wrapped is empty:
                # We have to use type(self), not self.__class__, because the
                # latter is proxied.
                result = type(self)()
                memo[id(self)] = result
                return result
            return copy.deepcopy(self._wrapped, memo)

        if six.PY3:
            __bytes__ = new_method_proxy(bytes)
            __str__ = new_method_proxy(str)
            __bool__ = new_method_proxy(bool)
        else:
            __str__ = new_method_proxy(str)
            __unicode__ = new_method_proxy(unicode)  # NOQA: unicode undefined on PY3
            __nonzero__ = new_method_proxy(bool)

        # Introspection support
        __dir__ = new_method_proxy(dir)

        # Need to pretend to be the wrapped class, for the sake of objects that
        # care about this (especially in equality tests)
        __class__ = property(new_method_proxy(operator.attrgetter("__class__")))
        __eq__ = new_method_proxy(operator.eq)
        __ne__ = new_method_proxy(operator.ne)
        __hash__ = new_method_proxy(hash)

        # List/Tuple/Dictionary methods support
        __getitem__ = new_method_proxy(operator.getitem)
        __setitem__ = new_method_proxy(operator.setitem)
        __delitem__ = new_method_proxy(operator.delitem)
        __iter__ = new_method_proxy(iter)
        __len__ = new_method_proxy(len)
        __contains__ = new_method_proxy(operator.contains)


    class SimpleLazyObject(LazyObject):
        """
        A lazy object initialized from any function.

        Designed for compound objects of unknown type. For builtins or objects of
        known type, use django.utils.functional.lazy.
        """
        def __init__(self, func):
            """
            Pass in a callable that returns the object to be wrapped.

            If copies are made of the resulting SimpleLazyObject, which can happen
            in various circumstances within Django, then you must ensure that the
            callable can be safely run more than once and will return the same
            value.
            """
            self.__dict__['_setupfunc'] = func
            super(SimpleLazyObject, self).__init__()

        def _setup(self):
            self._wrapped = self._setupfunc()

        # Return a meaningful representation of the lazy object for debugging
        # without evaluating the wrapped object.
        def __repr__(self):
            if self._wrapped is empty:
                repr_attr = self._setupfunc
            else:
                repr_attr = self._wrapped
            return '<%s: %r>' % (type(self).__name__, repr_attr)

        def __copy__(self):
            if self._wrapped is empty:
                # If uninitialized, copy the wrapper. Use SimpleLazyObject, not
                # self.__class__, because the latter is proxied.
                return SimpleLazyObject(self._setupfunc)
            else:
                # If initialized, return a copy of the wrapped object.
                return copy.copy(self._wrapped)

        def __deepcopy__(self, memo):
            if self._wrapped is empty:
                # We have to use SimpleLazyObject, not self.__class__, because the
                # latter is proxied.
                result = SimpleLazyObject(self._setupfunc)
                memo[id(self)] = result
                return result
            return copy.deepcopy(self._wrapped, memo)


    def unpickle_lazyobject(wrapped):
        """
        Used to unpickle lazy objects. Just return its argument, which will be the
        wrapped object.
        """
        return wrapped


__all__ = (
    'LazyObject',
    'SimpleLazyObject',
    'unpickle_lazyobject',
)
