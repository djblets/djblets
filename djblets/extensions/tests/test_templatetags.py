"""Tests for djblets.extensions.templatetags."""

import os
import re
from collections import OrderedDict

from django.http import HttpRequest
from django.template import Context, Template
from django.urls import ResolverMatch
from django.utils.safestring import mark_safe
from kgb import SpyAgency

from djblets.extensions.extension import Extension, ExtensionInfo, JSExtension
from djblets.extensions.hooks import TemplateHook
from djblets.extensions.manager import ExtensionManager
from djblets.extensions.testing import ExtensionTestCaseMixin
from djblets.testing.testcases import TestCase
from pipeline.conf import settings as pipeline_settings


class MyTestJSExtension1(JSExtension):
    model_class = 'TestExtension1'

    def get_model_data(self, request, **kwargs):
        return {'test': 'new'}


class MyTestJSExtension2(JSExtension):
    model_class = 'TestExtension2'

    def get_model_data(self, **kwargs):
        return {'test': 'old'}


class MyTestExtensionManager(ExtensionManager):
    should_install_static_media = True


class MyTestExtension(Extension):
    # While normally these would be plain dictionaries, we want to ensure
    # order for testing, so we'll be doing this a bit differently.
    css_bundles = OrderedDict()
    css_bundles['default'] = {
        'source_filenames': (
            'css/default-test.css',
        ),
    }
    css_bundles['included'] = {
        'source_filenames': (
            'css/included-test.css',
        ),
    }
    css_bundles['optional'] = {
        'source_filenames': (
            'css/optional-test.css',
        ),
        'apply_to': ['foo'],
        'include_bundles': ['included'],
    }

    js_bundles = OrderedDict()
    js_bundles['default'] = {
        'source_filenames': (
            'js/default-test.js',
        ),
    }
    js_bundles['included'] = {
        'source_filenames': (
            'js/included-test.js',
        ),
    }
    js_bundles['optional'] = {
        'source_filenames': (
            'js/optional-test.js',
        ),
        'apply_to': ['foo'],
        'include_bundles': ['included'],
    }

    js_extensions = [MyTestJSExtension1, MyTestJSExtension2]


