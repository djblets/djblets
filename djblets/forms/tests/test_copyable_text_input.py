"""Unit tests for djblets.forms.widgets.CopyableTextInput."""

from __future__ import unicode_literals

from django import forms

from djblets.forms.widgets import CopyableTextInput
from djblets.testing.testcases import TestCase


class CopyableTextInputTests(TestCase):
    """Unit tests for djblets.forms.widgets.CopyableTextInput."""

    def test_render(self):
        """Testing CopyableTextInput.render"""
        field = forms.CharField(widget=CopyableTextInput())
        rendered = field.widget.render(
            name='my_field',
            value='test',
            attrs={
                'id': 'id_my_field',
            })

        self.assertIn('class="copyable-text-input-link"', rendered)
        self.assertIn('data-field-id="id_my_field"', rendered)
        self.assertIn('title="Copy to clipboard"', rendered)
