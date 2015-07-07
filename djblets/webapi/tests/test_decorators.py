from __future__ import print_function, unicode_literals

from django.contrib.auth.models import AnonymousUser, User
from django.test.client import RequestFactory

from djblets.testing.testcases import TestCase
from djblets.webapi.decorators import (copy_webapi_decorator_data,
                                       webapi_login_required,
                                       webapi_permission_required,
                                       webapi_request_fields,
                                       webapi_response_errors)
from djblets.webapi.errors import (DOES_NOT_EXIST, INVALID_FORM_DATA,
                                   NOT_LOGGED_IN, PERMISSION_DENIED)


class WebAPIDecoratorTests(TestCase):
    """Unit tests for djblets.webapi.decorators."""

    def test_copy_webapi_decorator_data(self):
        """Testing copy_webapi_decorator_data"""
        def func1():
            """Function 1"""

        def func2():
            """Function 2"""

        func1.test1 = True
        func1.response_errors = set(['a', 'b'])
        func2.test2 = True
        func2.response_errors = set(['c', 'd'])

        result = copy_webapi_decorator_data(func1, func2)
        self.assertEqual(result, func2)

        self.assertTrue(hasattr(func2, 'test1'))
        self.assertTrue(hasattr(func2, 'test2'))
        self.assertTrue(hasattr(func2, 'response_errors'))
        self.assertTrue(func2.test1)
        self.assertTrue(func2.test2)
        self.assertEqual(func2.response_errors, set(['a', 'b', 'c', 'd']))
        self.assertEqual(func2.__doc__, 'Function 1')
        self.assertEqual(func2.__name__, 'func1')

        self.assertFalse(hasattr(func1, 'test2'))
        self.assertEqual(func1.response_errors, set(['a', 'b']))

    def test_webapi_response_errors_state(self):
        """Testing @webapi_response_errors state"""
        def orig_func():
            """Function 1"""

        func = webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN)(orig_func)

        self.assertFalse(hasattr(orig_func, 'response_errors'))

        self.assertEqual(func.__name__, 'orig_func')
        self.assertEqual(func.__doc__, 'Function 1')
        self.assertTrue(hasattr(func, 'response_errors'))
        self.assertEqual(func.response_errors,
                         set([DOES_NOT_EXIST, NOT_LOGGED_IN]))

    def test_webapi_response_errors_preserves_state(self):
        """Testing @webapi_response_errors preserves decorator state"""
        @webapi_response_errors(DOES_NOT_EXIST)
        @webapi_response_errors(NOT_LOGGED_IN)
        def func():
            """Function 1"""

        self.assertEqual(func.__name__, 'func')
        self.assertEqual(func.__doc__, 'Function 1')
        self.assertTrue(hasattr(func, 'response_errors'))
        self.assertEqual(func.response_errors,
                         set([DOES_NOT_EXIST, NOT_LOGGED_IN]))

    def test_webapi_response_errors_call(self):
        """Testing @webapi_response_errors calls original function"""
        @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN)
        def func():
            func.seen = True

        func()

        self.assertTrue(hasattr(func, 'seen'))

    def test_webapi_login_required_state(self):
        """Testing @webapi_login_required state"""
        def orig_func():
            """Function 1"""

        func = webapi_login_required(orig_func)

        self.assertFalse(hasattr(orig_func, 'login_required'))
        self.assertFalse(hasattr(orig_func, 'response_errors'))

        self.assertEqual(func.__name__, 'orig_func')
        self.assertEqual(func.__doc__, 'Function 1')
        self.assertTrue(hasattr(func, 'response_errors'))
        self.assertTrue(hasattr(func, 'login_required'))
        self.assertTrue(func.login_required)
        self.assertEqual(func.response_errors, set([NOT_LOGGED_IN]))

    def test_webapi_login_required_preserves_state(self):
        """Testing @webapi_login_required preserves decorator state"""
        @webapi_response_errors(DOES_NOT_EXIST)
        def orig_func():
            """Function 1"""

        func = webapi_login_required(orig_func)

        self.assertFalse(hasattr(orig_func, 'login_required'))

        self.assertEqual(func.__name__, 'orig_func')
        self.assertEqual(func.__doc__, 'Function 1')
        self.assertTrue(hasattr(func, 'response_errors'))
        self.assertTrue(hasattr(func, 'login_required'))
        self.assertTrue(func.login_required)
        self.assertEqual(func.response_errors,
                         set([DOES_NOT_EXIST, NOT_LOGGED_IN]))

    def test_webapi_login_required_call_when_authenticated(self):
        """Testing @webapi_login_required calls when authenticated"""
        @webapi_login_required
        def func(request):
            func.seen = True

        request = RequestFactory().request()
        request.user = User()
        result = func(request)

        self.assertTrue(hasattr(func, 'seen'))
        self.assertEqual(result, None)

    def test_webapi_login_required_call_when_anonymous(self):
        """Testing @webapi_login_required calls when anonymous"""
        @webapi_login_required
        def func(request):
            func.seen = True

        request = RequestFactory().request()
        request.user = AnonymousUser()
        result = func(request)

        self.assertFalse(hasattr(func, 'seen'))
        self.assertEqual(result, NOT_LOGGED_IN)

    def test_webapi_permission_required_state(self):
        """Testing @webapi_permission_required state"""
        def orig_func():
            """Function 1"""

        func = webapi_permission_required('myperm')(orig_func)

        self.assertFalse(hasattr(orig_func, 'response_errors'))

        self.assertEqual(func.__name__, 'orig_func')
        self.assertEqual(func.__doc__, 'Function 1')
        self.assertTrue(hasattr(func, 'response_errors'))
        self.assertEqual(func.response_errors,
                         set([NOT_LOGGED_IN, PERMISSION_DENIED]))

    def test_webapi_permission_required_preserves_state(self):
        """Testing @webapi_permission_required preserves decorator state"""
        @webapi_response_errors(DOES_NOT_EXIST)
        def orig_func():
            """Function 1"""

        func = webapi_permission_required('myperm')(orig_func)

        self.assertEqual(func.__name__, 'orig_func')
        self.assertEqual(func.__doc__, 'Function 1')
        self.assertTrue(hasattr(func, 'response_errors'))
        self.assertEqual(func.response_errors,
                         set([DOES_NOT_EXIST, NOT_LOGGED_IN,
                              PERMISSION_DENIED]))

    def test_webapi_permission_required_call_when_anonymous(self):
        """Testing @webapi_permission_required calls when anonymous"""
        @webapi_permission_required('foo')
        def func(request):
            func.seen = True

        request = RequestFactory().request()
        request.user = AnonymousUser()
        result = func(request)

        self.assertFalse(hasattr(func, 'seen'))
        self.assertEqual(result, NOT_LOGGED_IN)

    def test_webapi_permission_required_call_when_has_permission(self):
        """Testing @webapi_permission_required calls when has permission"""
        @webapi_permission_required('foo')
        def func(request):
            func.seen = True

        request = RequestFactory().request()
        request.user = User()
        request.user.has_perm = lambda perm: True
        result = func(request)

        self.assertTrue(hasattr(func, 'seen'))
        self.assertEqual(result, None)

    def test_webapi_permission_required_call_when_no_permission(self):
        """Testing @webapi_permission_required calls when no permission"""
        @webapi_permission_required('foo')
        def func(request):
            func.seen = True

        request = RequestFactory().request()
        request.user = User()
        request.user.has_perm = lambda perm: False
        result = func(request)

        self.assertFalse(hasattr(func, 'seen'))
        self.assertEqual(result, PERMISSION_DENIED)

    def test_webapi_request_fields_state(self):
        """Testing @webapi_request_fields state"""
        def orig_func():
            """Function 1"""

        required = {
            'required_param': {
                'type': bool,
                'description': 'Required param'
            },
        }

        optional = {
            'optional_param': {
                'type': bool,
                'description': 'Optional param'
            },
        }

        func = webapi_request_fields(required, optional)(orig_func)

        self.assertFalse(hasattr(orig_func, 'required_fields'))
        self.assertFalse(hasattr(orig_func, 'optional_fields'))
        self.assertFalse(hasattr(orig_func, 'response_errors'))

        self.assertEqual(func.__name__, 'orig_func')
        self.assertEqual(func.__doc__, 'Function 1')
        self.assertTrue(hasattr(func, 'response_errors'))
        self.assertTrue(hasattr(func, 'required_fields'))
        self.assertTrue(hasattr(func, 'optional_fields'))
        self.assertEqual(func.required_fields, required)
        self.assertEqual(func.optional_fields, optional)
        self.assertEqual(func.response_errors, set([INVALID_FORM_DATA]))

    def test_webapi_request_fields_preserves_state(self):
        """Testing @webapi_request_fields preserves decorator state"""
        required1 = {
            'required1': {
                'type': bool,
                'description': 'Required param'
            },
        }

        optional1 = {
            'optional1': {
                'type': bool,
                'description': 'Optional param'
            },
        }

        @webapi_request_fields(required1, optional1)
        @webapi_response_errors(DOES_NOT_EXIST)
        def orig_func():
            """Function 1"""

        required2 = {
            'required2': {
                'type': bool,
                'description': 'Required param'
            },
        }

        optional2 = {
            'optional2': {
                'type': bool,
                'description': 'Optional param'
            },
        }

        func = webapi_request_fields(required2, optional2)(orig_func)

        expected_required = required1.copy()
        expected_required.update(required2)
        expected_optional = optional1.copy()
        expected_optional.update(optional2)

        self.assertTrue(hasattr(orig_func, 'required_fields'))
        self.assertTrue(hasattr(orig_func, 'optional_fields'))
        self.assertTrue(hasattr(orig_func, 'response_errors'))

        self.assertEqual(func.__name__, 'orig_func')
        self.assertEqual(func.__doc__, 'Function 1')
        self.assertTrue(hasattr(func, 'response_errors'))
        self.assertTrue(hasattr(func, 'required_fields'))
        self.assertTrue(hasattr(func, 'optional_fields'))
        self.assertEqual(func.required_fields, expected_required)
        self.assertEqual(func.optional_fields, expected_optional)
        self.assertEqual(func.response_errors,
                         set([DOES_NOT_EXIST, INVALID_FORM_DATA]))

    def test_webapi_request_fields_call_normalizes_params(self):
        """Testing @webapi_request_fields normalizes params to function"""
        @webapi_request_fields(
            required={
                'required_param': {
                    'type': int,
                }
            },
            optional={
                'optional_param': {
                    'type': bool,
                }
            },
        )
        def func(request, required_param=None, optional_param=None,
                 parsed_request_fields=None, extra_fields={}):
            func.seen = True
            self.assertTrue(isinstance(required_param, int))
            self.assertTrue(isinstance(optional_param, bool))
            self.assertEqual(required_param, 42)
            self.assertTrue(optional_param)
            self.assertFalse(extra_fields)
            self.assertEqual(parsed_request_fields,
                             {
                                 'required_param': required_param,
                                 'optional_param': optional_param,
                             })

        result = func(RequestFactory().get(
            path='/',
            data={
                'required_param': '42',
                'optional_param': '1',
            }
        ))

        self.assertTrue(hasattr(func, 'seen'))
        self.assertEqual(result, None)

    def test_webapi_request_fields_call_with_unexpected_arg(self):
        """Testing @webapi_request_fields with unexpected argument"""
        @webapi_request_fields(
            required={
                'required_param': {
                    'type': int,
                }
            },
        )
        def func(request, required_param=None, extra_fields={}):
            func.seen = True

        result = func(RequestFactory().get(
            path='/',
            data={
                'required_param': '42',
                'optional_param': '1',
            }
        ))

        self.assertFalse(hasattr(func, 'seen'))
        self.assertEqual(result[0], INVALID_FORM_DATA)
        self.assertTrue('fields' in result[1])
        self.assertTrue('optional_param' in result[1]['fields'])

    def test_webapi_request_fields_call_with_allow_unknown(self):
        """Testing @webapi_request_fields with allow_unknown=True"""
        @webapi_request_fields(
            required={
                'required_param': {
                    'type': int,
                }
            },
            allow_unknown=True
        )
        def func(request, required_param=None, parsed_request_fields=None,
                 extra_fields={}):
            func.seen = True
            self.assertEqual(required_param, 42)
            self.assertTrue('optional_param' in extra_fields)
            self.assertEqual(extra_fields['optional_param'], '1')
            self.assertEqual(parsed_request_fields,
                             {'required_param': required_param})

        result = func(RequestFactory().get(
            path='/',
            data={
                'required_param': '42',
                'optional_param': '1',
            }
        ))

        self.assertTrue(hasattr(func, 'seen'))
        self.assertEqual(result, None)

    def test_webapi_request_fields_call_filter_special_params(self):
        """Testing @webapi_request_fields filters special params"""
        @webapi_request_fields(
            required={
                'required_param': {
                    'type': int,
                }
            },
        )
        def func(request, required_param=None, parsed_request_fields=None,
                 extra_fields={}):
            func.seen = True
            self.assertTrue(isinstance(required_param, int))
            self.assertEqual(required_param, 42)
            self.assertEqual(parsed_request_fields,
                             {'required_param': required_param})
            self.assertFalse(extra_fields)

        result = func(RequestFactory().get(
            path='/',
            data={
                'required_param': '42',
                'api_format': 'json',
            }
        ))

        self.assertTrue(hasattr(func, 'seen'))
        self.assertEqual(result, None)

    def test_webapi_request_fields_call_validation_int(self):
        """Testing @webapi_request_fields with int parameter validation"""
        @webapi_request_fields(
            required={
                'myint': {
                    'type': int,
                }
            }
        )
        def func(request, myint=False, parsed_request_fields=None,
                 extra_fields={}):
            func.seen = True

        result = func(RequestFactory().get(
            path='/',
            data={
                'myint': 'abc',
            }
        ))
        self.assertFalse(hasattr(func, 'seen'))
        self.assertEqual(result[0], INVALID_FORM_DATA)
        self.assertTrue('fields' in result[1])
        self.assertTrue('myint' in result[1]['fields'])
