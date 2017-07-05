"""Unit tests for PrePostDispatchViewMixin."""

from __future__ import unicode_literals

from django.http import HttpResponse, HttpResponseForbidden
from django.test.client import RequestFactory
from django.views.generic.base import View

from djblets.testing.testcases import TestCase
from djblets.views.generic.base import PrePostDispatchViewMixin


class PrePostDispatchViewMixinTests(TestCase):
    """Unit tests for PrePostDispatchViewMixin."""

    def test_dispatch(self):
        """Testing PrePostDispatchViewMixin.dispatch"""
        seen = set()

        class MyView(PrePostDispatchViewMixin, View):
            def pre_dispatch(self, *args, **kwargs):
                seen.add('pre_dispatch')

            def post_dispatch(self, response, *args, **kwargs):
                seen.add('post_dispatch')

                return response

        view = MyView.as_view()
        response = view(RequestFactory().request())

        self.assertEquals(seen, {'pre_dispatch', 'post_dispatch'})
        self.assertIsInstance(response, HttpResponse)

    def test_dispatch_with_pre_dispatch_response(self):
        """Testing PrePostDispatchViewMixin.pre_dispatch with custom response
        """
        class MyView(PrePostDispatchViewMixin, View):
            def pre_dispatch(self, *args, **kwargs):
                return HttpResponseForbidden()

        view = MyView.as_view()
        response = view(RequestFactory().request())

        self.assertIsInstance(response, HttpResponseForbidden)

    def test_dispatch_with_post_dispatch_response(self):
        """Testing PrePostDispatchViewMixin.post_dispatch with custom response
        """
        class MyView(PrePostDispatchViewMixin, View):
            def post_dispatch(self, *args, **kwargs):
                return HttpResponseForbidden()

        view = MyView.as_view()
        response = view(RequestFactory().request())

        self.assertIsInstance(response, HttpResponseForbidden)
