from django.conf.urls.defaults import patterns, include
from django.core.exceptions import ObjectDoesNotExist
from djblets.extensions.base import RegisteredExtension
from djblets.extensions.errors import DisablingExtensionError, \
                                      EnablingExtensionError, \
                                      InvalidExtensionError
from djblets.webapi.decorators import webapi_login_required, \
                                      webapi_permission_required, \
                                      webapi_request_fields
from djblets.webapi.errors import DOES_NOT_EXIST, \
                                  ENABLE_EXTENSION_FAILED, \
                                  DISABLE_EXTENSION_FAILED
from djblets.webapi.resources import WebAPIResource


class ExtensionResource(WebAPIResource):
    """A default resource for representing an Extension model."""
    model = RegisteredExtension
    fields = ('class_name', 'name', 'enabled', 'installed')
    name = 'extension'
    plural_name = 'extensions'
    uri_object_key = 'extension_name'
    uri_object_key_regex = '[.A-Za-z0-9_-]+'
    model_object_key = 'class_name'

    allowed_methods = ('GET', 'PUT',)

    def __init__(self, extension_manager):
        super(ExtensionResource, self).__init__()
        self._extension_manager = extension_manager
        self._url_patterns = None
        self._resource_url_patterns_queue = []
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

        self._url_patterns = super(ExtensionResource, self).get_url_patterns()

        # It's possible that some extensions were initialized before
        # the extension resource URLs were fetched.  In that case, those
        # extensions had their URLs queued up.  Dequeue them and add
        # them to the URL patterns.

        for url_patterns in self._resource_url_patterns_queue:
            self._add_to_url_patterns(url_patterns)

        self._resource_url_patterns_queue = []

        return self._url_patterns

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
                (r'^%s/%s/' % (extension.id, resource.name_plural),
                 include(resource.get_url_patterns()))))

        # It's possible that the ExtensionResource doesn't have
        # a reference to self._url_patterns yet (this happens when
        # an application starts up with extensions that are already
        # enabled).  In that case, we queue those URL patterns, and
        # attach once we get a reference to self._url_patterns.
        if not self._url_patterns:
            self._resource_url_patterns_queue.append(
                self._resource_url_patterns_map[extension])
        else:
            self._add_to_url_patterns(
                self._resource_url_patterns_map[extension])

    def _add_to_url_patterns(self, url_patterns):
        self._url_patterns.extend(url_patterns)

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
        for pattern in self._resource_url_patterns_map[extension]:
            self._url_patterns.remove(pattern)

        # Delete the URL patterns so that we can regenerate
        # them when the extension is re-enabled.  This is to
        # avoid caching incorrect URL patterns during extension
        # development, when extension resources are likely to
        # change.
        del(self._resource_url_patterns_map[extension])

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
