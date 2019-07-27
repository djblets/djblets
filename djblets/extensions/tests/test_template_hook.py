"""Unit tests for djblets.extensions.hooks.TemplateHook."""

from __future__ import unicode_literals

from django.template import Context, RequestContext, Template
from django.test.client import RequestFactory
from kgb import SpyAgency
from mock import Mock

from djblets.extensions.extension import Extension
from djblets.extensions.hooks import TemplateHook
from djblets.extensions.tests.base import ExtensionTestsMixin
from djblets.testing.testcases import TestCase


class TestExtension(Extension):
    def initialize(self):
        self.hook_no_applies_name = 'template-hook-no-applies-name'
        self.template_hook_no_applies = TemplateHook(
            self,
            self.hook_no_applies_name,
            'test_module/some_template.html',
            [])

        self.hook_with_applies_name = 'template-hook-with-applies-name'
        self.template_hook_with_applies = TemplateHook(
            self,
            self.hook_with_applies_name,
            'test_module/some_template.html',
            [
                'test-url-name',
                'url_2',
                'url_3',
            ]
        )


class TemplateHookTests(SpyAgency, ExtensionTestsMixin, TestCase):
    """Unit tests for djblets.extensions.hooks.TemplateHook."""

    def setUp(self):
        super(TemplateHookTests, self).setUp()

        self.extension = self.setup_extension(TestExtension)

        self.request = Mock()
        self.request._djblets_extensions_kwargs = {}
        self.request.path_info = '/'
        self.request.resolver_match = Mock()
        self.request.resolver_match.url_name = 'root'

    def test_hook_added_to_class_by_name(self):
        """Testing TemplateHook registration"""
        self.assertIn(
            self.extension.template_hook_with_applies,
            TemplateHook._by_name[self.extension.hook_with_applies_name])

        # The TemplateHook should also be added to the Extension's collection
        # of hooks.
        self.assertIn(self.extension.template_hook_with_applies,
                      self.extension.hooks)

    def test_hook_shutdown(self):
        """Testing TemplateHook shutdown"""
        self.extension.template_hook_with_applies.disable_hook()
        self.assertNotIn(
            self.extension.template_hook_with_applies,
            TemplateHook._by_name[self.extension.hook_with_applies_name])

        # The TemplateHook should still be in the Extension's collection
        # of hooks.
        self.assertIn(self.extension.template_hook_with_applies,
                      self.extension.hooks)

    def test_applies_to_default(self):
        """Testing TemplateHook.applies_to defaults to everything"""
        self.assertTrue(
            self.extension.template_hook_no_applies.applies_to(self.request))
        self.assertTrue(
            self.extension.template_hook_no_applies.applies_to(None))

    def test_applies_to(self):
        """Testing TemplateHook.applies_to customization"""
        self.assertFalse(
            self.extension.template_hook_with_applies.applies_to(self.request))

        self.request.resolver_match.url_name = 'test-url-name'
        self.assertTrue(
            self.extension.template_hook_with_applies.applies_to(self.request))

    def test_render_to_string(self):
        """Testing TemplateHook.render_to_string"""
        hook = TemplateHook(
            self.extension,
            name='test',
            template_name='deco/box.html',
            extra_context={
                'content': 'Hello world',
            })

        request = RequestFactory().request()
        result = hook.render_to_string(request, RequestContext(request, {
            'classname': 'test',
        }))

        self.assertHTMLEqual(
            result,
            '<div class="box-container">'
            ' <div class="box test">'
            '  <div class="box-inner">'
            '   Hello world'
            '  </div>'
            ' </div>'
            '</div>')

    def test_context_doesnt_leak(self):
        """Testing TemplateHook's context won't leak state"""
        class MyTemplateHook(TemplateHook):
            def render_to_string(self, request, context):
                context['leaky'] = True

                return ''

        MyTemplateHook(self.extension, 'test')
        context = Context({})
        context['request'] = None

        t = Template(
            '{% load djblets_extensions %}'
            '{% template_hook_point "test" %}')
        t.render(context).strip()

        self.assertNotIn('leaky', context)

    def test_render_to_string_sandbox(self):
        """Testing TemplateHook sandboxing"""
        class MyTemplateHook(TemplateHook):
            def render_to_string(self, request, context):
                raise Exception('Oh noes')

        MyTemplateHook(self.extension, 'test')
        context = Context({})
        context['request'] = None

        t = Template(
            '{% load djblets_extensions %}'
            '{% template_hook_point "test" %}')
        t.render(context).strip()

        # Didn't crash. We're good.

    def test_applies_to_sandbox(self):
        """Testing TemplateHook for applies_to"""
        class MyTemplateHook(TemplateHook):
            def applies_to(self, request):
                raise Exception

        hook = MyTemplateHook(extension=self.extension, name='test')
        context = Context({})
        context['request'] = self.request

        self.spy_on(hook.applies_to)

        t = Template(
            '{% load djblets_extensions %}'
            '{% template_hook_point "test" %}')
        string = t.render(context).strip()

        self.assertEqual(string, '')

        self.assertTrue(hook.applies_to.called)
