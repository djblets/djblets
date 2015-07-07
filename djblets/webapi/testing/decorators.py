"""Decorators to help with API test suites."""
from __future__ import unicode_literals

from djblets.util.decorators import simple_decorator


@simple_decorator
def webapi_test_template(test_func):
    """Mark a test function as a template for tests.

    This adds a flag to the test function hinting that it should be processed
    differently. :py:class:`WebAPITestCaseMixin` will replace the docstring to
    match that of the active test suite.
    """
    def _call(*args, **kwargs):
        return test_func(*args, **kwargs)

    _call.is_test_template = True

    return _call
