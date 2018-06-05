"""Unit tests for djblets.configforms.views.ConfigPagesView."""

from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.http import Http404
from django.test.client import RequestFactory
from django.utils import six

from djblets.configforms.forms import ConfigPageForm
from djblets.configforms.pages import ConfigPage
from djblets.configforms.views import ConfigPagesView
from djblets.testing.testcases import TestCase


class TestForm1(ConfigPageForm):
    form_id = 'my-form-1'
    form_title = 'Form 1'

    def save(self):
        pass


class TestForm2(ConfigPageForm):
    form_id = 'my-form-2'
    form_title = 'Form 2'


class TestForm3(ConfigPageForm):
    form_id = 'my-form-3'
    form_title = 'Form 3'

    def is_visible(self):
        return False


class TestPage1(ConfigPage):
    page_id = 'my-page-1'
    form_classes = [TestForm1]


class TestPage2(ConfigPage):
    page_id = 'my-page-2'
    form_classes = [TestForm2]


class TestPage3(ConfigPage):
    page_id = 'my-page-3'
    form_classes = [TestForm3]


class MyConfigPagesView(ConfigPagesView):
    title = 'My Page Title'
    nav_title = 'My Nav Entry'
    page_classes = [TestPage1, TestPage2, TestPage3]

    css_bundle_names = ['my-css-bundle']
    js_bundle_names = ['my-js-bundle']

    js_model_class = 'MyModel'
    js_view_class = 'MyView'

    def get_js_model_data(self):
        return {
            'my-attr': 'value',
        }

    def get_js_view_data(self):
        return {
            'my-option': 'value',
        }


class ConfigPagesViewTests(TestCase):
    """Unit tests for djblets.configforms.views.ConfigPagesView."""

    def test_dispatch_initial_state(self):
        """Testing ConfigPagesView.dispatch initial state"""
        request = RequestFactory().request()
        request.user = User.objects.create(username='test-user')

        view = MyConfigPagesView()
        view.request = request

        response = view.dispatch(view.request)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(view.pages), 2)
        self.assertIsInstance(view.pages[0], TestPage1)
        self.assertIsInstance(view.pages[1], TestPage2)
        self.assertEqual(set(six.iterkeys(view.forms)),
                         {'my-form-1', 'my-form-2'})

    def test_get_context_data(self):
        """Testing ConfigPagesView.get_context_data"""
        request = RequestFactory().request()
        request.user = User.objects.create(username='test-user')

        view = MyConfigPagesView()
        view.request = request

        view.dispatch(view.request)

        self.assertEqual(
            view.get_context_data(),
            {
                'base_template_name': 'base.html',
                'page_title': 'My Page Title',
                'nav_title': 'My Nav Entry',
                'pages_id': 'config_pages',
                'pages': view.pages,
                'css_bundle_names': ['my-css-bundle'],
                'js_bundle_names': ['my-js-bundle'],
                'js_model_class': 'MyModel',
                'js_view_class': 'MyView',
                'js_model_data': {
                    'my-attr': 'value',
                },
                'js_view_data': {
                    'my-option': 'value',
                },
                'forms': list(six.itervalues(view.forms)),
                'render_sidebar': True,
            })

    def test_post_without_form_target(self):
        """Testing ConfigPagesView.dispatch with POST and no form_target"""
        request = RequestFactory().post('/config/')
        request.user = User.objects.create(username='test-user')
        request._dont_enforce_csrf_checks = True

        view = MyConfigPagesView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 400)

    def test_post_with_invalid_form_target(self):
        """Testing ConfigPagesView.dispatch with POST and invalid form_target
        """
        request = RequestFactory().post('/config/', {
            'form_target': 'bad',
        })
        request.user = User.objects.create(username='test-user')
        request._dont_enforce_csrf_checks = True

        view = MyConfigPagesView.as_view()

        with self.assertRaises(Http404):
            view(request)

    def test_post_with_success(self):
        """Testing ConfigPagesView.dispatch with POST and success"""
        request = RequestFactory().post('/config/', {
            'form_target': 'my-form-1',
        })
        request.user = User.objects.create(username='test-user')
        request._dont_enforce_csrf_checks = True

        view = MyConfigPagesView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/config/')
