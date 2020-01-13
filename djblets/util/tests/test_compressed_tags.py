"""Unit tests for djblets.util.templatetags.djblets_forms."""

from __future__ import unicode_literals

import os

from django.conf import settings
from django.template import Context, Template
from pipeline.conf import settings as pipeline_settings

from djblets.testing.testcases import TestCase


class CompressedTagsTests(TestCase):
    """Unit tests for the {% compressed_* %} template tags."""

    def test_compressed_css_tag(self):
        """Testing {% compressed_css %}"""
        self._touch_files(['test.css', 'test.d41d8cd98f00.css'])

        pipeline_settings.STYLESHEETS = {
            'test': {
                'source_filenames': [],
                'output_filename': 'test.css',
            }
        }

        t = Template('{% load compressed %}'
                     '{% compressed_css "test" %}')

        self.assertHTMLEqual(
            t.render(Context({'test': 'test'})),
            '<link href="/test.d41d8cd98f00.css" rel="stylesheet"'
            ' type="text/css" />')

    def test_compressed_js_tag(self):
        """Testing {% compressed_js %}"""
        self._touch_files(['test.js', 'test.d41d8cd98f00.js'])

        pipeline_settings.JAVASCRIPT = {
            'test': {
                'source_filenames': [],
                'output_filename': 'test.js',
            }
        }

        t = Template('{% load compressed %}'
                     '{% compressed_js "test" %}')

        self.assertHTMLEqual(
            t.render(Context({'test': 'test'})),
            '<script type="text/javascript" src="/test.d41d8cd98f00.js"'
            ' charset="utf-8"></script>')

    def _touch_files(self, filenames):
        """Create one or more empty static media files.

        Args:
            filenames (list of unicode):
                The list of static media files to create.
        """
        for filename in filenames:
            with open(os.path.join(settings.STATIC_ROOT, filename), 'w'):
                pass
