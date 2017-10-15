"""Unit tests for djblets.util.templatetags.djblets_forms."""

from __future__ import unicode_literals

from django.template import Context, Template
from pipeline.conf import settings as pipeline_settings

from djblets.testing.testcases import TestCase


class CompressedTagsTests(TestCase):
    """Unit tests for the {% compressed_* %} template tags."""

    def test_compressed_css_tag(self):
        """Testing {% compressed_css %}"""
        pipeline_settings.STYLESHEETS = {
            'test': {
                'source_filenames': [],
                'output_filename': 'test.css',
            }
        }

        t = Template('{% load compressed %}'
                     '{% compressed_css "test" %}')

        self.assertEqual(t.render(Context({'test': 'test'})),
                         '/test.css\n')

    def test_compressed_js_tag(self):
        """Testing {% compressed_js %}"""
        pipeline_settings.JAVASCRIPT = {
            'test': {
                'source_filenames': [],
                'output_filename': 'test.js',
            }
        }

        t = Template('{% load compressed %}'
                     '{% compressed_js "test" %}')

        self.assertEqual(t.render(Context({'test': 'test'})),
                         '/test.js\n')
