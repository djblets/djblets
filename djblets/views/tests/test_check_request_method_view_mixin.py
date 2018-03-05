"""Unit tests for CheckRequestMethodViewMixin."""

from __future__ import unicode_literals

from django.http import HttpResponse
from django.test.client import RequestFactory
from django.views.generic.base import View

from djblets.testing.testcases import TestCase
from djblets.views.generic.base import CheckRequestMethodViewMixin


class BaseTestView(View):
    def dispatch(self, request, *args, **kwargs):
        # Note that we're not chaining up to View.dispatch, so that we don't
        # invoke its own method checks.
        return getattr(self, request.method.lower())(request, *args, **kwargs)


class CheckRequestMethodViewMixinTests(TestCase):
    """Unit tests for CheckRequestMethodViewMixin."""

    def test_dispatch_with_allowed(self):
        """Testing CheckRequestMethodViewMixin.dispatch with HTTP method
        allowed
        """
        class MyView(CheckRequestMethodViewMixin, BaseTestView):
            def get(self, *args, **kwargs):
                return HttpResponse('ok')

        view = MyView.as_view()
        response = view(RequestFactory().request())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'ok')

    def test_dispatch_with_not_allowed(self):
        """Testing CheckRequestMethodViewMixin.dispatch with HTTP method
        not allowed
        """
        class MyView(CheckRequestMethodViewMixin, BaseTestView):
            def get(self, *args, **kwargs):
                return HttpResponse('ok')

        view = MyView.as_view()
        response = view(RequestFactory().request(REQUEST_METHOD='POST'))

        self.assertEqual(response.status_code, 405)
        self.assertNotEqual(response.content, b'ok')
