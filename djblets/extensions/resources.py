from django.conf.urls import patterns, include
from django.core.exceptions import ObjectDoesNotExist

from djblets.extensions.base import RegisteredExtension
from djblets.extensions.errors import DisablingExtensionError, \
                                      EnablingExtensionError, \
                                      InvalidExtensionError
from djblets.util.urlresolvers import DynamicURLResolver
from djblets.webapi.decorators import webapi_login_required, \
                                      webapi_permission_required, \
                                      webapi_request_fields
from djblets.webapi.errors import DOES_NOT_EXIST, \
                                  ENABLE_EXTENSION_FAILED, \
                                  DISABLE_EXTENSION_FAILED
from djblets.webapi.resources import WebAPIResource


class ExtensionResource(WebAPIResource):
    """Provides information on installed extensions."""
    model = RegisteredExtension
    fields = {
        'class_name': {
            'type': str,
            'description': 'The class name for the extension.',
        },
        'name': {
            'type': str,
            'description': 'The name of the extension.',
        },
        'enabled': {
            'type': bool,
            'description': 'Whether or not the extension is enabled.',
        },
        'installed': {
            'type': bool,
            'description': 'Whether or not the extension is installed.',
        },
    }
    name = 'extension'
    plural_name = 'extensions'
    uri_object_key = 'extension_name'
    uri_object_key_regex = '[.A-Za-z0-9_-]+'
    model_object_key = 'class_name'

    allowed_methods = ('GET', 'PUT',)

    def __init__(self, extension_manager):
        super(ExtensionResource, self).__init__()
        self._extension_manager = extension_manager
        self._dynamic_patterns = DynamicURLResolver()
        self._resource_url_patterns_map = {}

        # We want ExtensionResource to notice when extensions are
        # initialized or uninitialized, so connect some methods to
        # those signals.
        from djblets.extensions.signals import extension_initialized, \
                                               extension_uninitialized
        extension_initialized.connect(self._on_extension_initialized)
        extension_uninitialized.connect(self._on_extension_uninitialized)

    @webapi_login_required
    def get_list(self, request, *args, **kwargs):
        """Returns the list of known extensions.

        Each extension in the list has been installed, but may not be
        enabled.
        """
        return WebAPIResource.get_list(self, request, *args, **kwargs)

    @webapi_login_required
    @webapi_permission_required('extensions.change_registeredextension')
    @webapi_request_fields(
        required={
            'enabled': {
                'type': bool,
                'description': 'Whether or not to make the extension active.'
            },
        },
    )
    def update(self, request, *args, **kwargs):
        """Updates the state of the extension.

        If ``enabled`` is true, then the extension will be enabled, if it is
        not already. If false, it will be disabled.
        """
        # Try to find the registered extension
        try:
            registered_extension = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        try:
            ext_class = self._extension_manager.get_installed_extension(
                registered_extension.class_name)
        except InvalidExtensionError:
            return DOES_NOT_EXIST

        if kwargs.get('enabled'):
            try:
                self._extension_manager.enable_extension(ext_class.id)
            except (EnablingExtensionError, InvalidExtensionError), e:
                return ENABLE_EXTENSION_FAILED.with_message(e.message)
        else:
            try:
                self._extension_manager.disable_extension(ext_class.id)
            except (DisablingExtensionError, InvalidExtensionError), e:
                return DISABLE_EXTENSION_FAILED.with_message(e.message)

        # Refetch extension, since the ExtensionManager may have changed
        # the model.
        registered_extension = self.get_object(request, *args, **kwargs)

        return 200, {
            self.item_result_key: registered_extension
        }

    def get_url_patterns(self):
        # We want extension resource URLs to be dynamically modifiable,
        # so we override get_url_patterns in order to capture and store
        # a reference to the url_patterns at /api/extensions/.
        url_patterns = super(ExtensionResource, self).get_url_patterns()
        url_patterns += patterns('', self._dynamic_patterns)

        return url_patterns

    def get_related_links(self, obj=None, request=None, *args, **kwargs):
        """Returns links to the resources provided by the extension.

        The result should be a dictionary of link names to a dictionary of
        information. The information should contain:

        * 'method' - The HTTP method
        * 'href' - The URL
        * 'title' - The title of the link (optional)
        * 'resource' - The WebAPIResource instance
        * 'list-resource' - True if this links to a list resource (optional)
        """
        links = {}

        if obj and obj.enabled:
            extension = obj.get_extension_class()

            if not extension:
                return links

            for resource in extension.resources:
                links[resource.name_plural] = {
                    'method': 'GET',
                    'href': "%s%s/" % (
                        self.get_href(obj, request, *args, **kwargs),
                        resource.uri_name),
                    'resource': resource,
                    'list-resource': not resource.singleton,
                }

        return links

    def _attach_extension_resources(self, extension):
        """
        Attaches an extensions resources to
        /api/extensions/{extension.id}/.
        """

        # Bail out if there are no resources to attach
        if not extension.resources:
            return

        if extension in self._resource_url_patterns_map:
            # This extension already had its urlpatterns
            # mapped and attached.  Nothing to do here.
            return

        # We're going to store references to the URL patterns
        # that are generated for this extension's resources.
        self._resource_url_patterns_map[extension] = []

        # For each resource, generate the URLs
        for resource in extension.resources:
            self._resource_url_patterns_map[extension].extend(patterns('',
                (r'^%s/%s/' % (extension.id, resource.uri_name),
                 include(resource.get_url_patterns()))))

        self._dynamic_patterns.add_patterns(
            self._resource_url_patterns_map[extension])

    def _unattach_extension_resources(self, extension):
        """
        Unattaches an extensions resources from
        /api/extensions/{extension.id}/.
        """

        # Bail out if there are no resources for this extension
        if not extension.resources:
            return

        # If this extension has never had its resource URLs
        # generated, then we don't have anything to worry
        # about.
        if not extension in self._resource_url_patterns_map:
            return

        # Remove the URL patterns
        self._dynamic_patterns.remove_patterns(
            self._resource_url_patterns_map[extension])

        # Delete the URL patterns so that we can regenerate
        # them when the extension is re-enabled.  This is to
        # avoid caching incorrect URL patterns during extension
        # development, when extension resources are likely to
        # change.
        del self._resource_url_patterns_map[extension]

    def _on_extension_initialized(self, sender, ext_class=None, **kwargs):
        """
        Signal handler that notices when an extension has
        been initialized.
        """
        self._attach_extension_resources(ext_class)

    def _on_extension_uninitialized(self, sender, ext_class=None, **kwargs):
        """
        Signal handler that notices and reacts when an extension
        has been uninitialized.
        """
        self._unattach_extension_resources(ext_class)
