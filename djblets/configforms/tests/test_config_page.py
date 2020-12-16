"""Unit tests for djblets.configforms.pages.ConfigPage."""

from __future__ import unicode_literals

import re

from django.contrib.auth.models import User
from django.test.client import RequestFactory

from djblets.configforms.forms import ConfigPageForm
from djblets.configforms.pages import ConfigPage
from djblets.configforms.views import ConfigPagesView
from djblets.testing.testcases import TestCase


class TestForm1(ConfigPageForm):
    form_id = 'my-form-1'
    form_title = 'Form 1'


class TestForm2(ConfigPageForm):
    form_id = 'my-form-2'
    form_title = 'Form 2'


class TestForm3(ConfigPageForm):
    form_id = 'my-form-3'
    form_title = 'Form 3'

    def is_visible(self):
        return False


class TestPage(ConfigPage):
    page_id = 'my-page'
    form_classes = [TestForm1, TestForm2, TestForm3]


class ConfigPageTests(TestCase):
    """Unit tests for djblets.configforms.pages.ConfigPage."""

    def setUp(self):
        super(ConfigPageTests, self).setUp()

        self.request = RequestFactory().request()
        self.user = User.objects.create_user(username='test-user',
                                             password='test-user')
        self.page = TestPage(ConfigPagesView, self.request, self.user)

    def test_initial_state(self):
        """Testing ConfigPage initial state"""
        self.assertEqual(len(self.page.forms), 2)
        self.assertIsInstance(self.page.forms[0], TestForm1)
        self.assertIsInstance(self.page.forms[1], TestForm2)

    def test_is_visible_with_visible_forms(self):
        """Testing ConfigPage.is_visible with visible forms"""
        self.assertTrue(self.page.is_visible())

    def test_is_visible_with_no_visible_forms(self):
        """Testing ConfigPage.is_visible without visible forms"""
        class TestPage(ConfigPage):
            page_id = 'my-page'
            form_classes = [TestForm3]

        page = TestPage(ConfigPagesView, self.request, self.user)
        self.assertFalse(page.is_visible())

    def test_render(self):
        """Testing ConfigPage.render"""
        # Filter out the CSRF token, since it's hard to match.
        rendered = re.sub(r"<input.+name='csrfmiddlewaretoken'.*>",
                          '',
                          self.page.render())

        self.assertHTMLEqual(
            rendered,
            '<div class="box-container">'
            ' <div class="box">'
            '  <div class="box-inner">'
            '   <div class="box-head">'
            '    <h1 class="box-title">Form 1</h1>'
            '   </div>'
            '   <div class="box-main box-foot">'
            '    <form method="post" action=".#my-page" id="form_my-form-1">'
            '     <div class="djblets-l-config-forms-container">'
            '      <input id="id_form_target" name="form_target"'
            '             type="hidden" value="my-form-1">'
            '      <input type="submit" class="btn" value="Save">'
            '     </div>'
            '    </form>'
            '   </div>'
            '  </div>'
            ' </div>'
            '</div>'
            '<div class="box-container">'
            ' <div class="box">'
            '  <div class="box-inner">'
            '   <div class="box-head">'
            '    <h1 class="box-title">Form 2</h1>'
            '   </div>'
            '   <div class="box-main box-foot">'
            '    <form method="post" action=".#my-page" id="form_my-form-2">'
            '     <div class="djblets-l-config-forms-container">'
            '      <input id="id_form_target" name="form_target"'
            '             type="hidden" value="my-form-2">'
            '      <input type="submit" class="btn" value="Save">'
            '     </div>'
            '    </form>'
            '   </div>'
            '  </div>'
            ' </div>'
            '</div>')
