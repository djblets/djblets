"""Backports of functionality from Django 1.8+'s django.utils.inspect.

Note that this module is not considered API-stable. Changes may be made that
remove or alter functionality in the future. Please use at your own risk.
"""

# TODO: Remove this file once we no longer support a version of Django
#       prior to 1.11.x.
#
# Much of this is a subset of Django 1.11.16's django/utils/inspect.py.
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
from __future__ import absolute_import, unicode_literals

import inspect

import django
from django.utils import six


if django.VERSION[:2] >= (1, 8):
    from django.utils.inspect import (getargspec,
                                      get_func_args,
                                      get_func_full_args,
                                      func_accepts_kwargs,
                                      func_accepts_var_args,
                                      func_has_no_args,
                                      func_supports_parameter)
else:
    def getargspec(func):
        if six.PY2:
            return inspect.getargspec(func)

        sig = inspect.signature(func)
        args = [
            p.name for p in sig.parameters.values()
            if p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
        ]
        varargs = [
            p.name for p in sig.parameters.values()
            if p.kind == inspect.Parameter.VAR_POSITIONAL
        ]
        varargs = varargs[0] if varargs else None
        varkw = [
            p.name for p in sig.parameters.values()
            if p.kind == inspect.Parameter.VAR_KEYWORD
        ]
        varkw = varkw[0] if varkw else None
        defaults = [
            p.default for p in sig.parameters.values()
            if (p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD and
                p.default is not p.empty)
        ] or None
        return args, varargs, varkw, defaults

    def get_func_args(func):
        if six.PY2:
            argspec = inspect.getargspec(func)
            return argspec.args[1:]  # ignore 'self'

        sig = inspect.signature(func)
        return [
            arg_name for arg_name, param in sig.parameters.items()
            if param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
        ]

    def get_func_full_args(func):
        """
        Return a list of (argument name, default value) tuples. If the argument
        does not have a default value, omit it in the tuple. Arguments such as
        *args and **kwargs are also included.
        """
        if six.PY2:
            argspec = inspect.getargspec(func)
            args = argspec.args[1:]  # ignore 'self'
            defaults = argspec.defaults or []
            # Split args into two lists depending on whether they have default
            # value
            no_default = args[:len(args) - len(defaults)]
            with_default = args[len(args) - len(defaults):]
            # Join the two lists and combine it with default values
            args = [(arg,) for arg in no_default] + zip(with_default, defaults)
            # Add possible *args and **kwargs and prepend them with '*' or '**'
            varargs = [('*' + argspec.varargs,)] if argspec.varargs else []
            kwargs = [('**' + argspec.keywords,)] if argspec.keywords else []
            return args + varargs + kwargs

        sig = inspect.signature(func)
        args = []
        for arg_name, param in sig.parameters.items():
            name = arg_name
            # Ignore 'self'
            if name == 'self':
                continue
            if param.kind == inspect.Parameter.VAR_POSITIONAL:
                name = '*' + name
            elif param.kind == inspect.Parameter.VAR_KEYWORD:
                name = '**' + name
            if param.default != inspect.Parameter.empty:
                args.append((name, param.default))
            else:
                args.append((name,))
        return args

    def func_accepts_kwargs(func):
        if six.PY2:
            # Not all callables are inspectable with getargspec, so we'll
            # try a couple different ways but in the end fall back on assuming
            # it is -- we don't want to prevent registration of valid but weird
            # callables.
            try:
                argspec = inspect.getargspec(func)
            except TypeError:
                try:
                    argspec = inspect.getargspec(func.__call__)
                except (TypeError, AttributeError):
                    argspec = None
            return not argspec or argspec[2] is not None

        return any(
            p for p in inspect.signature(func).parameters.values()
            if p.kind == p.VAR_KEYWORD
        )

    def func_accepts_var_args(func):
        """
        Return True if function 'func' accepts positional arguments *args.
        """
        if six.PY2:
            return inspect.getargspec(func)[1] is not None

        return any(
            p for p in inspect.signature(func).parameters.values()
            if p.kind == p.VAR_POSITIONAL
        )

    def func_has_no_args(func):
        args = inspect.getargspec(func)[0] if six.PY2 else [
            p for p in inspect.signature(func).parameters.values()
            if p.kind == p.POSITIONAL_OR_KEYWORD
        ]
        return len(args) == 1

    def func_supports_parameter(func, parameter):
        if six.PY3:
            return parameter in inspect.signature(func).parameters
        else:
            args, varargs, varkw, defaults = inspect.getargspec(func)
            return parameter in args
