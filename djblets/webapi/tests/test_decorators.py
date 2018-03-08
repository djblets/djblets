"""Unit tests for WebAPI decorators."""

from __future__ import unicode_literals

from django.contrib.auth.models import AnonymousUser, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.client import RequestFactory
from django.utils import six

from djblets.testing.testcases import TestCase
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import (copy_webapi_decorator_data,
                                       webapi_login_required,
                                       webapi_permission_required,
                                       webapi_request_fields,
                                       webapi_response_errors)
from djblets.webapi.errors import (DOES_NOT_EXIST, INVALID_FORM_DATA,
                                   NOT_LOGGED_IN, PERMISSION_DENIED)
from djblets.webapi.fields import (BooleanFieldType,
                                   ChoiceFieldType,
                                   IntFieldType,
                                   FileFieldType,
                                   StringFieldType)


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
                'type': BooleanFieldType,
                'description': 'Required param'
            },
        }

        optional = {
            'optional_param': {
                'type': BooleanFieldType,
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
                'type': BooleanFieldType,
                'description': 'Required param'
            },
        }

        optional1 = {
            'optional1': {
                'type': BooleanFieldType,
                'description': 'Optional param'
            },
        }

        @webapi_request_fields(required1, optional1)
        @webapi_response_errors(DOES_NOT_EXIST)
        def orig_func():
            """Function 1"""

        required2 = {
            'required2': {
                'type': BooleanFieldType,
                'description': 'Required param'
            },
        }

        optional2 = {
            'optional2': {
                'type': BooleanFieldType,
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

    def test_webapi_request_fields_checks_inheritance(self):
        """Testing @webapi_request_fields properly checks inherited fields"""
        class A(object):
            @webapi_request_fields(required={
                'required1': {
                    'type': BooleanFieldType,
                    'description': 'Required param',
                },
            })
            def test(*args, **kwargs):
                pass

        class B(A):
            @webapi_request_fields(required={
                'required2': {
                    'type': BooleanFieldType,
                    'description': 'Required param',
                },
            })
            @augment_method_from(A)
            def test(*args, **kwargs):
                pass

        request = RequestFactory().post('/', data={'required2': True})

        b = B()
        error, response = b.test(request)

        self.assertTrue('fields' in response)
        self.assertTrue('required1' in response['fields'])
        self.assertEqual(response['fields']['required1'],
                         ['This field is required'])
        self.assertFalse('required2' in response['fields'])

    def test_webapi_request_fields_call_normalizes_params(self):
        """Testing @webapi_request_fields normalizes params to function"""
        if not hasattr(__builtins__, 'file'):
            # Python 3.x doesn't have `file`, so define our own for the test.
            class file(object):
                pass

        @webapi_request_fields(
            required={
                'required_int': {
                    'type': IntFieldType,
                },
                'required_string': {
                    'type': StringFieldType,
                },
                'required_choice': {
                    'type': ChoiceFieldType,
                    'choices': ['a', 'b', 'c'],
                },
                'required_bool': {
                    'type': BooleanFieldType,
                },
                'required_file': {
                    'type': FileFieldType,
                },
            },
            optional={
                'optional_param': {
                    'type': BooleanFieldType,
                }
            },
        )
        def func(request, required_int=None, required_string=None,
                 required_choice=None, required_file=None, required_bool=None,
                 optional_param=None, parsed_request_fields=None,
                 extra_fields={}):
            func.seen = True
            self.assertEqual(required_int, 42)
            self.assertEqual(required_string, 'test')
            self.assertEqual(required_choice, 'a')
            self.assertEqual(required_file.read(), b'content')
            self.assertTrue(required_bool)
            self.assertTrue(optional_param)
            self.assertFalse(extra_fields)
            self.assertEqual(
                parsed_request_fields,
                {
                    'required_int': required_int,
                    'required_string': required_string,
                    'required_choice': required_choice,
                    'required_bool': required_bool,
                    'required_file': required_file,
                    'optional_param': optional_param,
                })

        result = func(RequestFactory().post(
            path='/',
            data={
                'required_int': '42',
                'required_string': 'test',
                'required_choice': 'a',
                'required_bool': 'true',
                'required_file': SimpleUploadedFile(name='test',
                                                    content=b'content'),
                'optional_param': '1',
            },
        ))

        self.assertTrue(hasattr(func, 'seen'))
        self.assertIsNone(result)

    def test_webapi_request_fields_call_normalizes_params_legacy_types(self):
        """Testing @webapi_request_fields normalizes params to function when
        using legacy types
        """
        if not hasattr(__builtins__, 'file'):
            # Python 3.x doesn't have `file`, so define our own for the test.
            class file(object):
                pass

        @webapi_request_fields(
            required={
                'required_int': {
                    'type': int,
                },
                'required_unicode_str': {
                    'type': six.text_type,
                },
                'required_native_str': {
                    'type': str,
                },
                'required_choice_list': {
                    'type': ['a', 'b', 'c'],
                },
                'required_choice_tuple': {
                    'type': ('a', 'b', 'c'),
                },
                'required_bool': {
                    'type': bool,
                },
                'required_file': {
                    'type': file,
                },
            },
            optional={
                'optional_param': {
                    'type': bool,
                }
            },
        )
        def func(request, required_int=None, required_unicode_str=None,
                 required_native_str=None, required_choice_list=None,
                 required_choice_tuple=None, required_file=None,
                 required_bool=None, optional_param=None,
                 parsed_request_fields=None, extra_fields={}):
            func.seen = True
            self.assertEqual(required_int, 42)
            self.assertEqual(required_unicode_str, 'test')
            self.assertEqual(required_native_str, str('test'))
            self.assertEqual(required_choice_list, 'a')
            self.assertEqual(required_choice_tuple, 'c')
            self.assertEqual(required_file.read(), b'content')
            self.assertTrue(required_bool)
            self.assertTrue(optional_param)
            self.assertFalse(extra_fields)
            self.assertEqual(
                parsed_request_fields,
                {
                    'required_int': required_int,
                    'required_unicode_str': required_unicode_str,
                    'required_native_str': required_native_str,
                    'required_choice_list': required_choice_list,
                    'required_choice_tuple': required_choice_tuple,
                    'required_bool': required_bool,
                    'required_file': required_file,
                    'optional_param': optional_param,
                })

        result = func(RequestFactory().post(
            path='/',
            data={
                'required_int': '42',
                'required_unicode_str': 'test',
                'required_native_str': str('test'),
                'required_choice_list': 'a',
                'required_choice_tuple': 'c',
                'required_bool': 'true',
                'required_file': SimpleUploadedFile(name='test',
                                                    content=b'content'),
                'optional_param': '1',
            },
        ))

        self.assertTrue(hasattr(func, 'seen'))
        self.assertIsNone(result)

        self.assertEqual(
            func.required_fields,
            {
                'required_int': {
                    'type': IntFieldType,
                },
                'required_unicode_str': {
                    'type': StringFieldType,
                },
                'required_native_str': {
                    'type': StringFieldType,
                },
                'required_choice_list': {
                    'type': ChoiceFieldType,
                    'choices': ('a', 'b', 'c'),
                },
                'required_choice_tuple': {
                    'type': ChoiceFieldType,
                    'choices': ('a', 'b', 'c'),
                },
                'required_bool': {
                    'type': BooleanFieldType,
                },
                'required_file': {
                    'type': FileFieldType,
                },
            })

    def test_webapi_request_fields_call_with_unexpected_arg(self):
        """Testing @webapi_request_fields with unexpected argument"""
        @webapi_request_fields(
            required={
                'required_param': {
                    'type': IntFieldType,
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
                    'type': IntFieldType,
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
                    'type': IntFieldType,
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
                    'type': IntFieldType,
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
