"""A flexible resource for the root of your API resource tree."""

import logging
from collections import defaultdict, namedtuple
from threading import RLock
from typing import Callable, Dict, Optional, OrderedDict

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest, HttpResponseNotModified
from django.utils.translation import gettext_lazy as _
from django.urls import path
from typing_extensions import TypeAlias

from djblets.webapi.errors import DOES_NOT_EXIST
from djblets.webapi.resources.base import WebAPIResource
from djblets.webapi.responses import WebAPIResponseError


logger = logging.getLogger(__name__)


#: A type alias for a mapping of URI templates.
#:
#: Each key is a URI template name, and each value is a URL.
#:
#: Version Added:
#:     3.2
URITemplates: TypeAlias = Dict[str, str]


#: A mapping of API resource instances to URI templates.
#:
#: Version Added:
#:     3.2
_URITemplatesByResourceMap: TypeAlias = Dict[Optional[WebAPIResource],
                                             URITemplates]


class _URITemplatesCache:
    """A least-recently-used cache for URI templates.

    This will map base API URLs to generated dictionaries of URI templates. It
    holds up to a maximum number of cached entries, and will discard the oldest
    as needed once the limit is reached.

    Since cache state is shared between threads, adding and fetching items are
    done behind a thread lock, to avoid issues with multiple threads trying to
    manipulate the cache at the same time.

    Version Added:
        3.2
    """

    ######################
    # Instance variables #
    ######################

    #: The maximum number of URI templates to store in the cache.
    #:
    #: Type:
    #:     int
    max_size: int

    def __init__(
        self,
        max_size: int = 50,
    ) -> None:
        """Initialize the cache.

        Args:
            max_size (int, optional):
                The maximum size of the cache.
        """
        self.max_size = max_size
        self._cache = OrderedDict[str, URITemplates]()
        self._lock = RLock()

    def add(
        self,
        base_href: str,
        uri_templates: URITemplates,
    ) -> None:
        """Add URI templates to the cache.

        If the cache is full, the last item will be discarded.

        Args:
            base_href (str):
                The base API URL mapped to the URI templates.

            uri_templates (dict):
                The dictionary of generated URI templates.
        """
        with self._lock:
            cache = self._cache

            if len(cache) >= self.max_size:
                cache.popitem(last=False)

            cache[base_href] = uri_templates

    def get(
        self,
        base_href: str,
        *,
        build_func: Optional[Callable[[str], URITemplates]] = None,
    ) -> URITemplates:
        """Return URI templates from the cache.

        If the URI templates are in the cache, they'll be returned and then
        marked as most-recently used, to avoid falling out of cache too soon.

        Args:
            base_href (str):
                The base API URL mapped to the URI templates.

            build_func (callable, optional):
                Optional function to call to build the results if missing.

                This will be built while a lock is held.

        Returns:
            dict:
            The URI templates found in the cache. This may be
            newly-constructed.

        Raises:
            KeyError:
                No cached content exists for the given ``base_href``.
        """
        with self._lock:
            cache = self._cache

            try:
                uri_templates = cache[base_href]
                cache.move_to_end(base_href)
            except KeyError:
                if build_func is None:
                    raise

                uri_templates = build_func(base_href)
                self.add(base_href, uri_templates)

            return uri_templates

    def clear(self) -> None:
        """Clear the URI template cache."""
        with self._lock:
            self._cache.clear()


