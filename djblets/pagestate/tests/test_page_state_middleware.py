"""Unit tests for djblets.pagestate.middleware.PageStateMiddleware.

Version Added:
    5.3
"""

from __future__ import annotations

from django.http import HttpResponse
from django.template import Context, Template
from django.test import RequestFactory

from djblets.pagestate.state import PageState
from djblets.pagestate.middleware import PageStateMiddleware
from djblets.testing.testcases import TestCase


class PageStateMiddlewareTests(TestCase):
    """Unit tests for PageStateMiddleware.

    Version Added:
        5.3
    """

    def test_with_etag_and_injections(self) -> None:
        """Testing PageStateMiddleware with response ETag, PageState, and
        injections
        """
        request = RequestFactory().get('/')

        page_state = PageState.for_request(request)
        page_state.inject('test', {
            'content': 'Test',
            'etag': 'test',
        })

        response = HttpResponse(Template(
            '{% load djblets_pagestate %}'
            '{% page_hook_point "test" %}'
        ).render(Context({
            'request': request,
        })))
        response['ETag'] = 'test'

        new_response = PageStateMiddleware(lambda request: response)(request)

        self.assertIs(new_response, response)
        self.assertEqual(
            response['ETag'],
            '8f286193e023cd52b89af86cc9a5588f329e67c4381ec1eb6cc9c49ced471907')

    def test_without_response_etag(self) -> None:
        """Testing PageStateMiddleware without response ETag"""
        request = RequestFactory().get('/')

        page_state = PageState.for_request(request)
        page_state.inject('test', {
            'content': 'Test',
            'etag': 'test',
        })

        response = HttpResponse(Template(
            '{% load djblets_pagestate %}'
            '{% page_hook_point "test" %}'
        ).render(Context({
            'request': request,
        })))

        new_response = PageStateMiddleware(lambda request: response)(request)

        self.assertIs(new_response, response)
        self.assertNotIn('ETag', response)

    def test_without_page_state(self) -> None:
        """Testing PageStateMiddleware with response ETag and without
        PageState
        """
        request = RequestFactory().get('/')

        response = HttpResponse(Template(
            '{% load djblets_pagestate %}'
        ).render(Context({
            'request': request,
        })))
        response['ETag'] = 'test'

        new_response = PageStateMiddleware(lambda request: response)(request)

        self.assertIs(new_response, response)
        self.assertEqual(response['ETag'], 'test')

    def test_without_injections(self) -> None:
        """Testing PageStateMiddleware with response ETag and PageState,
        without injections
        """
        request = RequestFactory().get('/')

        response = HttpResponse(Template(
            '{% load djblets_pagestate %}'
            '{% page_hook_point "test" %}'
        ).render(Context({
            'request': request,
        })))
        response['ETag'] = 'test'

        new_response = PageStateMiddleware(lambda request: response)(request)

        self.assertIs(new_response, response)
        self.assertEqual(response['ETag'], 'test')
