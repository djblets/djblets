from __future__ import unicode_literals

from django.template import TemplateDoesNotExist
from django.template.loader import BaseLoader


class MemoryTemplateLoader(BaseLoader):
    """An in-memory template loader."""

    is_usable = True

    def __init__(self, templates=None):
        """Initialize the loader.

        Args:
            templates (dict, optional):
                A mapping of template names (:py:class`unicode`) to template
                sources (:py:class:`unicode`).
        """
        super(MemoryTemplateLoader, self).__init__()
        self.templates = templates or {}

    def load_template_source(self, template_name, template_dirs=None):
        """Load the source of the given template

        Args:
            template_name (unicode):
                The name of the template to load.

            template_dirs (list, optional):
                Unused. This is required for compatibility.

        Returns:
            tuple:
            A 2-tuple of the template source (as :py:class:`unicode`) and its
            origin, which will always be the value ``u':memory:'``.

        Raises:
            django.template.base.TemplateDoesNotExist:
                This exception is raised when the template cannot be found.

        """
        try:
            return self.templates[template_name], ':memory:'
        except KeyError:
            raise TemplateDoesNotExist(template_name)
