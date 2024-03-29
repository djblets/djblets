import os
from importlib import import_module

from django.core.exceptions import SuspiciousFileOperation
from django.template import Origin, TemplateDoesNotExist
from django.template.loaders.app_directories import Loader as AppDirsLoader
from django.utils._os import safe_join


class Loader(AppDirsLoader):
    """Looks for templates in app directories, optionally with a namespace.

    This extends the standard Django 'app_directories' template loader by
    allowing a prefix specifying the app whose template should be used.
    It solves the problem of one app defining a template and another app
    trying to both override and extend it, resulting in an infinite loop.

    Templates can be in the standard form of 'path/to/template', or in the
    namespaced form of 'app.path:path/to/template'.
    """
    def __init__(self, *args, **kwargs):
        super(Loader, self).__init__(*args, **kwargs)

        self._cache = {}

    def get_template_sources(self, template_name):
        parts = template_name.split(':')

        if len(parts) == 2:
            app = parts[0]

            template_dir = self._cache.get(app)

            if not template_dir:
                try:
                    mod = import_module(app)
                except ImportError:
                    raise TemplateDoesNotExist(template_name)

                template_dir = os.path.join(os.path.dirname(mod.__file__),
                                            'templates')
                self._cache[app] = template_dir

            template_name = parts[1]
            template_dirs = [template_dir]
        else:
            template_dirs = self.get_dirs()

        for template_dir in template_dirs:
            try:
                name = safe_join(template_dir, template_name)
            except SuspiciousFileOperation:
                continue

            yield Origin(
                name=name,
                template_name=template_name,
                loader=self)
