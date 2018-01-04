from __future__ import unicode_literals

import warnings

import django
from django.conf.urls import include, url
from django.core.urlresolvers import (NoReverseMatch, clear_url_caches,
                                      reverse)
from django.utils import six
from django.views.decorators.cache import never_cache
from kgb import SpyAgency

from djblets.testing.testcases import TestCase
from djblets.urls.patterns import never_cache_patterns
from djblets.urls.resolvers import DynamicURLResolver


def dummy_view(request):
    pass


class URLPatternsTests(SpyAgency, TestCase):
    """Unit tests for djblets.urls.patterns."""

    def test_never_cache_patterns_with_prefix(self):
        """Testing never_cache_patterns with view lookup string prefix"""
        msg = (
            'String prefixes for URLs in never_cache_patterns() is '
            'deprecated, and will not work on Django 1.10 or higher.'
        )

        if django.VERSION[:2] >= (1, 10):
            with self.assertRaisesMessage(ValueError, msg):
                never_cache_patterns(
                    'djblets.urls.tests',

                    url('^a/$', dummy_view),
                )
        else:
            self.spy_on(never_cache)

            with warnings.catch_warnings(record=True) as w:
                urlpatterns = never_cache_patterns(
                    'djblets.urls.tests',

                    url('^a/$', 'dummy_view'),
                    url('^b/$', 'dummy_view'),
                )

            self.assertEqual(six.text_type(w[-1].message), msg)
            self.assertEqual(len(never_cache.spy.calls), 2)
            self.assertEqual(len(urlpatterns), 2)

            pattern = urlpatterns[0]
            self.assertEqual(pattern._callback_str,
                             'djblets.urls.tests.dummy_view')
            self.assertTrue(
                never_cache.spy.calls[0].returned(pattern.callback))

            pattern = urlpatterns[1]
            self.assertEqual(pattern._callback_str,
                             'djblets.urls.tests.dummy_view')
            self.assertTrue(
                never_cache.spy.calls[1].returned(pattern.callback))

    def test_never_cache_patterns_without_prefix(self):
        """Testing never_cache_patterns without view lookup string prefix"""
        self.spy_on(never_cache)

        with warnings.catch_warnings(record=True) as w:
            urlpatterns = never_cache_patterns(
                url('^a/$', dummy_view),
                url('^b/$', dummy_view),
            )

        self.assertEqual(len(w), 0)
        self.assertEqual(len(never_cache.spy.calls), 2)
        self.assertEqual(len(urlpatterns), 2)

        self.assertTrue(
            never_cache.spy.calls[0].returned(urlpatterns[0].callback))
        self.assertTrue(
            never_cache.spy.calls[1].returned(urlpatterns[1].callback))


class URLResolverTests(TestCase):
    def tearDown(self):
        super(URLResolverTests, self).tearDown()
        clear_url_caches()

    def test_dynamic_url_resolver(self):
        """Testing DynamicURLResolver"""
        def dummy_view(self):
            pass

        dynamic_urls = DynamicURLResolver()
        root_urlconf = [
            url(r'^root/', include([dynamic_urls])),
            url(r'^foo/', dummy_view, name='foo'),
        ]

        with self.settings(ROOT_URLCONF=root_urlconf):
            clear_url_caches()

            new_patterns = [
                url(r'^bar/$', dummy_view, name='bar'),
                url(r'^baz/$', dummy_view, name='baz'),
            ]

            # The new patterns shouldn't reverse, just the original "foo".
            reverse('foo')
            self.assertRaises(NoReverseMatch, reverse, 'bar')
            self.assertRaises(NoReverseMatch, reverse, 'baz')

            # Add the new patterns. Now reversing should work.
            dynamic_urls.add_patterns(new_patterns)

            reverse('foo')
            reverse('bar')
            reverse('baz')

            # Get rid of the patterns again. We should be back in the original
            # state.
            dynamic_urls.remove_patterns(new_patterns)

            reverse('foo')
            self.assertRaises(NoReverseMatch, reverse, 'bar')
            self.assertRaises(NoReverseMatch, reverse, 'baz')
