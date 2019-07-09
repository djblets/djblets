"""Template loaders for extensions."""

from __future__ import unicode_literals

import warnings

from django.template import TemplateDoesNotExist
from pkg_resources import _manager as manager
try:
    from django.template.loaders.base import Loader as BaseLoader
except ImportError:
    # Django < 1.8
    from django.template.loader import BaseLoader

from djblets.extensions.manager import get_extension_managers


class Loader(BaseLoader):
    """Loads templates found within an extension.

    This will look through all enabled extensions and attempt to fetch
    the named template under the :file:`templates` directory within the
    extension's package.

    This should be added last to the list of template loaders.

    .. versionadded:: 0.9
    """

    is_usable = manager is not None

    def load_template_source(self, template_name, template_dirs=None):
        """Load templates from enabled extensions."""
        if manager:
            resource = "templates/" + template_name

            for extmgr in get_extension_managers():
                for ext in extmgr.get_enabled_extensions():
                    package = ext.info.app_name

                    try:
                        return (manager.resource_string(package, resource),
                                'extension:%s:%s ' % (package, resource))
                    except Exception:
                        pass

        raise TemplateDoesNotExist(template_name)