class TemplateTagTests(SpyAgency, ExtensionTestCaseMixin, TestCase):
    """Tests for djblets.extensions.templatetags."""

    default_extension_manager_cls = MyTestExtensionManager

    maxDiff = None

    def setUp(self):
        def _has_resource(self, path):
            return path == 'static'

        def _extract_resource(self, path):
            if path == 'static':
                return os.path.abspath(os.path.join(__file__, '..', 'static'))

            return None

        super(TemplateTagTests, self).setUp()

        self.spy_on(ExtensionInfo.has_resource,
                    owner=ExtensionInfo,
                    call_fake=_has_resource)
        self.spy_on(ExtensionInfo.extract_resource,
                    owner=ExtensionInfo,
                    call_fake=_extract_resource)

        self.extension = self.setup_extension(MyTestExtension)
        self.request = HttpRequest()

        self._old_pipeline_enabled = pipeline_settings.PIPELINE_ENABLED

    def tearDown(self):
        super(TemplateTagTests, self).tearDown()

        pipeline_settings.PIPELINE_ENABLED = self._old_pipeline_enabled

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

        DummyTemplateHook(content=mark_safe('<strong>foo</strong>\n'),
                          extension=self.extension,
                          name='test-hook')
        DummyTemplateHook(content='<bar>\n',
                          extension=self.extension,
                          name='test-hook')

        self.assertEqual(
            t.render(Context({
                'request': self.request,
            })),
            '<strong>foo</strong>\n'
            '&lt;bar&gt;\n')

    def test_ext_static_tag(self):
        """Testing ext_static template tag"""
        t = Template('{% load djblets_extensions %}'
                     '{% ext_static ext "css/default-test.css" %}')

        self.assertEqual(
            t.render(Context({
                'ext': self.extension,
                'request': self.request,
            })),
            '/ext/djblets.extensions.tests.test_templatetags.MyTestExtension/'
            'css/default-test.dad0c9b31e59.css')

    def test_ext_css_bundle_tag_with_pipeline_enabled(self):
        """Testing ext_css_bundle template tag with PIPELINE_ENABLED=True"""
        pipeline_settings.PIPELINE_ENABLED = True

        t = Template('{% load djblets_extensions %}'
                     '{% ext_css_bundle ext "default" %}')

        self.assertHTMLEqual(
            t.render(Context({
                'ext': self.extension,
                'request': self.request,
            })),
            '<link href="/ext/djblets.extensions.tests.test_templatetags'
            '.MyTestExtension/css/default.min.dad0c9b31e59.css" '
            'media="all" rel="stylesheet" type="text/css" />')

    def test_ext_css_bundle_tag_with_pipeline_disabled(self):
        """Testing ext_css_bundle template tag with PIPELINE_ENABLED=False"""
        pipeline_settings.PIPELINE_ENABLED = False

        t = Template('{% load djblets_extensions %}'
                     '{% ext_css_bundle ext "default" %}')

        self.assertHTMLEqual(
            t.render(Context({
                'ext': self.extension,
                'request': self.request,
            })),
            '<link href="/ext/djblets.extensions.tests.test_templatetags.'
            'MyTestExtension/css/default-test.dad0c9b31e59.css" '
            'media="all" rel="stylesheet" type="text/css">')

    def test_ext_js_bundle_tag_with_pipeline_enabled(self):
        """Testing ext_js_bundle template tag with PIPELINE_ENABLED=True"""
        pipeline_settings.PIPELINE_ENABLED = True

        t = Template('{% load djblets_extensions %}'
                     '{% ext_js_bundle ext "default" %}')

        self.assertHTMLEqual(
            t.render(Context({
                'ext': self.extension,
                'request': self.request,
            })),
            '<script type="text/javascript" '
            'src="/ext/djblets.extensions.tests.test_templatetag'
            's.MyTestExtension/js/default.min.dad0c9b31e59.js" '
            'charset="utf-8"></script>')

    def test_ext_js_bundle_tag_with_pipeline_disabled(self):
        """Testing ext_js_bundle template tag with PIPELINE_ENABLED=False"""
        pipeline_settings.PIPELINE_ENABLED = False

        t = Template('{% load djblets_extensions %}'
                     '{% ext_js_bundle ext "default" %}')

        self.assertHTMLEqual(
            t.render(Context({
                'ext': self.extension,
                'request': self.request,
            })),
            '<script type="text/javascript" '
            'src="/ext/djblets.extensions.tests.test_templatetag'
            's.MyTestExtension/js/default-test.dad0c9b31e59.js" '
            'charset="utf-8"></script>')

    def test_load_extensions_css_tag_with_pipline_enabled(self):
        """Testing load_extensions_css template tag with PIPELINE_ENABLED=True
        """
        pipeline_settings.PIPELINE_ENABLED = True

        t = Template('{% load djblets_extensions %}'
                     '{% load_extensions_css manager_id %}')

        self.request.resolver_match = ResolverMatch(None, None, None, 'foo')

        self.assertHTMLEqual(
            t.render(Context({
                'ext': self.extension,
                'manager_id': self.extension_mgr.key,
                'request': self.request,
            })),
            '<link href="/ext/djblets.extensions.tests.test_templatetags'
            '.MyTestExtension/css/default.min.dad0c9b31e59.css" '
            'rel="stylesheet" media="all" type="text/css">'
            '<link href="/ext/djblets.extensions.tests.test_templatetags'
            '.MyTestExtension/css/included.min.dad0c9b31e59.css" '
            'rel="stylesheet" media="all" type="text/css">'
            '<link href="/ext/djblets.extensions.tests.test_templatetags'
            '.MyTestExtension/css/optional.min.dad0c9b31e59.css" '
            'rel="stylesheet" media="all" type="text/css">')

    def test_load_extensions_css_tag_with_pipline_disabled(self):
        """Testing load_extensions_css template tag with PIPELINE_ENABLED=False
        """
        pipeline_settings.PIPELINE_ENABLED = False

        t = Template('{% load djblets_extensions %}'
                     '{% load_extensions_css manager_id %}')

        self.request.resolver_match = ResolverMatch(None, None, None, 'foo')

        self.assertHTMLEqual(
            t.render(Context({
                'ext': self.extension,
                'manager_id': self.extension_mgr.key,
                'request': self.request,
            })),
            '<link href="/ext/djblets.extensions.tests.test_templatetags'
            '.MyTestExtension/css/default-test.dad0c9b31e59.css" '
            'rel="stylesheet" media="all" type="text/css">'
            '<link href="/ext/djblets.extensions.tests.test_templatetags'
            '.MyTestExtension/css/included-test.dad0c9b31e59.css" '
            'rel="stylesheet" media="all" type="text/css">'
            '<link href="/ext/djblets.extensions.tests.test_templatetags'
            '.MyTestExtension/css/optional-test.dad0c9b31e59.css" '
            'rel="stylesheet" media="all" type="text/css">')

    def test_load_extensions_js_tag_with_pipeline_enabled(self):
        """Testing load_extensions_js template tag with PIPELINE_ENABLED=True
        """
        pipeline_settings.PIPELINE_ENABLED = True

        t = Template('{% load djblets_extensions %}'
                     '{% load_extensions_js manager_id %}')

        self.request.resolver_match = ResolverMatch(None, None, None, 'foo')

        self.assertHTMLEqual(
            t.render(Context({
                'ext': self.extension,
                'manager_id': self.extension_mgr.key,
                'request': self.request,
            })),
            '<script type="text/javascript" '
            'src="/ext/djblets.extensions.tests.test_templatetags'
            '.MyTestExtension/js/default.min.dad0c9b31e59.js" '
            'charset="utf-8"></script>'
            '<script type="text/javascript" '
            'src="/ext/djblets.extensions.tests.test_templatetags'
            '.MyTestExtension/js/included.min.dad0c9b31e59.js" '
            'charset="utf-8"></script>'
            '<script type="text/javascript" '
            'src="/ext/djblets.extensions.tests.test_templatetags'
            '.MyTestExtension/js/optional.min.dad0c9b31e59.js" '
            'charset="utf-8"></script>')

    def test_load_extensions_js_tag_with_pipeline_disabled(self):
        """Testing load_extensions_js template tag with PIPELINE_ENABLED=False
        """
        pipeline_settings.PIPELINE_ENABLED = False

        t = Template('{% load djblets_extensions %}'
                     '{% load_extensions_js manager_id %}')

        self.request.resolver_match = ResolverMatch(None, None, None, 'foo')

        self.assertHTMLEqual(
            t.render(Context({
                'ext': self.extension,
                'manager_id': self.extension_mgr.key,
                'request': self.request,
            })),
            '<script type="text/javascript" '
            'src="/ext/djblets.extensions.tests.test_templatetags'
            '.MyTestExtension/js/default-test.dad0c9b31e59.js" '
            'charset="utf-8"></script>'
            '<script type="text/javascript" '
            'src="/ext/djblets.extensions.tests.test_templatetags'
            '.MyTestExtension/js/included-test.dad0c9b31e59.js" '
            'charset="utf-8"></script>'
            '<script type="text/javascript" '
            'src="/ext/djblets.extensions.tests.test_templatetags'
            '.MyTestExtension/js/optional-test.dad0c9b31e59.js" '
            'charset="utf-8"></script>')

    def test_init_js_extensions(self):
        """Testing init_js_extensions template tag"""
        t = Template('{% load djblets_extensions %}'
                     '{% init_js_extensions manager_id %}')

        self.request.resolver_match = ResolverMatch(None, None, None, 'foo')

        content = t.render(Context({
            'ext': self.extension,
            'manager_id': self.extension_mgr.key,
            'request': self.request,
        }))

        self.assertIsNotNone(re.search(
            r'new TestExtension1\({\s+"test": "new",',
            content))

        self.assertIsNotNone(re.search(
            r'new TestExtension2\({\s+"test": "old",',
            content))
