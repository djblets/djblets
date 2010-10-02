import pkg_resources
from pkg_resources import _manager as manager

from django.template import TemplateDoesNotExist
from django.conf import settings

from djblets.extensions.base import get_extension_managers


def load_template_source(template_name, template_dirs=None):
    """
    Loads templates from enabled extensions.
    """
    if manager:
        resource = "templates/" + template_name

        for extmgr in get_extension_managers():
            for ext in extmgr.get_enabled_extensions():
                package = ext.info.app_name

                try:
                    return (manager.resource_string(package, resource),
                            'extension:%s:%s ' % (package, resource))
                except Exception, e:
                    pass

    raise TemplateDoesNotExist, template_name

load_template_source.is_usable = manager is not None
