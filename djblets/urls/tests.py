from __future__ import unicode_literals

from django.conf.urls import include, url
from django.core.urlresolvers import (NoReverseMatch, clear_url_caches,
                                      reverse)

from djblets.testing.testcases import TestCase
from djblets.urls.resolvers import DynamicURLResolver


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
