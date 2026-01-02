"""Unit tests for djblets.pagestate.state.PageState.

Version Added:
    5.3
"""

from __future__ import annotations

import inspect
import logging
from typing import TYPE_CHECKING

from django.template import Context
from django.test import RequestFactory

from djblets.pagestate.injectors import page_state_injectors
from djblets.pagestate.state import PageState, logger
from djblets.testing.testcases import TestCase

if TYPE_CHECKING:
    from collections.abc import Iterator

    from django.http import HttpRequest

    from djblets.pagestate.state import PageStateData


class MyPageStateInjector:
    """Injector used for unit tests.

    Version Added:
        5.3
    """

    injector_id = 'test-injector'

    def iter_page_state_data(
        self,
        *,
        point_name: str,
        request: HttpRequest,
        context: Context,
    ) -> Iterator[PageStateData]:
        """Generate page state data.

        This generates three sample sets of data:

        1. Content
        2. Content with ETag
        3. ETag-only

        Args:
            point_name (str):
                The template hook point name to populate.

            request (django.http.HttpRequest):
                The HTTP request from the client.

            context (django.template.Context):
                The context for the templates.

        Yields:
            djblets.pagestate.state.PageStateData:
            Data for each rendered template hook.
        """
        yield {
            'content': 'Test...',
        }

        if point_name == 'error':
            raise Exception('oh no!')

        yield {
            'content': f'Hello from {point_name}',
            'etag': f'etag-{point_name}',
        }

        yield {
            'etag': 'just-etag',
        }


class PageStateTests(TestCase):
    """Unit tests for PageState.

    Version Added:
        5.3
    """

    def test_for_request(self) -> None:
        """Testing PageState.for_request"""
        request = RequestFactory().get('/')

        page_state = PageState.for_request(request)

        self.assertIsNotNone(page_state)

        self.assertIs(page_state, PageState.for_request(request))

    def test_for_request_with_only_if_exists_and_exists(self) -> None:
        """Testing PageState.for_request with only_if_exists=True and
        exists
        """
        request = RequestFactory().get('/')

        page_state = PageState.for_request(request, only_if_exists=True)

        self.assertIsNone(page_state)

    def test_for_request_with_only_if_exists_and_not_exists(self) -> None:
        """Testing PageState.for_request with only_if_exists=True and does
        not exist
        """
        request = RequestFactory().get('/')

        page_state1 = PageState.for_request(request)
        page_state2 = PageState.for_request(request, only_if_exists=True)

        self.assertIsNotNone(page_state2)
        self.assertIs(page_state1, page_state2)

    def test_inject(self) -> None:
        """Testing PageState.inject"""
        page_state = PageState()
        page_state.inject('test-point1', {
            'content': 'Test 1',
        })
        page_state.inject('test-point1', {
            'content': 'Test 2',
            'etag': 'my-etag',
        })
        page_state.inject('test-point2', {
            'content': 'Test 3',
        })

        self.assertEqual(page_state._data, {
            'test-point1': [
                {
                    'content': 'Test 1',
                },
                {
                    'content': 'Test 2',
                    'etag': 'my-etag',
                },
            ],
            'test-point2': [
                {
                    'content': 'Test 3',
                },
            ],
        })

    def test_clear_injections_with_all_points(self) -> None:
        """Testing PageState.clear_injections with all points"""
        page_state = PageState()
        page_state.inject('test-point1', {
            'content': 'Test 1',
        })
        page_state.inject('test-point1', {
            'content': 'Test 2',
            'etag': 'my-etag',
        })
        page_state.inject('test-point2', {
            'content': 'Test 3',
        })
        page_state.clear_injections()

        self.assertEqual(page_state._data, {})

    def test_clear_injections_with_point_name(self) -> None:
        """Testing PageState.clear_injections with point name"""
        page_state = PageState()
        page_state.inject('test-point1', {
            'content': 'Test 1',
        })
        page_state.inject('test-point1', {
            'content': 'Test 2',
            'etag': 'my-etag',
        })
        page_state.inject('test-point2', {
            'content': 'Test 3',
        })
        page_state.clear_injections('test-point1')

        self.assertEqual(page_state._data, {
            'test-point2': [
                {
                    'content': 'Test 3',
                },
            ],
        })

    def test_get_etag(self) -> None:
        """Testing PageState.get_etag"""
        request = RequestFactory().get('/')
        context = Context({
            'request': request,
        })

        page_state = PageState()
        page_state.inject('test-point', {
            'etag': 'my-etag',
        })

        list(page_state.iter_content(point_name='test-point',
                                     request=request,
                                     context=context))

        self.assertEqual(
            page_state.get_etag(),
            'f65b90c21028a6de099c2415a9c4e0cb1b97f5c0e3c2d9e4e37672b24ecfa256')

    def test_get_etag_with_no_etags(self) -> None:
        """Testing PageState.get_etag with no ETags processed"""
        page_state = PageState()
        self.assertEqual(page_state.get_etag(), '')

    def test_iter_content(self) -> None:
        """Testing PageState.iter_content"""
        request = RequestFactory().get('/')
        context = Context({
            'request': request,
        })

        page_state = PageState()
        page_state.inject('test-point', {
            'content': 'Manually injected',
        })

        injector = MyPageStateInjector()

        try:
            page_state_injectors.register(injector)

            results_gen = page_state.iter_content(point_name='test-point',
                                                  request=request,
                                                  context=context)
            self.assertTrue(inspect.isgenerator(results_gen))

            results = list(results_gen)
        finally:
            page_state_injectors.unregister(injector)

        self.assertEqual(
            results,
            [
                'Test...',
                'Hello from test-point',
                'Manually injected',
            ])

        # Check the ETag.
        self.assertEqual(
            page_state.get_etag(),
            '130fb40ea2247871bc8d25c30b2c84d8a0f41b8854f1a26cacc38e29bd86aa15')

    def test_iter_content_with_injector_failure(self) -> None:
        """Testing PageState.iter_content with injector failure"""
        request = RequestFactory().get('/')
        context = Context({
            'request': request,
        })

        page_state = PageState()
        page_state.inject('error', {
            'content': 'Manually injected',
        })

        injector = MyPageStateInjector()

        try:
            page_state_injectors.register(injector)

            with self.assertLogs(logger, level=logging.DEBUG) as logs_cm:
                results = list(page_state.iter_content(point_name='error',
                                                       request=request,
                                                       context=context))
        finally:
            page_state_injectors.unregister(injector)

        self.assertEqual(
            results,
            [
                'Test...',
                'Manually injected',
            ])

        # Check the ETag.
        self.assertEqual(
            page_state.get_etag(),
            'be545b7118ba27fc5e13b7e85beaef15007273903288ba64f1513a0044b70d9f')

        self.assertEqual(len(logs_cm.output), 1)
        self.assertTrue(logs_cm.output[0].startswith(
            'ERROR:djblets.pagestate.state:Error iterating through page '
            'state data for injector <djblets.pagestate.tests.test_page_state.'
            'MyPageStateInjector object at 0x'
        ))
