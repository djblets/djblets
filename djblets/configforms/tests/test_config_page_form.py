"""Unit tests for djblets.configforms.forms.ConfigPageForm."""

from __future__ import unicode_literals

import warnings

from django import forms
from django.contrib.auth.models import User
from django.test.client import RequestFactory
from django.utils import six

from djblets.configforms.forms import ConfigPageForm
from djblets.configforms.pages import ConfigPage
from djblets.configforms.views import ConfigPagesView
from djblets.testing.testcases import TestCase


class TestForm(ConfigPageForm):
    form_id = 'my-form'
    field1 = forms.CharField(label='Field 1',
                             required=False)
    field2 = forms.CharField(label='Field 2',
                             required=False)


class TestPage(ConfigPage):
    page_id = 'my-page'
    form_classes = [TestForm]


class ConfigPageFormTests(TestCase):
    """Unit tests for djblets.configforms.forms.ConfigPageForm."""

    def setUp(self):
        super(ConfigPageFormTests, self).setUp()

        request = RequestFactory().request()
        user = User.objects.create_user(username='test-user',
                                        password='test-user')
        page = TestPage(ConfigPagesView, request, user)

        self.form = TestForm(page, request, user)

    def test_initial_state(self):
        """Testing ConfigPageForm initial state"""
        self.assertEqual(self.form.fields['form_target'].initial, 'my-form')

    def test_set_initial(self):
        """Testing ConfigPageForm.set_initial"""
        self.form.set_initial({
            'field1': 'foo',
            'field2': 'bar',
        })

        self.assertEqual(self.form.fields['field1'].initial, 'foo')
        self.assertEqual(self.form.fields['field2'].initial, 'bar')

    def test_render(self):
        """Testing ConfigPageForm.render"""
        rendered = self.form.render()

        self.assertHTMLEqual(
            '<input id="id_form_target" name="form_target"'
            ' type="hidden" value="my-form">'
            '<div class="fields-row field-field1" id="row-field1">'
            ' <div class="field">'
            '  <label for="id_field1">Field 1:</label>'
            '  <input id="id_field1" name="field1" type="text">'
            ' </div>'
            '</div>'
            '<div class="fields-row field-field2" id="row-field2">'
            ' <div class="field">'
            '  <label for="id_field2">Field 2:</label>'
            '  <input id="id_field2" name="field2" type="text">'
            ' </div>'
            '</div>'
            '<input type="submit" class="btn" value="Save">',
            rendered)