class RootResource(WebAPIResource):
    """The root of a resource tree.

    This is meant to be instantiated with a list of immediate child
    resources. The result of :py:meth:`get_url_patterns` should be included in
    a project's :file:`urls.py`.
    """

    name = 'root'
    singleton = True

    #: A resource entry returned from :py:meth:`RootResource.walk_resources`.
    #:
    #: Attributes:
    #:      name (str):
    #:          The name of current resource being explored.
    #:
    #       list_href (str):
    #:          The list_href associated with this resource.
    #:
    #       resource (djblets.webapi.resources.base.WebAPIResource):
    #:          The resource object being explored.
    #:
    #       is_list (bool):
    #:          Whether or not the resource is a list resource.
    #:
    #:      uri_template_name (str)
    #:          The name of the resource to use in the URI templates list.
    ResourceEntry = namedtuple('ResourceEntry',
                               ('name',
                                'list_href',
                                'resource',
                                'is_list',
                                'uri_template_name'))

    def __init__(self, child_resources=[], include_uri_templates=True):
        super(RootResource, self).__init__()
        self.list_child_resources = child_resources

        self._cached_uri_templates = _URITemplatesCache()
        self._registered_uri_templates: _URITemplatesByResourceMap = {}
        self._include_uri_templates = include_uri_templates

    def get_etag(self, request, obj, *args, **kwargs):
        return self.encode_etag(request, repr(obj))

    def get(self, request, *args, **kwargs):
        """Retrieve the list of top-level resources and URL templates."""
        data = self.serialize_root(request, *args, **kwargs)
        etag = self.get_etag(request, data)

        if self.are_cache_headers_current(request, etag=etag):
            return HttpResponseNotModified()

        return 200, data, {
            'ETag': etag,
        }

    def serialize_root(self, request, *args, **kwargs):
        """Serialize the contents of the root resource.

        By default, this just provides links and URI templates. Subclasses
        can override this to provide additional data, or to otherwise
        change the structure of the root resource.
        """
        data = {
            'links': self.get_links(self.list_child_resources,
                                    request=request, *args, **kwargs),
        }

        if self._include_uri_templates:
            data['uri_templates'] = self.get_uri_templates(request, *args,
                                                           **kwargs)

        return data

    def get_uri_templates(
        self,
        request: HttpRequest,
        *args,
        **kwargs,
    ) -> URITemplates:
        """Return all URI templates in the resource tree.

        REST APIs can be very chatty if a client wants to be well-behaved
        and crawl the resource tree asking for the links, instead of
        hard-coding the paths. The benefit is that they can keep from
        breaking when paths change. The downside is that it can take many
        HTTP requests to get the right resource.

        This list of all URI templates allows clients who know the resource
        name and the data they care about to simply plug them into the
        URI template instead of trying to crawl over the whole tree. This
        can make things far more efficient.

        Args:
            request (django.http.HttpRequest):
                The GET request for the Root resource.

            *args (tuple, unused):
                Additional unused arguments.

            **kwargs (dict, unused):
                Additional unused keyword arguments.

        Returns:
            dict:
            A mapping of resources to their URI templates.
        """
        base_href = request.build_absolute_uri()

        return self._cached_uri_templates.get(
            base_href,
            build_func=self.build_uri_templates)

    def build_uri_templates(
        self,
        base_href: str,
    ) -> URITemplates:
        """Build the URI templates to include in the payload.

        The resource will cache these automatically in local memory, so that
        repeated calls will often be unnecessary. This allows for things like
        per-organization APIs that each have their own cache.

        Caches are automatically invalidated as needed.

        Version Added:
            3.2

        Args:
            base_href (str):
                The base URL for the API endpoint.

        Returns:
            dict:
            A dictionary mapping URI template keys to template values.
        """
        templates = defaultdict(list)
        unassigned_templates = self._registered_uri_templates.get(
            None, {})

        for uri_template_name, href in unassigned_templates.items():
            templates[uri_template_name].append(href)

        for entry in self.walk_resources(self, base_href):
            uri_template_name = entry.uri_template_name

            if uri_template_name is None:
                continue

            templates[uri_template_name].append(entry.list_href)

            if entry.is_list:
                list_templates = self._registered_uri_templates.get(
                    entry.resource, {})

                for uri_template_name, href in list_templates.items():
                    templates[uri_template_name].append(
                        '%s%s' % (entry.list_href, href))

        final_templates = {}

        for uri_template_name, uri_template in templates.items():
            if len(uri_template) > 1:
                if settings.DEBUG or getattr(settings, 'PRODUCTION', True):
                    logger.error(
                        'More than one URI template was mapped to '
                        'the "%s" name: %s. Only the first one will be '
                        'included in the URI templates list. To '
                        'include the other URI templates, they must '
                        'be mapped to a unique name by setting each '
                        'resource\'s uri_template_name property.'
                        % (uri_template_name, ', '.join(uri_template)))
                else:
                    raise ImproperlyConfigured(
                        _('More than one URI template was mapped to '
                          'the "%(name)s" name: %(templates)s. Each URI '
                          'template must be mapped to a unique URI '
                          'template name in order to be included in the '
                          'URI templates list. This can be set through '
                          'the uri_template_name property.')
                        % {
                            'name': uri_template_name,
                            'templates': ', '.join(uri_template)
                        })

            final_templates[uri_template_name] = uri_template[0]

        return final_templates

    @classmethod
    def walk_resources(cls, resource, list_href):
        """Yield all URI endpoints associated with a specified resource.

        Args:
            resource (djblets.webapi.resources.WebAPIResource):
                The starting point for searching the resource tree.

            list_href (unicode):
                The path to the list resource, relative to the WebAPIResource
                provided. Used as a component of the URL in the API.

        Yields:
            RootResource.ResourceEntry:
            Resource entries for all sub-resources.
        """
        yield cls.ResourceEntry(
            name=resource.name_plural,
            list_href=list_href,
            resource=resource,
            is_list=True,
            uri_template_name=resource.uri_template_name_plural)

        for child in resource.list_child_resources:
            child_href = '%s%s/' % (list_href, child.uri_name)

            for entry in cls.walk_resources(child, child_href):
                yield entry

        if resource.uri_object_key:
            object_href = '%s{%s}/' % (list_href, resource.uri_object_key)

            yield cls.ResourceEntry(
                name=resource.name,
                list_href=object_href,
                resource=resource,
                is_list=False,
                uri_template_name=resource.uri_template_name)

            for child in resource.item_child_resources:
                child_href = '%s%s/' % (object_href, child.uri_name)

                for entry in cls.walk_resources(child, child_href):
                    yield entry

    def api_404_handler(self, request, api_format=None, *args, **kwargs):
        """Default handler at the end of the URL patterns.

        This returns an API 404, instead of a normal django 404.
        """
        return WebAPIResponseError(request,
                                   err=DOES_NOT_EXIST,
                                   api_format=api_format)

    def get_url_patterns(self):
        """Return the Django URL patterns for this object and its children.

        This returns the same list as
        :py:meth:`WebAPIResource.get_url_patterns`, but also introduces a
        generic catch-all 404 handler which returns API errors instead of HTML.
        """
        urlpatterns = super(RootResource, self).get_url_patterns()
        urlpatterns += [
            path('<str>', self.api_404_handler),
        ]

        return urlpatterns

    def register_uri_template(
        self,
        name: str,
        relative_path: str,
        relative_resource: Optional[WebAPIResource] = None,
    ) -> None:
        """Register the specified resource for URI template serialization.

        This adds the specified name and relative resource to the Root
        Resource's URI templates.

        Args:
            name (str):
                The name of the associated resource being added to templates.

            relative_path (str):
                The path of the API resource relative to its parent resources.

            relative_resource (djblets.webapi.resources.base.WebAPIResource,
                               optional):
                The resource instance associated with this URI template.
        """
        templates = self._registered_uri_templates.setdefault(
            relative_resource, {})

        if name in templates:
            logger.debug(
                'The %s resource is already mapped to the following '
                'URI template: %s. This will be overwritten by the new URI '
                'template: %s.'
                % (name, templates[name], relative_path))

        # Allow the URI template to be overwritten if it already exists.
        templates[name] = relative_path

        # Clear the cache so that new lookups can detect newly added templates.
        self._cached_uri_templates.clear()

    def unregister_uri_template(
        self,
        name: str,
        relative_resource: Optional[WebAPIResource] = None,
    ) -> None:
        """Unregister the specified resource for URI template serialization.

        This removes the specified name and relative resource to the Root
        Resource's URI templates.

        Args:
            name (str):
                The name of the resource being removed from templates.

            relative_resource (djblets.webapi.resources.base.WebAPIResource,
                               optional):
                The resource instance associated with this URI template.
        """
        try:
            del self._registered_uri_templates[relative_resource][name]
        except KeyError:
            return

        # Clear the cache so that new lookups won't include the old URI
        # templates.
        self._cached_uri_templates.clear()
