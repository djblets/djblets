"""Unit tests for djblets.privacy.templatetags.djblets_privacy."""

from __future__ import unicode_literals

from django.template import Context, Template
from django.test.client import RequestFactory

try:
    # Django >= 1.10
    from django.urls import ResolverMatch
except ImportError:
    # Django < 1.10
    from django.core.urlresolvers import ResolverMatch

from djblets.testing.testcases import TestCase


class PIISafePageURLTemplateTagTests(TestCase):
    """Unit tests for the {% pii_safe_page_url %} template tag."""

    def test_with_pii(self):
        """Testing {% pii_safe_page_url %} with PII in URL"""
        url = self._render_url('/users/test/', kwargs={
            'username': 'test',
        })

        self.assertEqual(url, '/users/&lt;REDACTED&gt;/')

    def test_without_pii(self):
        """Testing {% pii_safe_page_url %} without PII in URL"""
        self.assertEqual(self._render_url('/groups/test/'),
                         '/groups/test/')

    def _render_url(self, path, kwargs={}):
        request = RequestFactory().get(path)
        request.resolver_match = ResolverMatch(func=lambda: None,
                                               args=(),
                                               kwargs=kwargs)

        t = Template('{% load djblets_privacy %}'
                     '{% pii_safe_page_url %}')

        return t.render(Context({
            'request': request,
        }))
