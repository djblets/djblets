"""Unit tests for djblets.pagestate.templatetags.

Version Added:
    5.3
"""

from __future__ import annotations

from django.template import Context, Template
from django.test import RequestFactory

from djblets.pagestate.state import PageState
from djblets.testing.testcases import TestCase


class PageHookPointTests(TestCase):
    """Testing {% page_hook_point %}.

    Version Added:
        5.3
    """

    def test_with_injections(self) -> None:
        """Testing {% page_hook_point %} with injections"""
        request = RequestFactory().get('/')
        page_state = PageState.for_request(request)
        page_state.inject('test-point', {
            'content': 'Test 1\n',
        })
        page_state.inject('test-point', {
            'content': 'Test 2\n',
        })

        result = Template(
            '{% load djblets_pagestate %}'
            '{% page_hook_point "test-point" %}'
        ).render(Context({
            'request': request,
        }))

        self.assertEqual(result, 'Test 1\nTest 2\n')

    def test_without_injections(self) -> None:
        """Testing {% page_hook_point %} without injections"""
        request = RequestFactory().get('/')

        result = Template(
            '{% load djblets_pagestate %}'
            '{% page_hook_point "test-point" %}'
        ).render(Context({
            'request': request,
        }))

        self.assertEqual(result, '')
