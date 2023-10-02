"""Unit tests for djblets.http.responses.EventStreamHttpResponse.

Version Added:
    4.0
"""

from __future__ import annotations

from typing import Optional

from django.middleware.gzip import GZipMiddleware
from django.test.client import RequestFactory

from djblets.http.responses import (EventStreamHttpResponse,
                                    EventStreamMessages)
from djblets.testing.testcases import TestCase


class EventStreamHttpResponseTests(TestCase):
    """Unit tests for EventStreamHttpResponse.

    Version Added:
        4.0
    """

    def test_with_generator(self) -> None:
        """Testing EventStreamHttpResponse with generator"""
        response = EventStreamHttpResponse(
            (
                {
                    'data': b'This is message %d.' % i,
                }
                for i in range(5)
            )
        )

        self.assertEqual(
            list(response),
            [
                b'data: This is message 0.\n'
                b'\n',

                b'data: This is message 1.\n'
                b'\n',

                b'data: This is message 2.\n'
                b'\n',

                b'data: This is message 3.\n'
                b'\n',

                b'data: This is message 4.\n'
                b'\n',
            ])

    def test_with_callable(self) -> None:
        """Testing EventStreamHttpResponse with callable"""
        def _gen_messages(
            last_id: Optional[str],
        ) -> EventStreamMessages:
            self.assertIsNone(last_id)

            for i in range(5):
                yield {
                    'data': f'This is message {i}.',
                }

        response = EventStreamHttpResponse(_gen_messages)

        self.assertEqual(
            list(response),
            [
                b'data: This is message 0.\n'
                b'\n',

                b'data: This is message 1.\n'
                b'\n',

                b'data: This is message 2.\n'
                b'\n',

                b'data: This is message 3.\n'
                b'\n',

                b'data: This is message 4.\n'
                b'\n',
            ])

    def test_with_all_fields(self) -> None:
        """Testing EventStreamHttpResponse with all field types"""
        response = EventStreamHttpResponse(
            (
                {
                    'data': f'This is message {i}.',
                    'event': 'update',
                    'id': f'id-{i}',
                    'retry_ms': 123,
                }
                for i in range(5)
            )
        )

        self.assertEqual(
            list(response),
            [
                b'id: id-0\n'
                b'event: update\n'
                b'data: This is message 0.\n'
                b'retry: 123\n'
                b'\n',

                b'id: id-1\n'
                b'event: update\n'
                b'data: This is message 1.\n'
                b'retry: 123\n'
                b'\n',

                b'id: id-2\n'
                b'event: update\n'
                b'data: This is message 2.\n'
                b'retry: 123\n'
                b'\n',

                b'id: id-3\n'
                b'event: update\n'
                b'data: This is message 3.\n'
                b'retry: 123\n'
                b'\n',

                b'id: id-4\n'
                b'event: update\n'
                b'data: This is message 4.\n'
                b'retry: 123\n'
                b'\n',
            ])

    def test_with_all_blank_id(self) -> None:
        """Testing EventStreamHttpResponse with blank ID"""
        response = EventStreamHttpResponse(
            (
                {
                    'id': '',
                    'data': f'test {i}',
                }
                for i in range(2)
            )
        )

        self.assertEqual(
            list(response),
            [
                b'id\n'
                b'data: test 0\n'
                b'\n',

                b'id\n'
                b'data: test 1\n'
                b'\n',
            ])

    def test_with_all_multiline_data(self) -> None:
        """Testing EventStreamHttpResponse with multi-line data"""
        response = EventStreamHttpResponse(
            (
                {
                    'data': ''.join(
                        f'this is line {j + 1}\n'
                        for j in range(i + 1)
                    )
                }
                for i in range(3)
            )
        )

        self.assertEqual(
            list(response),
            [
                b'data: this is line 1\n'
                b'\n',

                b'data: this is line 1\n'
                b'data: this is line 2\n'
                b'\n',

                b'data: this is line 1\n'
                b'data: this is line 2\n'
                b'data: this is line 3\n'
                b'\n',
            ])

    def test_with_last_event_id(self) -> None:
        """Testing EventStreamHttpResponse with Last-Event-ID"""
        def _gen_messages(
            last_id: Optional[str],
        ) -> EventStreamMessages:
            assert last_id == '3'

            for i in range(int(last_id), 5):
                yield {
                    'data': f'This is message {i}.',
                }

        request = RequestFactory().get('/', HTTP_LAST_EVENT_ID='3')

        response = EventStreamHttpResponse(_gen_messages,
                                           request=request)

        self.assertEqual(
            list(response),
            [
                b'data: This is message 3.\n'
                b'\n',

                b'data: This is message 4.\n'
                b'\n',
            ])

    def test_with_gzip_middleware(self) -> None:
        """Testing EventStreamHttpResponse with GZipMiddleware"""

        # NOTE: django-stubs hard-codes HttpResponse as the result of the
        #       lambda, so we have to ignore the typing.
        middleware = GZipMiddleware(
            lambda request: EventStreamHttpResponse(  # type: ignore
                (
                    {
                        'data': f'This is message {i}.',
                        'event': 'update',
                        'id': f'id-{i}',
                        'retry_ms': 123,
                    }
                    for i in range(5)
                ),
                request=request))

        response = middleware(
            RequestFactory().get('/', HTTP_LAST_EVENT_ID='3'))

        self.assertEqual(
            list(response),
            [
                b'id: id-0\n'
                b'event: update\n'
                b'data: This is message 0.\n'
                b'retry: 123\n'
                b'\n',

                b'id: id-1\n'
                b'event: update\n'
                b'data: This is message 1.\n'
                b'retry: 123\n'
                b'\n',

                b'id: id-2\n'
                b'event: update\n'
                b'data: This is message 2.\n'
                b'retry: 123\n'
                b'\n',

                b'id: id-3\n'
                b'event: update\n'
                b'data: This is message 3.\n'
                b'retry: 123\n'
                b'\n',

                b'id: id-4\n'
                b'event: update\n'
                b'data: This is message 4.\n'
                b'retry: 123\n'
                b'\n',
            ])
