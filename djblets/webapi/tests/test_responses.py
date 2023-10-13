"""Unit tests for djblets.webapi.responses."""

from __future__ import annotations

import json
from typing import Optional

from django import forms
from django.contrib.auth.models import User
from django.test.client import RequestFactory
from django.utils.encoding import force_str

from djblets.testing.testcases import TestCase
from djblets.webapi.encoders import BasicAPIEncoder
from djblets.webapi.errors import (INVALID_ATTRIBUTE,
                                   INVALID_FORM_DATA,
                                   WebAPIError)
from djblets.webapi.resources.registry import unregister_resource
from djblets.webapi.resources.user import UserResource
from djblets.webapi.responses import (WebAPIEventStreamMessage,
                                      WebAPIEventStreamMessages,
                                      WebAPIResponse,
                                      WebAPIResponseError,
                                      WebAPIResponseEventStream,
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

    def test_pagination_serialization_encoding(self):
        """Testing WebAPIResponsePaginated query parameter encoding"""
        # This test is for an issue when query parameters included unicode
        # characters. In this case, creating the 'self' or pagination links
        # would cause a KeyError. If this test runs fine without any uncaught
        # exceptions, then it means we're good.
        request = self.factory.get('/api/users/?q=%D0%B5')
        response = self.user_resource(request)

        assert isinstance(response, WebAPIResponsePaginated)

        rsp = json.loads(force_str(response.content))
        self.assertEqual(rsp['links']['self']['href'],
                         'http://testserver/api/users/?q=%D0%B5')


class WebAPIResponseErrorTests(TestCase):
    """Unit tests for djblets.webapi.responses.WebAPIResponseError."""

    def setUp(self) -> None:
        super().setUp()

        self.request = RequestFactory().get('/')
        self.encoders = [BasicAPIEncoder()]

    def test_init(self):
        """Testing WebAPIResponseError.__init__"""
        headers = {
            'Header1': 'value1',
        }
        encoder_kwargs = {
            'xxx': 123,
        }

        response = WebAPIResponseError(
            request=self.request,
            err=INVALID_ATTRIBUTE,
            extra_params={
                'extra1': 'value1',
            },
            headers=headers,
            api_format='json',
            encoders=self.encoders,
            encoder_kwargs=encoder_kwargs,
            mimetype='application/json+test',
            supported_mimetypes=['application/json+test'])

        self.assertIs(response.request, self.request)
        self.assertEqual(response.api_data, {
            'err': {
                'code': INVALID_ATTRIBUTE.code,
                'msg': INVALID_ATTRIBUTE.msg,
                'type': INVALID_ATTRIBUTE.error_type,
            },
            'extra1': 'value1',
            'stat': 'fail',
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response['Header1'], 'value1')
        self.assertIs(response.encoders, self.encoders)
        self.assertEqual(response.encoder_kwargs, encoder_kwargs)
        self.assertEqual(response.mimetype, 'application/json+test')

    def test_with_all_fields(self) -> None:
        """Testing WebAPIResponseError with all WebAPIError fields"""
        response = WebAPIResponseError(
            request=self.request,
            err=WebAPIError(
                code=911,
                msg='This is a thing that went wrong.',
                error_type='oh-nosers',
                error_subtype='super-oh-nosers',
                detail='The thing went VERY wrong!'),
            api_format='json',
            encoders=self.encoders,
            mimetype='application/json+test',
            supported_mimetypes=['application/json+test'])

        self.assertEqual(
            response.api_data,
            {
                'err': {
                    'code': 911,
                    'detail': 'The thing went VERY wrong!',
                    'msg': 'This is a thing that went wrong.',
                    'subtype': 'super-oh-nosers',
                    'type': 'oh-nosers',
                },
                'stat': 'fail',
            })

    def test_with_subtype_no_type(self) -> None:
        """Testing WebAPIResponseError with WebAPIError containing subtype
        but no type
        """
        response = WebAPIResponseError(
            request=self.request,
            err=WebAPIError(
                code=911,
                msg='This is a thing that went wrong.',
                error_subtype='super-oh-nosers',
                detail='The thing went VERY wrong!'),
            api_format='json',
            encoders=self.encoders,
            mimetype='application/json+test',
            supported_mimetypes=['application/json+test'])

        self.assertEqual(
            response.api_data,
            {
                'err': {
                    'code': 911,
                    'detail': 'The thing went VERY wrong!',
                    'msg': 'This is a thing that went wrong.',
                },
                'stat': 'fail',
            })


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
                'msg': INVALID_FORM_DATA.msg,
                'type': INVALID_FORM_DATA.error_type,
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


class WebAPIResponseEventStreamTests(TestCase):
    """Unit tests for WebAPIResponseEventStream.

    Version Added:
        4.0
    """

    def test_with_generator(self) -> None:
        """Testing WebAPIResponseEventStream with generator"""
        request = RequestFactory().get('/')
        response = WebAPIResponseEventStream(
            (
                WebAPIEventStreamMessage(
                    obj={
                        'key': i,
                    })
                for i in range(5)
            ),
            request=request,
        )

        self.assertEqual(
            list(response),
            [
                b'data: {"key": 0, "stat": "ok"}\n'
                b'\n',

                b'data: {"key": 1, "stat": "ok"}\n'
                b'\n',

                b'data: {"key": 2, "stat": "ok"}\n'
                b'\n',

                b'data: {"key": 3, "stat": "ok"}\n'
                b'\n',

                b'data: {"key": 4, "stat": "ok"}\n'
                b'\n',
            ])
        self.assertEqual(response['Content-Type'], 'text/event-stream')
        self.assertEqual(response['X-Event-Data-Mimetype'],
                         'application/json')

    def test_with_callable(self) -> None:
        """Testing WebAPIResponseEventStream with callable"""
        def _gen_messages(
            last_id: Optional[str],
        ) -> WebAPIEventStreamMessages:
            for i in range(5):
                yield WebAPIEventStreamMessage(
                    obj={
                        'key': i,
                    },
                    stat='progress')

            yield WebAPIEventStreamMessage()

        request = RequestFactory().get('/')
        response = WebAPIResponseEventStream(_gen_messages,
                                             request=request)

        self.assertEqual(
            list(response),
            [
                b'data: {"key": 0, "stat": "progress"}\n'
                b'\n',

                b'data: {"key": 1, "stat": "progress"}\n'
                b'\n',

                b'data: {"key": 2, "stat": "progress"}\n'
                b'\n',

                b'data: {"key": 3, "stat": "progress"}\n'
                b'\n',

                b'data: {"key": 4, "stat": "progress"}\n'
                b'\n',

                b'data: {"stat": "ok"}\n'
                b'\n',
            ])

    def test_with_all_fields(self) -> None:
        """Testing EventStreamHttpResponse with all field types"""
        request = RequestFactory().get('/')
        response = WebAPIResponseEventStream(
            (
                WebAPIEventStreamMessage(
                    event='update',
                    id=f'id-{i}',
                    obj={
                        'key': i,
                    },
                    retry_ms=123)
                for i in range(5)
            ),
            request=request,
        )

        self.assertEqual(
            list(response),
            [
                b'id: id-0\n'
                b'event: update\n'
                b'data: {"key": 0, "stat": "ok"}\n'
                b'retry: 123\n'
                b'\n',

                b'id: id-1\n'
                b'event: update\n'
                b'data: {"key": 1, "stat": "ok"}\n'
                b'retry: 123\n'
                b'\n',

                b'id: id-2\n'
                b'event: update\n'
                b'data: {"key": 2, "stat": "ok"}\n'
                b'retry: 123\n'
                b'\n',

                b'id: id-3\n'
                b'event: update\n'
                b'data: {"key": 3, "stat": "ok"}\n'
                b'retry: 123\n'
                b'\n',

                b'id: id-4\n'
                b'event: update\n'
                b'data: {"key": 4, "stat": "ok"}\n'
                b'retry: 123\n'
                b'\n',
            ])

    def test_with_all_data(self) -> None:
        """Testing EventStreamHttpResponse with custom data value"""
        request = RequestFactory().get('/')
        response = WebAPIResponseEventStream(
            (
                WebAPIEventStreamMessage(data='test')
                for i in range(5)
            ),
            request=request,
        )

        self.assertEqual(
            list(response),
            [
                b'data: test\n'
                b'\n',

                b'data: test\n'
                b'\n',

                b'data: test\n'
                b'\n',

                b'data: test\n'
                b'\n',

                b'data: test\n'
                b'\n',
            ])

    def test_with_response_mimetype(self) -> None:
        """Testing EventStreamHttpResponse with response mimetype"""
        request = RequestFactory().get('/')
        response = WebAPIResponseEventStream(
            (
                WebAPIEventStreamMessage(obj={
                    'key': i,
                })
                for i in range(5)
            ),
            request=request,
            message_data_mimetype='application/vnd.foo.resource+json')

        self.assertEqual(
            list(response),
            [
                b'data: {"key": 0, "stat": "ok"}\n'
                b'\n',

                b'data: {"key": 1, "stat": "ok"}\n'
                b'\n',

                b'data: {"key": 2, "stat": "ok"}\n'
                b'\n',

                b'data: {"key": 3, "stat": "ok"}\n'
                b'\n',

                b'data: {"key": 4, "stat": "ok"}\n'
                b'\n',
            ])
        self.assertEqual(response['Content-Type'], 'text/event-stream')
        self.assertEqual(response['X-Event-Data-Mimetype'],
                         'application/vnd.foo.resource+json')

    def test_with_accept_mimetype(self) -> None:
        """Testing EventStreamHttpResponse with Accept: <mimetype> header"""
        request = RequestFactory().get(
            '/',
            HTTP_ACCEPT='application/xml')

        response = WebAPIResponseEventStream(
            (
                WebAPIEventStreamMessage(obj={
                    'key': i,
                })
                for i in range(5)
            ),
            request=request)

        self.assertEqual(
            list(response),
            [
                b'data: <?xml version="1.0" encoding="utf-8"?>\n'
                b'data: <rsp>\n'
                b'data:  <stat>ok</stat>\n'
                b'data:  <key>0</key>\n'
                b'data: </rsp>\n'
                b'\n',

                b'data: <?xml version="1.0" encoding="utf-8"?>\n'
                b'data: <rsp>\n'
                b'data:  <stat>ok</stat>\n'
                b'data:  <key>1</key>\n'
                b'data: </rsp>\n'
                b'\n',

                b'data: <?xml version="1.0" encoding="utf-8"?>\n'
                b'data: <rsp>\n'
                b'data:  <stat>ok</stat>\n'
                b'data:  <key>2</key>\n'
                b'data: </rsp>\n'
                b'\n',

                b'data: <?xml version="1.0" encoding="utf-8"?>\n'
                b'data: <rsp>\n'
                b'data:  <stat>ok</stat>\n'
                b'data:  <key>3</key>\n'
                b'data: </rsp>\n'
                b'\n',

                b'data: <?xml version="1.0" encoding="utf-8"?>\n'
                b'data: <rsp>\n'
                b'data:  <stat>ok</stat>\n'
                b'data:  <key>4</key>\n'
                b'data: </rsp>\n'
                b'\n',
            ])
        self.assertEqual(response['Content-Type'], 'text/event-stream')
        self.assertEqual(response['X-Event-Data-Mimetype'], 'application/xml')

    def test_with_api_format_get(self) -> None:
        """Testing EventStreamHttpResponse with ?api_format in GET"""
        request = RequestFactory().get('/?api_format=xml')

        response = WebAPIResponseEventStream(
            (
                WebAPIEventStreamMessage(obj={
                    'key': i,
                })
                for i in range(5)
            ),
            request=request)

        self.assertEqual(
            list(response),
            [
                b'data: <?xml version="1.0" encoding="utf-8"?>\n'
                b'data: <rsp>\n'
                b'data:  <stat>ok</stat>\n'
                b'data:  <key>0</key>\n'
                b'data: </rsp>\n'
                b'\n',

                b'data: <?xml version="1.0" encoding="utf-8"?>\n'
                b'data: <rsp>\n'
                b'data:  <stat>ok</stat>\n'
                b'data:  <key>1</key>\n'
                b'data: </rsp>\n'
                b'\n',

                b'data: <?xml version="1.0" encoding="utf-8"?>\n'
                b'data: <rsp>\n'
                b'data:  <stat>ok</stat>\n'
                b'data:  <key>2</key>\n'
                b'data: </rsp>\n'
                b'\n',

                b'data: <?xml version="1.0" encoding="utf-8"?>\n'
                b'data: <rsp>\n'
                b'data:  <stat>ok</stat>\n'
                b'data:  <key>3</key>\n'
                b'data: </rsp>\n'
                b'\n',

                b'data: <?xml version="1.0" encoding="utf-8"?>\n'
                b'data: <rsp>\n'
                b'data:  <stat>ok</stat>\n'
                b'data:  <key>4</key>\n'
                b'data: </rsp>\n'
                b'\n',
            ])
        self.assertEqual(response['Content-Type'], 'text/event-stream')
        self.assertEqual(response['X-Event-Data-Mimetype'], 'application/xml')

    def test_with_api_format_post(self) -> None:
        """Testing EventStreamHttpResponse with ?api_format in POST"""
        request = RequestFactory().post('/', {
            'api_format': 'xml',
        })

        response = WebAPIResponseEventStream(
            (
                WebAPIEventStreamMessage(obj={
                    'key': i,
                })
                for i in range(5)
            ),
            request=request)

        self.assertEqual(
            list(response),
            [
                b'data: <?xml version="1.0" encoding="utf-8"?>\n'
                b'data: <rsp>\n'
                b'data:  <stat>ok</stat>\n'
                b'data:  <key>0</key>\n'
                b'data: </rsp>\n'
                b'\n',

                b'data: <?xml version="1.0" encoding="utf-8"?>\n'
                b'data: <rsp>\n'
                b'data:  <stat>ok</stat>\n'
                b'data:  <key>1</key>\n'
                b'data: </rsp>\n'
                b'\n',

                b'data: <?xml version="1.0" encoding="utf-8"?>\n'
                b'data: <rsp>\n'
                b'data:  <stat>ok</stat>\n'
                b'data:  <key>2</key>\n'
                b'data: </rsp>\n'
                b'\n',

                b'data: <?xml version="1.0" encoding="utf-8"?>\n'
                b'data: <rsp>\n'
                b'data:  <stat>ok</stat>\n'
                b'data:  <key>3</key>\n'
                b'data: </rsp>\n'
                b'\n',

                b'data: <?xml version="1.0" encoding="utf-8"?>\n'
                b'data: <rsp>\n'
                b'data:  <stat>ok</stat>\n'
                b'data:  <key>4</key>\n'
                b'data: </rsp>\n'
                b'\n',
            ])
        self.assertEqual(response['Content-Type'], 'text/event-stream')
        self.assertEqual(response['X-Event-Data-Mimetype'], 'application/xml')
