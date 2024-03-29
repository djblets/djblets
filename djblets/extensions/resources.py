from django.core.exceptions import ObjectDoesNotExist
from django.urls import include, path, reverse
from django.utils.translation import gettext as _

from djblets.extensions.errors import (DisablingExtensionError,
                                       EnablingExtensionError,
                                       InvalidExtensionError)
from djblets.extensions.models import RegisteredExtension
from djblets.extensions.signals import (extension_initialized,
                                        extension_uninitialized)
from djblets.urls.resolvers import DynamicURLResolver
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_permission_required,
                                       webapi_request_fields,
                                       webapi_response_errors)
from djblets.webapi.errors import (DOES_NOT_EXIST,
                                   ENABLE_EXTENSION_FAILED,
                                   DISABLE_EXTENSION_FAILED,
                                   PERMISSION_DENIED)
from djblets.webapi.fields import BooleanFieldType, StringFieldType
from djblets.webapi.resources.base import WebAPIResource


class ExtensionResource(WebAPIResource):
    """Provides information on installed extensions."""
    model = RegisteredExtension
    fields = {
        'author': {
            'type': StringFieldType,
            'description': 'The author of the extension.',
        },
        'author_url': {
            'type': StringFieldType,
            'description': "The author's website.",
        },
        'can_disable': {
            'type': BooleanFieldType,
            'description': 'Whether or not the extension can be disabled.',
        },
        'can_enable': {
            'type': BooleanFieldType,
            'description': 'Whether or not the extension can be enabled.',
        },
        'class_name': {
            'type': StringFieldType,
            'description': 'The class name for the extension.',
        },
        'enabled': {
            'type': BooleanFieldType,
            'description': 'Whether or not the extension is enabled.',
        },
        'installed': {
            'type': BooleanFieldType,
            'description': 'Whether or not the extension is installed.',
        },
        'loadable': {
            'type': BooleanFieldType,
            'description': 'Whether or not the extension is currently '
                           'loadable. An extension may be installed but '
                           'missing or may be broken due to a bug.',
        },
        'load_error': {
            'type': StringFieldType,
            'description': 'If the extension could not be loaded, this will '
                           'contain any errors captured while trying to load.',
        },
        'name': {
            'type': StringFieldType,
            'description': 'The name of the extension.',
        },
        'summary': {
            'type': StringFieldType,
            'description': "A summary of the extension's functionality.",
        },
        'version': {
            'type': StringFieldType,
            'description': 'The installed version of the extension.',
        },
    }
    name = 'extension'
    plural_name = 'extensions'
    uri_object_key = 'extension_name'
    uri_object_key_regex = r'[.A-Za-z0-9_-]+'
    model_object_key = 'class_name'

    allowed_methods = ('GET', 'PUT')

    def __init__(self, extension_manager):
        super(ExtensionResource, self).__init__()
        self._extension_manager = extension_manager
        self._dynamic_patterns = DynamicURLResolver()
        self._resource_url_patterns_map = {}

        # We want ExtensionResource to notice when extensions are
        # initialized or uninitialized, so connect some methods to
        # those signals.
        from djblets.extensions.signals import (extension_initialized,
                                                extension_uninitialized)
        extension_initialized.connect(self._on_extension_initialized)
        extension_uninitialized.connect(self._on_extension_uninitialized)

    def serialize_author_field(self, extension, *args, **kwargs):
        if extension.extension_class is None:
            return None

        return extension.extension_class.info.author

    def serialize_author_url_field(self, extension, *args, **kwargs):
        if extension.extension_class is None:
            return None

        return extension.extension_class.info.author_url

    def serialize_can_disable_field(self, extension, *args, **kwargs):
        return self._extension_manager.get_can_disable_extension(extension)

    def serialize_can_enable_field(self, extension, *args, **kwargs):
        return self._extension_manager.get_can_enable_extension(extension)

    def serialize_loadable_field(self, ext, *args, **kwargs):
        return (ext.extension_class is not None and
                ext.class_name not in self._extension_manager._load_errors)

    def serialize_load_error_field(self, extension, *args, **kwargs):
        s = self._extension_manager._load_errors.get(extension.class_name)

        if s:
            return s

        if extension.extension_class is None:
            return _(
                'This extension is not installed or could not be found. Try '
                're-installing it and then click "Reload Extensions".'
            )

        return None

    def serialize_name_field(self, extension, *args, **kwargs):
        if extension.extension_class is None:
            return extension.name
        else:
            return extension.extension_class.info.name

    def serialize_summary_field(self, extension, *args, **kwargs):
        if extension.extension_class is None:
            return None

        return extension.extension_class.info.summary

    def serialize_version_field(self, extension, *args, **kwargs):
        if extension.extension_class is None:
            return None

        return extension.extension_class.info.version

    @webapi_response_errors(DOES_NOT_EXIST, PERMISSION_DENIED)
    @webapi_login_required
    def get_list(self, request, *args, **kwargs):
        """Returns the list of known extensions.

        Each extension in the list has been installed, but may not be
        enabled.
        """
        return WebAPIResource.get_list(self, request, *args, **kwargs)

    def get_links(self, resources=[], obj=None, request=None, *args, **kwargs):
        links = super(ExtensionResource, self).get_links(
            resources, obj, request=request, *args, **kwargs)

        if request and obj:
            admin_base_href = '%s%s' % (
                request.build_absolute_uri(reverse('extension-list')),
                obj.class_name)

            extension_cls = obj.extension_class

            if extension_cls:
                extension_info = extension_cls.info

                if extension_info.is_configurable:
                    links['admin-configure'] = {
                        'method': 'GET',
                        'href': '%s/config/' % admin_base_href,
                    }

                if extension_info.has_admin_site:
                    links['admin-database'] = {
                        'method': 'GET',
                        'href': '%s/db/' % admin_base_href,
                    }

        return links

    @webapi_login_required
    @webapi_permission_required('extensions.change_registeredextension')
    @webapi_response_errors(PERMISSION_DENIED, DOES_NOT_EXIST,
                            ENABLE_EXTENSION_FAILED, DISABLE_EXTENSION_FAILED)
    @webapi_request_fields(
        required={
            'enabled': {
                'type': BooleanFieldType,
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

        extension_id = registered_extension.class_name

        if kwargs.get('enabled'):
            try:
                self._extension_manager.enable_extension(extension_id)
            except EnablingExtensionError as e:
                err = ENABLE_EXTENSION_FAILED.with_message(str(e))

                return err, {
                    'load_error': e.load_error,
                    'needs_reload': e.needs_reload,
                }
            except InvalidExtensionError as e:
                return ENABLE_EXTENSION_FAILED.with_message(str(e))
        else:
            try:
                self._extension_manager.disable_extension(extension_id)
            except (DisablingExtensionError, InvalidExtensionError) as e:
                return DISABLE_EXTENSION_FAILED.with_message(str(e))

        # Refetch extension, since the ExtensionManager may have changed
        # the model.
        registered_extension = \
            RegisteredExtension.objects.get(pk=registered_extension.pk)

        return 200, {
            self.item_result_key: registered_extension
        }

    def get_url_patterns(self):
        # We want extension resource URLs to be dynamically modifiable,
        # so we override get_url_patterns in order to capture and store
        # a reference to the url_patterns at /api/extensions/.
        url_patterns = super(ExtensionResource, self).get_url_patterns()
        url_patterns += [self._dynamic_patterns]

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
        Attaches an extension's resources to /api/extensions/{extension.id}/.
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
            self._resource_url_patterns_map[extension].extend([
                path('%s/%s/' % (extension.id, resource.uri_name),
                     include(resource.get_url_patterns())),
            ])

        self._dynamic_patterns.add_patterns(
            self._resource_url_patterns_map[extension])

    def _unattach_extension_resources(self, extension):
        """
        Unattaches an extension's resources from
        /api/extensions/{extension.id}/.
        """

        # Bail out if there are no resources for this extension
        if not extension.resources:
            return

        # If this extension has never had its resource URLs
        # generated, then we don't have anything to worry
        # about.
        if extension not in self._resource_url_patterns_map:
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
        Signal handler that notices when an extension has been initialized.
        """
        self._attach_extension_resources(ext_class)

    def _on_extension_uninitialized(self, sender, ext_class=None, **kwargs):
        """
        Signal handler that notices and reacts when an extension
        has been uninitialized.
        """
        self._unattach_extension_resources(ext_class)


class ExtensionRootResourceMixin(object):
    """Mixin for Root Resources making use of Extension Resources.

    As extensions are able to provide their own API resources, this mixin
    allows a root resource to generate URI templates for non built-in
    resources.

    See Also:
        :py:class:`~djblets.webapi.resources.root.RootResource`
    """

    def __init__(self, *args, **kwargs):
        """Initialize the extension resource mixin to listen for changes.

        Args:
            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Additional keyword arguments.
        """
        super(ExtensionRootResourceMixin, self).__init__(*args, **kwargs)

        extension_initialized.connect(
            self._generate_extension_uris_for_template)
        extension_uninitialized.connect(
            self._remove_extension_uris_from_template)

    def get_extension_resource(self):
        """Return the associated extension resource.

        Subclasses using this mixin must implement this method.

        Returns:
            djblets.extensions.resources.ExtensionResource:
            The extension resource associated with the root resource.
        """
        raise NotImplementedError

    def _generate_extension_uris_for_template(self, ext_class, **kwargs):
        """Generate URI templates for a newly enabled extension.

        Args:
            ext_class djblets.extensions.extension.Extension:
                The extension being added to the URI templates.

            **kwargs (dict):
                Additional keyword arguments.
        """
        ext_resource = self.get_extension_resource()

        for resource in ext_class.resources:
            partial_href = '%s/%s/' % (ext_class.id, resource.uri_name)

            for entry in self.walk_resources(resource, partial_href):
                self.register_uri_template(entry.name, entry.list_href,
                                           ext_resource)

    def _remove_extension_uris_from_template(self, ext_class, **kwargs):
        """Remove the URI templates of an extension when disabled.

        Args:
            ext_class djblets.extensions.extension.Extension:
                The extension being removed from the URI templates.

            **kwargs (dict):
                Additional keyword arguments.
        """
        ext_resource = self.get_extension_resource()

        for resource in ext_class.resources:
            partial_href = '%s/%s/' % (ext_class.id, resource.uri_name)

            for entry in self.walk_resources(resource, partial_href):
                self.unregister_uri_template(entry.name, ext_resource)
