from django.apps.registry import apps
from django.conf import settings
from django.template import Context, Template, TemplateSyntaxError, engines
from django.template.loader import get_template
from django.template.loaders.cached import Loader as CachedLoader

from djblets.template.caches import (clear_template_caches,
                                     clear_template_tag_caches)
from djblets.testing.testcases import TestCase


class CachesTests(TestCase):
    """Unit tests for djblets.template.caches."""

    def test_clear_template_tag_caches(self):
        """Testing clear_template_tag_caches"""

        def _check_state(enabled):
            if enabled:
                self.assertEqual(
                    Template(template_str).render(Context({})),
                    'Hello, world!')
            else:
                with self.assertRaisesRegex(TemplateSyntaxError,
                                            'is not a (valid|registered) tag '
                                            'library'):
                    Template(template_str).render(Context({}))

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

        apps.set_installed_apps(settings.INSTALLED_APPS)

        try:
            clear_template_tag_caches()
            _check_state(enabled=True)
        finally:
            settings.INSTALLED_APPS = old_installed_apps
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

        template_loader = engines.all()[0].engine.template_loaders[0]

        self.assertTrue(isinstance(template_loader, CachedLoader))
        self.assertNotEqual(template_loader.get_template_cache, {})

        clear_template_caches()

        self.assertEqual(template_loader.get_template_cache, {})
