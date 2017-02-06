from __future__ import unicode_literals

from django.conf import settings
from django.template import Context, Template, TemplateSyntaxError
from django.template.loader import get_template
from django.template.loaders.cached import Loader as CachedLoader

try:
    # Django >= 1.7
    from django.apps.registry import apps
except ImportError:
    # Django == 1.6
    apps = None

try:
    # Django >= 1.6, <= 1.8
    from django.template.base import get_templatetags_modules
except ImportError:
    # Django >= 1.9
    get_templatetags_modules = None

try:
    # Django >= 1.8
    from django.template import engines
except ImportError:
    # Django >= 1.7, <= 1.8
    engines = None

from djblets.template.caches import (clear_template_caches,
                                     clear_template_tag_caches)
from djblets.testing.testcases import TestCase


class CachesTests(TestCase):
    """Unit tests for djblets.template.caches."""

    def test_clear_template_tag_caches(self):
        """Testing clear_template_tag_caches"""

        def _check_state(enabled):
            if enabled:
                if get_templatetags_modules is not None:
                    self.assertIn(templatetags_module_name,
                                  get_templatetags_modules())

                self.assertEqual(
                    Template(template_str).render(Context({})),
                    'Hello, world!')
            else:
                if get_templatetags_modules is not None:
                    self.assertNotIn(templatetags_module_name,
                                     get_templatetags_modules())

                with self.assertRaisesRegexp(TemplateSyntaxError,
                                             'is not a (valid|registered) tag '
                                             'library'):
                    Template(template_str).render(Context({}))

        templatetags_module_name = 'djblets.template.tests.templatetags'
        template_str = (
            '{% load template_tests %}'
            '{% my_test_template_tag %}'
        )

        # Sanity-check that the template tag module isn't registered.
        _check_state(enabled=False)

        # Enable a new template tag library.
        old_installed_apps = settings.INSTALLED_APPS

        settings.INSTALLED_APPS = list(old_installed_apps) + [
            'djblets.template.tests',
        ]

        if apps:
            apps.set_installed_apps(settings.INSTALLED_APPS)

        try:
            clear_template_tag_caches()
            _check_state(enabled=True)
        finally:
            settings.INSTALLED_APPS = old_installed_apps

            if apps:
                apps.unset_installed_apps()

        clear_template_tag_caches()
        _check_state(enabled=False)

        # Other libraries should still work.
        Template('{% load djblets_js djblets_extensions %}').render(
            Context({}))

    def test_clear_template_caches(self):
        """Testing clear_template_caches"""
        # Load a template to populate the cache.
        get_template('avatars/avatar.html')

        if engines is not None:
            # Django >= 1.8
            template_loader = engines.all()[0].engine.template_loaders[0]
        else:
            # Django >= 1.6, <= 1.7
            #
            # We need to import this here in order to get the latest copy
            # of this variable.
            from django.template.loader import template_source_loaders

            template_loader = template_source_loaders[0]

        self.assertTrue(isinstance(template_loader, CachedLoader))

        if hasattr(template_loader, 'get_template'):
            self.assertNotEqual(template_loader.get_template_cache, {})
        else:
            self.assertNotEqual(template_loader.template_cache, {})

        clear_template_caches()

        if hasattr(template_loader, 'get_template'):
            self.assertEqual(template_loader.get_template_cache, {})
        else:
            self.assertEqual(template_loader.template_cache, {})
