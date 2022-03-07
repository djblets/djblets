"""Template loaders for extensions."""

from django.template import Origin, TemplateDoesNotExist
from django.template.loaders.base import Loader as BaseLoader
from pkg_resources import _manager as manager

from djblets.extensions.manager import get_extension_managers


class ExtensionOrigin(Origin):
    """An origin for a template in an extension.

    Version Added:
        3.0
    """

    def __init__(self, package, resource, *args, **kwargs):
        """Initialize the origin.

        Args:
            package (unicode):
                The name of the package providing the template.

            resource (unicode):
                The resource path within the package.

            *args (tuple):
                Positional arguments to pass to the parent.

            **kwargs (dict):
                Keyword arguments to pass to the parent.
        """
        self.package = package
        self.resource = resource

        super(ExtensionOrigin, self).__init__(*args, **kwargs)


class Loader(BaseLoader):
    """Loads templates found within an extension.

    This will look through all enabled extensions and attempt to fetch
    the named template under the :file:`templates` directory within the
    extension's package.

    This should be added last to the list of template loaders.

    .. versionadded:: 0.9
    """

    is_usable = manager is not None

    def get_contents(self, origin):
        """Return the contents of a template.

        Args:
            origin (ExtensionOrigin):
                The origin of the template.

        Returns:
            unicode:
            The resulting template contents.

        Raises:
            TemplateDoesNotExist:
                The template could not be found.
        """
        try:
            data = manager.resource_string(origin.package, origin.resource)
            return data.decode('utf-8')
        except Exception:
            raise TemplateDoesNotExist(origin)

    def get_template_sources(self, template_name):
        """Load templates from enabled extensions.

        Args:
            template_name (unicode):
                The name of the template to load.

        Yields:
            ExtensionOrigin:
            Each possible location for the template.
        """
        if manager:
            resource = "templates/" + template_name

            for extmgr in get_extension_managers():
                for ext in extmgr.get_enabled_extensions():
                    package = ext.info.app_name

                    yield ExtensionOrigin(
                        package=package,
                        resource=resource,
                        name='extension:%s:%s' % (package, resource),
                        template_name=template_name,
                        loader=self)
