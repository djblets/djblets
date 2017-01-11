from __future__ import unicode_literals

import re
import uuid

from django.core.urlresolvers import ResolverMatch
from django.http import HttpRequest
from django.template import Context, Template

from djblets.extensions.extension import JSExtension
from djblets.extensions.hooks import TemplateHook
from djblets.extensions.tests import (FakeEntryPoint, TestExtensionManager,
                                      TestExtensionWithRegistration)
from djblets.testing.testcases import TestCase


class TestJSExtension(JSExtension):
    model_class = 'FooNew'

    def get_model_data(self, request, **kwargs):
        return {'test': 'new'}


class TestJSExtensionDeprecated(JSExtension):
    model_class = 'FooOld'

    def get_model_data(self):
        return {'test': 'old'}


class TemplateTagTests(TestCase):
    """Tests for djblets.extensions.templatetags."""

    class TestExtension(TestExtensionWithRegistration):
        css_bundles = {
            'default': {},
            'optional': {
                'apply_to': ['foo'],
            },
        }

        js_bundles = {
            'default': {},
            'optional': {
                'apply_to': ['foo'],
            },
        }

        js_extensions = [TestJSExtension, TestJSExtensionDeprecated]

    def setUp(self):
        self.key = uuid.uuid4()

        self.manager = TestExtensionManager(
            [FakeEntryPoint(self.TestExtension)], self.key)
        self.extension = self.TestExtension(self.manager)
        self.request = HttpRequest()

    def test_template_hook_point_tag(self):
        """Testing template_hook_point template tag"""
        class DummyTemplateHook(TemplateHook):
            """A template hook where the content is specified."""

            def __init__(self, content, *args, **kwargs):
                super(DummyTemplateHook, self).__init__(*args, **kwargs)
                self._content = content

            def render_to_string(self, request, context):
                return self._content

        t = Template('{% load djblets_extensions %}'
                     '{% template_hook_point "test-hook" %}')

        DummyTemplateHook('foo\n', self.extension, 'test-hook')
        DummyTemplateHook('bar\n', self.extension, 'test-hook')

        self.assertEqual(
            t.render(Context({
                'request': self.request,
            })),
            'foo\nbar\n')

    def test_ext_static_tag(self):
        """Testing ext_static template tag"""
        t = Template('{% load djblets_extensions %}'
                     '{% ext_static ext "foo" %}')

        self.assertEqual(
            t.render(Context({
                'ext': self.extension,
                'request': self.request,
            })),
            '/ext/djblets.extensions.templatetags.tests.TestExtension/foo')

    def test_ext_css_bundle_tag(self):
        """Testing ext_css_bundle template tag"""
        t = Template('{% load djblets_extensions %}'
                     '{% ext_css_bundle ext "default" %}')

        self.manager.load()
        self.manager.enable_extension(self.extension.id)

        self.assertEqual(
            t.render(Context({
                'ext': self.extension,
                'request': self.request,
            })),
            '/ext/djblets.extensions.templatetags.tests.TestExtension/css/'
            'default.min.css\n')

    def test_ext_js_bundle_tag(self):
        """Testing ext_js_bundle template tag"""
        t = Template('{% load djblets_extensions %}'
                     '{% ext_js_bundle ext "default" %}')

        self.manager.load()
        self.manager.enable_extension(self.extension.id)

        self.assertEqual(
            t.render(Context({
                'ext': self.extension,
                'request': self.request,
            })),
            '/ext/djblets.extensions.templatetags.tests.TestExtension/js/'
            'default.min.js\n')

    def test_load_extensions_css_tag(self):
        """Testing load_extensions_css template tag"""
        t = Template('{% load djblets_extensions %}'
                     '{% load_extensions_css manager_id %}')

        self.manager.load()
        self.manager.enable_extension(self.extension.id)
        self.request.resolver_match = ResolverMatch(None, None, None, 'foo')

        self.assertEqual(
            t.render(Context({
                'ext': self.extension,
                'manager_id': self.key,
                'request': self.request,
            })),
            '/ext/djblets.extensions.templatetags.tests.TestExtension/css/'
            'default.min.css\n'
            '/ext/djblets.extensions.templatetags.tests.TestExtension/css/'
            'optional.min.css\n')

    def test_load_extensions_js_tag(self):
        """Testing load_extensions_js template tag"""
        t = Template('{% load djblets_extensions %}'
                     '{% load_extensions_js manager_id %}')

        self.manager.load()
        self.manager.enable_extension(self.extension.id)
        self.request.resolver_match = ResolverMatch(None, None, None, 'foo')

        self.assertEqual(
            t.render(Context({
                'ext': self.extension,
                'manager_id': self.key,
                'request': self.request,
            })),
            '/ext/djblets.extensions.templatetags.tests.TestExtension/js/'
            'default.min.js\n'
            '/ext/djblets.extensions.templatetags.tests.TestExtension/js/'
            'optional.min.js\n')

    def test_init_js_extensions(self):
        """Testing init_js_extensions template tag"""
        t = Template('{% load djblets_extensions %}'
                     '{% init_js_extensions manager_id %}')

        self.manager.load()
        self.manager.enable_extension(self.extension.id)
        self.request.resolver_match = ResolverMatch(None, None, None, 'foo')

        content = t.render(Context({
            'ext': self.extension,
            'manager_id': self.key,
            'request': self.request,
        }))

        self.assertIsNotNone(re.search(
            r'new FooNew\({\s+"test": "new",',
            content))

        self.assertIsNotNone(re.search(
            r'new FooOld\({\s+"test": "old",',
            content))
