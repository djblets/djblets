from __future__ import unicode_literals

import inspect
from functools import wraps

from django.contrib.auth.models import User
from django.utils import six
from django.utils.decorators import method_decorator


def add_fixtures(fixtures, replace=False):
    """Adds or replaces the fixtures used for this test.

    This must be used along with :py:func:`djblets.testing.testcases.TestCase`.
    """
    def _dec(func):
        func._fixtures = fixtures
        func._replace_fixtures = replace
        return func

    return _dec


def requires_user_profile(f):
    """Ensure that User.get_profile exists for the following unit test.

    In Django 1.7+, ``User.get_profile`` no longer exists. Currently some
    parts of Djblets require this method to exist in Django or be added by the
    consuming app. To fix this requirement for unit testing on Django 1.7+, we
    attach a method that raises :py:exc:`NotImplementedError` when the method
    does not exist. After the test exits the method will be removed.

    Args:
        f (callable or type):
            The function or class to decorate

    Returns:
        callable or type:
        The decorated function or class.
    """
    def get_profile(self):
        raise NotImplementedError

    if inspect.isclass(f):
        # f is a class, so we will decorate all test_ methods on the class.
        decorator = method_decorator(requires_user_profile)
        attrs = vars(f)

        for attr_name, value in six.iteritems(attrs):
            if attr_name.startswith('test_') and callable(value):
                setattr(f, attr_name, decorator(value))

        return f
    else:
        @wraps(f)
        def decorated(*args, **kwargs):
            add_profile = not hasattr(User, 'get_profile')

            if add_profile:
                setattr(User, 'get_profile', get_profile)

            try:
                f(*args, **kwargs)
            finally:
                # Ensure that the method is the one we added. It is possible
                # that some code has replaced the method.
                if add_profile and hasattr(User, 'get_profile'):
                    # We have to un-spy for KGB-added spies because they will
                    # end up re-adding User.get_profile in test tear down after
                    # this decorator exits otherwise.
                    if hasattr(User.get_profile, 'unspy'):
                        User.get_profile.unspy()

                    # On Python 3.x, unbound methods are just plain functions,
                    # so they don't have __func__.
                    if hasattr(User.get_profile, '__func__'):
                        # Python 2.x
                        user_get_profile = User.get_profile.__func__
                    else:
                        # Python 3.x
                        user_get_profile = User.get_profile

                    if user_get_profile is get_profile:
                        delattr(User, 'get_profile')
        return decorated
