"""Unit tests for djblets.extensions.hooks.TemplateHook."""

from django.template import Context, RequestContext, Template
from django.test.client import RequestFactory
from django.urls import ResolverMatch
from kgb import SpyAgency

from djblets.extensions.extension import Extension
from djblets.extensions.hooks import TemplateHook
from djblets.extensions.testing import ExtensionTestCaseMixin
from djblets.testing.testcases import TestCase


class MyTestExtension(Extension):
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


class TemplateHookTests(SpyAgency, ExtensionTestCaseMixin, TestCase):
    """Unit tests for djblets.extensions.hooks.TemplateHook."""

    extension_class = MyTestExtension

    def setUp(self):
        super(TemplateHookTests, self).setUp()

        request = RequestFactory().get('/')
        request._djblets_extensions_kwargs = {}  # type: ignore
        request.resolver_match = ResolverMatch(
            func=lambda *args, **kwargs: None,
            args=(),
            kwargs={},
            url_name='root')

        self.request = request

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

    def test_with_class_attrs(self) -> None:
        """Testing TemplateHook with class attributes"""
        class MyTemplateHook(TemplateHook):
            name = 'my-name'
            apply_to = ['url1', 'url2']
            template_name = 'my-template.html'
            extra_context = {
                'key': 'value',
            }

        extension = self.extension
        assert extension is not None

        hook = MyTemplateHook(extension)

        self.assertAttrsEqual(
            hook,
            {
                'apply_to': ['url1', 'url2'],
                'extra_context': {
                    'key': 'value',
                },
                'name': 'my-name',
                'template_name': 'my-template.html',
            })

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

    def test_render(self) -> None:
        """Testing TemplateHook.render"""
        extension = self.extension
        assert extension is not None

        hook = TemplateHook(
            extension,
            name='test',
            template_name='deco/box.html',
            extra_context={
                'content': 'Hello world',
            })

        request = RequestFactory().request()
        result = hook.render(
            request=request,
            context=RequestContext(request, {
                'classname': 'test',
            }))

        assert result is not None

        self.assertHTMLEqual(
            result['content'],
            '<div class="box-container">'
            ' <div class="box test">'
            '  <div class="box-inner">'
            '   Hello world'
            '  </div>'
            ' </div>'
            '</div>')

    def test_render_with_should_render_false(self) -> None:
        """Testing TemplateHook.render with should_render() returning False"""
        class MyTemplateHook(TemplateHook):
            def should_render(self, *args, **kwargs) -> bool:
                return False

        extension = self.extension
        assert extension is not None

        hook = MyTemplateHook(
            extension,
            name='test',
            template_name='deco/box.html',
            extra_context={
                'content': 'Hello world',
            })

        request = RequestFactory().request()
        result = hook.render(
            request=request,
            context=RequestContext(request, {
                'classname': 'test',
            }))

        assert result is None

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

        self.assertSpyCalled(hook.applies_to)
