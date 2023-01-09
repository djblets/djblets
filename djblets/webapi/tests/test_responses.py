import json
from typing import List

from django import forms
from django.contrib.auth.models import User
from django.test.client import RequestFactory
from django.utils.encoding import force_str

from djblets.deprecation import RemovedInDjblets40Warning
from djblets.testing.testcases import ExpectedWarning, TestCase
from djblets.webapi.encoders import BasicAPIEncoder
from djblets.webapi.errors import INVALID_ATTRIBUTE, INVALID_FORM_DATA
from djblets.webapi.resources.registry import unregister_resource
from djblets.webapi.resources.user import UserResource
from djblets.webapi.responses import (WebAPIResponse,
                                      WebAPIResponseError,
                                      WebAPIResponseFormError,
                                      WebAPIResponsePaginated)


class WebAPIResponseTests(TestCase):
    """Unit tests for djblets.webapi.responses.WebAPIResponse."""

    def test_init(self):
        """Testing WebAPIResponse.__init__"""
        request = RequestFactory().get('/')
        headers = {
            'Header1': 'value1',
        }
        encoders = [BasicAPIEncoder()]
        encoder_kwargs = {
            'xxx': 123,
        }

        response = WebAPIResponse(
            request=request,
            obj={
                'a': 1,
                'b': 2,
            },
            stat='ok',
            api_format='json',
            status=200,
            headers=headers,
            encoders=encoders,
            encoder_kwargs=encoder_kwargs,
            mimetype='application/json+test',
            supported_mimetypes=['application/json+test'])

        self.assertIs(response.request, request)
        self.assertEqual(response.api_data, {
            'a': 1,
            'b': 2,
            'stat': 'ok',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Header1'], 'value1')
        self.assertIs(response.encoders, encoders)
        self.assertEqual(response.encoder_kwargs, encoder_kwargs)
        self.assertEqual(response.mimetype, 'application/json+test')

    def test_init_with_deprecated_all_args(self):
        """Testing WebAPIResponse.__init__ with deprecated all-args invocation
        """
        request = RequestFactory().get('/')
        headers = {
            'Header1': 'value1',
        }
        encoders = [BasicAPIEncoder()]
        encoder_kwargs = {
            'xxx': 123,
        }

        message = (
            'Positional argument(s) "obj", "stat", "api_format", "status", '
            '"headers", "encoders", "encoder_kwargs", "mimetype", '
            '"supported_mimetypes" must be passed as keyword arguments when '
            'calling WebAPIResponse.__init__(). This will be required in '
            'Djblets 4.0.'
        )

        with self.assertWarns(RemovedInDjblets40Warning, message):
            response = WebAPIResponse(
                request,
                {
                    'a': 1,
                    'b': 2,
                },
                'ok',
                'json',
                200,
                headers,
                encoders,
                encoder_kwargs,
                'application/json+test',
                ['application/json+test'])

        self.assertIs(response.request, request)
        self.assertEqual(response.api_data, {
            'a': 1,
            'b': 2,
            'stat': 'ok',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Header1'], 'value1')
        self.assertEqual(response.encoders, encoders)
        self.assertEqual(response.encoder_kwargs, encoder_kwargs)
        self.assertEqual(response.mimetype, 'application/json+test')


class WebAPIResponsePaginatedTests(TestCase):
    """Unit tests for djblets.webapi.responses.WebAPIResponsePaginated."""

    def setUp(self):
        super(WebAPIResponsePaginatedTests, self).setUp()

        self.factory = RequestFactory()
        self.user_resource = UserResource()

    def tearDown(self):
        super(WebAPIResponsePaginatedTests, self).tearDown()

        unregister_resource(self.user_resource)

    def test_init(self):
        """Testing WebAPIResponsePaginated.__init__"""
        def _my_serialize(obj):
            return obj

        request = self.factory.get('/')
        headers = {
            'Header1': 'value1',
        }
        encoders = [BasicAPIEncoder()]
        encoder_kwargs = {
            'xxx': 123,
        }

        response = WebAPIResponsePaginated(
            request=request,
            queryset=User.objects.all(),
            results_key='my_results',
            prev_key='my_prev',
            next_key='my_next',
            total_results_key='my_total_results',
            start_param='my-start',
            max_results_param='my-max-results',
            default_start=10,
            default_max_results=100,
            max_results_cap=500,
            serialize_object_func=_my_serialize,
            extra_data={
                'extra1': 'value1',
            },
            stat='ok',
            api_format='json',
            status=200,
            headers=headers,
            encoders=encoders,
            encoder_kwargs=encoder_kwargs,
            mimetype='application/json+test',
            supported_mimetypes=['application/json+test'])

        self.assertIs(response.request, request)
        self.assertEqual(response.api_data, {
            'extra1': 'value1',
            'links': {
                'my_prev': {
                    'href': 'http://testserver/?my-start=0&my-max-results=100',
                    'method': 'GET',
                },
            },
            'my_results': [],
            'my_total_results': 0,
            'stat': 'ok',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Header1'], 'value1')
        self.assertEqual(response.encoders, encoders)
        self.assertEqual(response.encoder_kwargs, encoder_kwargs)
        self.assertEqual(response.mimetype, 'application/json+test')

    def test_init_with_deprecated_all_args(self):
        """Testing WebAPIResponsePaginated.__init__ with deprecated all-args
        invocation
        """
        def _my_serialize(obj):
            return obj

        request = self.factory.get('/')
        headers = {
            'Header1': 'value1',
        }
        encoders = [BasicAPIEncoder()]
        encoder_kwargs = {
            'xxx': 123,
        }

        warning_list: List[ExpectedWarning] = [
            {
                'cls': RemovedInDjblets40Warning,
                'message': (
                    'Positional argument(s) "queryset", "results_key", '
                    '"prev_key", "next_key", "total_results_key", '
                    '"start_param", "max_results_param", "default_start", '
                    '"default_max_results", "max_results_cap", '
                    '"serialize_object_func", "extra_data" must be passed '
                    'as keyword arguments when calling '
                    'WebAPIResponsePaginated.__init__(). This will be '
                    'required in Djblets 4.0.'
                ),
            },
            {
                'cls': RemovedInDjblets40Warning,
                'message': (
                    'Positional argument(s) "stat", "api_format", "status", '
                    '"headers", "encoders", "encoder_kwargs", "mimetype", '
                    '"supported_mimetypes" must be passed as keyword '
                    'arguments when calling WebAPIResponse.__init__(). This '
                    'will be required in Djblets 4.0.'
                ),
            },
        ]

        with self.assertWarnings(warning_list):
            response = WebAPIResponsePaginated(
                request,
                User.objects.all(),
                'my_results',
                'my_prev',
                'my_next',
                'my_total_results',
                'my-start',
                'my-max-results',
                10,
                100,
                500,
                _my_serialize,
                {
                    'extra1': 'value1',
                },
                'ok',
                'json',
                200,
                headers,
                encoders,
                encoder_kwargs,
                'application/json+test',
                ['application/json+test'])

        self.assertIs(response.request, request)
        self.assertEqual(response.api_data, {
            'extra1': 'value1',
            'links': {
                'my_prev': {
                    'href': 'http://testserver/?my-start=0&my-max-results=100',
                    'method': 'GET',
                },
            },
            'my_results': [],
            'my_total_results': 0,
            'stat': 'ok',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Header1'], 'value1')
        self.assertEqual(response.encoders, encoders)
        self.assertEqual(response.encoder_kwargs, encoder_kwargs)
        self.assertEqual(response.mimetype, 'application/json+test')

    def test_pagination_serialization_encoding(self):
        """Testing WebAPIResponsePaginated query parameter encoding"""
        # This test is for an issue when query parameters included unicode
        # characters. In this case, creating the 'self' or pagination links
        # would cause a KeyError. If this test runs fine without any uncaught
        # exceptions, then it means we're good.
        request = self.factory.get('/api/users/?q=%D0%B5')
        response = self.user_resource(request)

        rsp = json.loads(force_str(response.content))
        self.assertEqual(rsp['links']['self']['href'],
                         'http://testserver/api/users/?q=%D0%B5')


class WebAPIResponseErrorTests(TestCase):
    """Unit tests for djblets.webapi.responses.WebAPIResponseError."""

    def test_init(self):
        """Testing WebAPIResponseError.__init__"""
        request = RequestFactory().get('/')
        headers = {
            'Header1': 'value1',
        }
        encoders = [BasicAPIEncoder()]
        encoder_kwargs = {
            'xxx': 123,
        }

        response = WebAPIResponseError(
            request=request,
            err=INVALID_ATTRIBUTE,
            extra_params={
                'extra1': 'value1',
            },
            headers=headers,
            api_format='json',
            encoders=encoders,
            encoder_kwargs=encoder_kwargs,
            mimetype='application/json+test',
            supported_mimetypes=['application/json+test'])

        self.assertIs(response.request, request)
        self.assertEqual(response.api_data, {
            'err': {
                'code': INVALID_ATTRIBUTE.code,
                'msg': 'Invalid attribute',
            },
            'extra1': 'value1',
            'stat': 'fail',
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response['Header1'], 'value1')
        self.assertIs(response.encoders, encoders)
        self.assertEqual(response.encoder_kwargs, encoder_kwargs)
        self.assertEqual(response.mimetype, 'application/json+test')

    def test_init_with_deprecated_all_args(self):
        """Testing WebAPIResponseError.__init__ with deprecated all-args
        invocation
        """
        request = RequestFactory().get('/')
        headers = {
            'Header1': 'value1',
        }
        encoders = [BasicAPIEncoder()]
        encoder_kwargs = {
            'xxx': 123,
        }

        warning_list: List[ExpectedWarning] = [
            {
                'cls': RemovedInDjblets40Warning,
                'message': (
                    'Positional argument(s) "extra_params", "headers" must '
                    'be passed as keyword arguments when calling '
                    'WebAPIResponseError.__init__(). This will be required '
                    'in Djblets 4.0.'
                ),
            },
            {
                'cls': RemovedInDjblets40Warning,
                'message': (
                    'Positional argument(s) "api_format", "encoders", '
                    '"encoder_kwargs", "mimetype", '
                    '"supported_mimetypes" must be passed as keyword '
                    'arguments when calling WebAPIResponse.__init__(). This '
                    'will be required in Djblets 4.0.'
                ),
            },
        ]

        with self.assertWarnings(warning_list):
            response = WebAPIResponseError(
                request,
                INVALID_ATTRIBUTE,
                {
                    'extra1': 'value1',
                },
                headers,
                'json',
                encoders,
                encoder_kwargs,
                'application/json+test',
                ['application/json+test']
            )

        self.assertIs(response.request, request)
        self.assertEqual(response.api_data, {
            'err': {
                'code': INVALID_ATTRIBUTE.code,
                'msg': 'Invalid attribute',
            },
            'extra1': 'value1',
            'stat': 'fail',
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response['Header1'], 'value1')
        self.assertEqual(response.encoders, encoders)
        self.assertEqual(response.encoder_kwargs, encoder_kwargs)
        self.assertEqual(response.mimetype, 'application/json+test')


class WebAPIResponseFormErrorTests(TestCase):
    """Unit tests for djblets.webapi.responses.WebAPIResponseFormError."""

    def test_init(self):
        """Testing WebAPIResponseFormError.__init__"""
        class MyForm(forms.Form):
            my_field = forms.CharField(required=True)

        request = RequestFactory().get('/')
        headers = {
            'Header1': 'value1',
        }
        encoders = [BasicAPIEncoder()]
        encoder_kwargs = {
            'xxx': 123,
        }

        form = MyForm({})
        self.assertFalse(form.is_valid())

        response = WebAPIResponseFormError(
            request=request,
            form=form,
            headers=headers,
            api_format='json',
            encoders=encoders,
            encoder_kwargs=encoder_kwargs,
            mimetype='application/json+test',
            supported_mimetypes=['application/json+test'])

        self.assertIs(response.request, request)
        self.assertEqual(response.api_data, {
            'err': {
                'code': INVALID_FORM_DATA.code,
                'msg': 'One or more fields had errors',
            },
            'fields': {
                'my_field': ['This field is required.'],
            },
            'stat': 'fail',
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response['Header1'], 'value1')
        self.assertIs(response.encoders, encoders)
        self.assertEqual(response.encoder_kwargs, encoder_kwargs)
        self.assertEqual(response.mimetype, 'application/json+test')

    def test_init_with_deprecated_all_args(self):
        """Testing WebAPIResponseFormError.__init__ with deprecated all-args
        invocation
        """
        class MyForm(forms.Form):
            my_field = forms.CharField(required=True)

        request = RequestFactory().get('/')
        headers = {
            'Header1': 'value1',
        }
        encoders = [BasicAPIEncoder()]
        encoder_kwargs = {
            'xxx': 123,
        }

        form = MyForm({})
        self.assertFalse(form.is_valid())

        warning_list: List[ExpectedWarning] = [
            {
                'cls': RemovedInDjblets40Warning,
                'message': (
                    'Positional argument(s) "headers" must be passed as '
                    'keyword arguments when calling '
                    'WebAPIResponseError.__init__(). This will be required '
                    'in Djblets 4.0.'
                ),
            },
            {
                'cls': RemovedInDjblets40Warning,
                'message': (
                    'Positional argument(s) "api_format", "encoders", '
                    '"encoder_kwargs", "mimetype", '
                    '"supported_mimetypes" must be passed as keyword '
                    'arguments when calling WebAPIResponse.__init__(). This '
                    'will be required in Djblets 4.0.'
                ),
            },
        ]

        with self.assertWarnings(warning_list):
            response = WebAPIResponseFormError(
                request,
                form,
                headers,
                'json',
                encoders,
                encoder_kwargs,
                'application/json+test',
                ['application/json+test']
            )

        self.assertIs(response.request, request)
        self.assertEqual(response.api_data, {
            'err': {
                'code': INVALID_FORM_DATA.code,
                'msg': 'One or more fields had errors',
            },
            'fields': {
                'my_field': ['This field is required.'],
            },
            'stat': 'fail',
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response['Header1'], 'value1')
        self.assertEqual(response.encoders, encoders)
        self.assertEqual(response.encoder_kwargs, encoder_kwargs)
        self.assertEqual(response.mimetype, 'application/json+test')
