from __future__ import unicode_literals

from functools import wraps

from django.contrib.auth.models import User


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
    does not exist. After the text exits the method will be removed.

    Args:
        f (callable):
            The function to decorate

    Returns:
        callable:
        The decorated method.
    """
    def get_profile(self):
        raise NotImplementedError

    @wraps(f)
    def decorated(*args, **kwargs):
        add_profile = not hasattr(User, 'get_profile')

        if add_profile:
            setattr(User, 'get_profile', get_profile)

        try:
            f(*args, **kwargs)
        finally:
            # Ensure that the method is the one we added. It is possible that
            # some code has replaced the method.
            if add_profile and hasattr(User, 'get_profile'):
                # We have to un-spy for KGB-added spies because they will end
                # up re-adding User.get_profile in test tear down after this
                # decorator exits otherwise.
                if hasattr(User.get_profile, 'unspy'):
                    User.get_profile.unspy()

                if User.get_profile.im_func is get_profile:
                    delattr(User, 'get_profile')

    return decorated
