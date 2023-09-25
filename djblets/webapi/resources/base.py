"""Base class for a resource in an API."""

from __future__ import annotations

import logging
import warnings
from typing import (Any, List, Mapping, Optional, Sequence, TYPE_CHECKING,
                    Type, Union)

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models.fields.related_descriptors import (
    ManyToManyDescriptor,
    ForwardManyToOneDescriptor)
from django.db.models.query import QuerySet
from django.http import (HttpResponseNotAllowed, HttpResponse,
                         HttpResponseNotModified)
from django.urls import include, path, re_path, reverse
from django.views.decorators.vary import vary_on_headers
from typing_extensions import Literal, NotRequired, TypedDict

from djblets.auth.ratelimit import (RATE_LIMIT_API_ANONYMOUS,
                                    RATE_LIMIT_API_AUTHENTICATED,
                                    get_usage_count)
from djblets.util.decorators import cached_property
from djblets.util.http import (build_not_modified_from_response,
                               encode_etag,
                               etag_if_none_match,
                               get_http_requested_mimetype,
                               get_modified_since,
                               set_etag,
                               set_last_modified)
from djblets.webapi.auth.backends import check_login
from djblets.webapi.resources.registry import (get_resource_for_object,
                                               _class_to_resources,
                                               _name_to_resources)
from djblets.webapi.responses import (WebAPIResponse,
                                      WebAPIResponseError,
                                      WebAPIResponsePaginated)
from djblets.webapi.decorators import (SPECIAL_PARAMS,
                                       webapi_login_required,
                                       webapi_request_fields,
                                       webapi_response_errors)
from djblets.webapi.errors import (DOES_NOT_EXIST,
                                   LOGIN_FAILED,
                                   NOT_LOGGED_IN,
                                   PERMISSION_DENIED,
                                   RATE_LIMIT_EXCEEDED,
                                   WebAPIError)
from djblets.webapi.fields import IntFieldType

if TYPE_CHECKING:
    from django.db.models import Model

    from djblets.webapi.fields import (BaseAPIFieldType,
                                       ListFieldTypeItemsInfo)


m2m_descriptors = (ManyToManyDescriptor,)
fkey_descriptors = (ForwardManyToOneDescriptor,)


logger = logging.getLogger(__name__)


class WebAPIResourceFieldInfo(TypedDict):
    """Information on a field in a serialized API payload.

    Version Added:
        4.0
    """

    #: A description of the field.
    #:
    #: This is in ReStructuredText format, and is intended for documentation
    #: generation.
    #:
    #: Type
    #:     str
    description: str

    #: The type of field.
    #:
    #: This should be a :py:class:`~djblets.webapi.fields.BaseAPIFieldType`
    #: subclass.
    #:
    #: For backwards-compatibiltiy, :py:class:`str`, :py:class:`bytes`,
    #: :py:class:`bool`, :py:class:`int`, or a :py:class:`list, or
    #: :py:class:`tuple` of string values can be specified, but these are
    #: considered legacy.
    type: Union[
        Type[BaseAPIFieldType],
        Type[bytes],
        Type[str],
        Type[bool],
        Type[int],
        Sequence[str],
    ]

    #: The version of the product the field was added in.
    #:
    #: Type:
    #:     str
    added_in: NotRequired[str]

    #: A list of choices allowed for the field.
    #:
    #: This is available if using
    # :py:class:`djblets.webapi.fields.ChoiceFieldType`.
    choices: Sequence[str]

    #: The version of the product the field was deprecated in.
    #:
    #: Type:
    #:     str
    deprecated_in: NotRequired[str]

    #: Information on the type in a list of items.
    #:
    #: This is available if using
    # :py:class:`djblets.webapi.fields.ListFieldType`.
    #:
    #: Type:
    #:     dict
    items: NotRequired[ListFieldTypeItemsInfo]

    #: A referenced resource for the field.
    #:
    #: This is available if using
    # :py:class:`djblets.webapi.fields.ResourceFieldType`.
    #:
    #: Type:
    #:     str or type
    resource: NotRequired[Union[str, Type[WebAPIResource]]]


class AllowedMimetypeEntry(TypedDict):
    """An allowed mimetype for an item and list resource.

    Version Added:
        4.0
    """

    #: An allowed mimetype for a list resource.
    #:
    #: This can be ``None`` or omitted in order to avoid defining a list
    #: mimetype for this entry.
    #:
    #: Type:
    #:     str
    item: NotRequired[Optional[str]]

    #: An allowed mimetype for a list resource.
    #:
    #: This can be ``None`` or omitted in order to avoid defining an item
    #: mimetype for this entry.
    #:
    #: Type:
    #:     str
    list: NotRequired[Optional[str]]


class WebAPIResource(object):
    """A resource handling HTTP operations for part of the API.

    A WebAPIResource is a RESTful resource living at a specific URL. It
    can represent either an object or a list of objects, and can respond
    to various HTTP methods (GET, POST, PUT, DELETE).

    Subclasses are expected to override functions and variables in order to
    provide specific functionality, such as modifying the resource or
    creating a new resource.

    For information on writing an API resource, see
    :ref:`writing-api-resources`.
    """

    #: A Django model backing this API resource.
    #:
    #: If provided, this resource will automatically handle querying and
    #: representation of resource instances. Subclasses will still want to
    #: handle access control, fields, parent resources, child resources, and
    #: custom-build support for adding, updating, and deleting resources.
    #:
    #: Type:
    #:     type
    model: Optional[Type[Model]] = None

    #: A mapping of field names to definitions for any serialized objects.
    #:
    #: Each key should be a field name either present in :py:attr:`model` or
    #: defined as a :samp:`serialize_<fieldname>_field` method.
    #:
    #: Type:
    #:     dict
    fields: Mapping[
        str,
        Union[WebAPIResourceFieldInfo, Mapping[str, Any]]
    ] = {}

    #: A regex for mapping keys for an object in an item resource.
    #:
    #: By default, this matches integers. Subclasses can override this to
    #: match IDs with other values.
    #:
    #: Type:
    #:     str
    uri_object_key_regex: str = r'[0-9]+'

    #: The key to populate with the ID of an object in an item resource.
    #:
    #: Type:
    #:     str
    uri_object_key: Optional[str] = None

    #: The key on the provided model for matching an object key.
    #:
    #: This is used when :py:attr:`model` is set, allowing API resources to
    #: automatically query for a model instance matching this model key to
    #: the value in the URL corresponding to :py:attr:`uri_object_key`.
    #:
    #: Type:
    #:     str
    model_object_key: str = 'pk'

    #: A key on the provided model for matching a parent resource's model.
    #:
    #: This is used when :py:attr:`model` is set, allowing API resources to
    #: locate the parent resource for the purposes of access checks and
    #: URL generation.
    #:
    #: Type:
    #:     str
    model_parent_key: Optional[str] = None

    #: The field on an item resource object to use for a Last-Modified header.
    #:
    #: Type:
    #:     str
    last_modified_field: Optional[str] = None

    #: The field on an item resource object to use for an ETag header.
    #:
    #: Type:
    #:     str
    etag_field: Optional[str] = None

    #: Whether to auto-generate ETags for responses.
    #:
    #: If set, and an ETag is not otherwise provided, one will be generated
    #: based on the response payload.
    #:
    #: Type:
    #:     bool
    autogenerate_etags: bool = False

    #: Whether the resource is a singleton.
    #:
    #: Singleton resources behave like an item resource without a parent list
    #: resource. They have a single endpoint.
    #:
    #: Type:
    #:     bool
    singleton: bool = False

    #: A list of child resources to link to on the list resource.
    #:
    #: Type:
    #:     list of WebAPIResource
    list_child_resources: Sequence[WebAPIResource] = []

    #: A list of child resources to link to on the item resource.
    #:
    #: Type:
    #:     list of WebAPIResource
    item_child_resources: Sequence[WebAPIResource] = []

    #: A list of HTTP methods that are allowed on this resource.
    #:
    #: Subclasses must have resource handlers defined for each allowed HTTP
    #: method.
    #:
    #: Type:
    #:     tuple of str
    allowed_methods: Sequence[str] = ('GET',)

    #: A vendor name to use within item and list resource mimetypes.
    #:
    #: This will be the ``vendor`` in
    #: :samp:`{category}/vnd.{vendor}.{name}+{format}`.
    #:
    #: Type:
    #:     str
    mimetype_vendor: Optional[str] = None

    #: An explicit name to use within list resource mimetypees.
    #:
    #: This will be the ``name`` in
    #: :samp:`{category}/vnd.{vendor}.{name}+{format}`.
    #:
    #: Type:
    #:     str
    mimetype_list_resource_name: Optional[str] = None

    #: An explicit name to use within item resource mimetypees.
    #:
    #: This will be the ``name`` in
    #: :samp:`{category}/vnd.{vendor}.{name}+{format}`.
    #:
    #: Type:
    #:     str
    mimetype_item_resource_name: Optional[str] = None

    #: Mimetypes allowed for requests to the resource.
    #:
    #: Each entry defines optional item and/or list mimetypes that
    #: correspond to :mailheader:`Accept` header values.
    #:
    #: Instances of this resource may have a modified version of the list
    #: set on the class.
    #:
    #: Type:
    #:     list
    allowed_mimetypes: Sequence[AllowedMimetypeEntry] = [
        {
            'list': mime,
            'item': mime,
        }
        for mime in WebAPIResponse.supported_mimetypes
    ]

    #: The class to use for paginated results in list resources.
    #:
    #: Type:
    #:     list
    paginated_cls: Type[WebAPIResponsePaginated] = WebAPIResponsePaginated

    #: A mapping of HTTP methods to handler method names.
    #:
    #: Type:
    #:     dict
    method_mapping: Mapping[str, str] = {
        'GET': 'get',
        'POST': 'post',
        'PUT': 'put',
        'DELETE': 'delete',
    }

    ######################
    # Instance variables #
    ######################

    #: A flag noting this class is an API handler.
    #:
    #: This is always ``True``. It's set to help middleware or other
    #: processors differentiate API views from others.
    #:
    #: Type:
    #:     bool
    is_webapi_handler: Literal[True]

    #: The parent resource for this resource.
    #:
    #: Type:
    #:     WebAPIResource
    _parent_resource: Optional[WebAPIResource] = None

    #: A cached list of fields to pre-fetch when querying resources.
    #:
    #: This is automatically computed in :py:meth:`_get_queryset` once for
    #: the lifetime of the resource instance.
    #:
    #: Type:
    #:     list of str
    _prefetch_related_fields: List[str]

    #: A cached list of fields to select when querying resources.
    #:
    #: This is automatically computed in :py:meth:`_get_queryset` once for
    #: the lifetime of the resource instance.
    #:
    #: Type:
    #:     list of str
    _select_related_fields: List[str]

    def __init__(self):
        _name_to_resources[self.name] = self
        _name_to_resources[self.name_plural] = self
        _class_to_resources[self.__class__] = self

        # Mark this class, and any subclasses, to be Web API handlers
        self.is_webapi_handler = True

        # Copy this list, because otherwise we may modify the class-level
        # version of it.
        self.allowed_mimetypes = list(self.allowed_mimetypes)

        if self.mimetype_vendor:
            # Generate list and item resource-specific mimetypes
            # for each supported mimetype, and add them as a pair to the
            # allowed mimetypes.
            for mimetype_pair in self.allowed_mimetypes:
                vend_mimetype_pair = {
                    'list': None,
                    'item': None,
                }

                for key, is_list in [('list', True), ('item', False)]:
                    if (key in mimetype_pair and
                        (mimetype_pair[key] in
                         WebAPIResponse.supported_mimetypes)):
                        vend_mimetype_pair[key] = \
                            self._build_resource_mimetype(mimetype_pair[key],
                                                          is_list)

                if vend_mimetype_pair['list'] or vend_mimetype_pair['item']:
                    self.allowed_mimetypes.append(vend_mimetype_pair)

    @vary_on_headers('Accept', 'Cookie')
    def __call__(self, request, api_format=None, *args, **kwargs):
        """Invoke the correct HTTP handler based on the type of request.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            api_format (str, optional):
                The API format requested by the caller (``json`` or ``xml``).

                This is considered legacy and may be removed in a future
                release.

            *args (tuple):
                Additional positional arguments passed by the URL dispatcher.

            **kwargs (dict):
                Keyword arguments representing values captured from the URL.

        Returns:
            django.http.HttpResponse:
            The resulting HTTP response from the API handler.
        """
        if not hasattr(request, '_djblets_webapi_object_cache'):
            request._djblets_webapi_object_cache = {}

        auth_result = check_login(request)
        headers = {}

        if isinstance(auth_result, tuple):
            auth_success, auth_message, auth_headers = auth_result
            headers = auth_headers or {}

            if not auth_success:
                err = LOGIN_FAILED

                if auth_message:
                    err = err.with_message(auth_message)

                return WebAPIResponseError(
                    request,
                    err=err,
                    headers=headers,
                    api_format=api_format,
                    mimetype=self._build_error_mimetype(request))

        # Check to see if the user has been rate limited. Rate limits for
        # authentication failures have already been handled via the auth
        # backend, so this just checks for the API rate limits, if any.
        if auth_result:
            rate_limit_type = RATE_LIMIT_API_AUTHENTICATED
        else:
            rate_limit_type = RATE_LIMIT_API_ANONYMOUS

        usage = get_usage_count(request, increment=True,
                                limit_type=rate_limit_type)

        if (usage is not None and
            usage['count'] > usage['limit']):
            headers['Retry-After'] = usage['time_left']
            headers['X-RateLimit-Limit'] = usage['limit']

            return WebAPIResponseError(
                request,
                err=RATE_LIMIT_EXCEEDED,
                headers=headers,
                api_format=api_format,
                mimetype=self._build_error_mimetype(request))

        method = request.method

        if method == 'POST':
            # Not all clients can do anything other than GET or POST.
            # So, in the case of POST, we allow overriding the method
            # used.
            method = request.POST.get('_method', kwargs.get('_method', method))
        elif method == 'PUT':
            # Normalize the PUT data so we can get to it.
            # This is due to Django's treatment of PUT vs. POST. They claim
            # that PUT, unlike POST, is not necessarily represented as form
            # data, so they do not parse it. However, that gives us no clean
            # way of accessing the data. So we pretend it's POST for a second
            # in order to parse.
            #
            # This must be done only for legitimate PUT requests, not faked
            # ones using ?method=PUT.
            try:
                request.method = 'POST'
                request._load_post_and_files()
                request.method = 'PUT'
            except AttributeError:
                request.META['REQUEST_METHOD'] = 'POST'
                request._load_post_and_files()
                request.META['REQUEST_METHOD'] = 'PUT'

        request._djblets_webapi_method = method
        request._djblets_webapi_kwargs = kwargs
        request.PUT = request.POST

        if method in self.allowed_methods:
            if (method == "GET" and
                not self.singleton and
                (self.uri_object_key is None or
                 self.uri_object_key not in kwargs)):
                view = self.get_list
            else:
                view = getattr(self, self.method_mapping.get(method, None))
        else:
            view = None

        if view and callable(view):
            result = self.call_method_view(
                request, method, view, api_format=api_format, *args, **kwargs)

            if isinstance(result, WebAPIResponse):
                response = result
            elif isinstance(result, WebAPIError):
                response = WebAPIResponseError(
                    request,
                    err=result,
                    api_format=api_format,
                    mimetype=self._build_error_mimetype(request))
            elif isinstance(result, tuple):
                if method == 'GET':
                    request_params = request.GET
                else:
                    request_params = request.POST

                if len(result) == 3:
                    headers.update(result[2])

                if 'Location' in headers:
                    extra_querystr = '&'.join([
                        '%s=%s' % (param, request_params[param])
                        for param in SPECIAL_PARAMS
                        if param in request_params
                    ])

                    if extra_querystr:
                        if '?' in headers['Location']:
                            headers['Location'] += '&' + extra_querystr
                        else:
                            headers['Location'] += '?' + extra_querystr

                if isinstance(result[0], WebAPIError):
                    response = WebAPIResponseError(
                        request,
                        err=result[0],
                        extra_params=result[1],
                        api_format=api_format,
                        mimetype=self._build_error_mimetype(request))
                else:
                    response_args = self.build_response_args(request)
                    headers.update(response_args.pop('headers', {}))

                    response = WebAPIResponse(
                        request,
                        status=result[0],
                        obj=result[1],
                        api_format=api_format,
                        encoder_kwargs=dict({
                            'calling_resource': self,
                        }, **kwargs),
                        **response_args)
            elif isinstance(result, HttpResponse):
                response = result
            else:
                raise AssertionError(result)

            if 200 <= response.status_code < 300:
                # Check if there's no explicit ETag in a GET/HEAD request and
                # the resource is told to generate missing ETags automatically.
                #
                # Starting in Djblets 2.0, we do this after a response payload
                # is generated instead of up-front, so that we don't serialize
                # the resource payload twice.
                if (self.autogenerate_etags and
                    method in ('GET', 'HEAD') and
                    'ETag' not in response):
                    # There's no ETag, so we'll build one based on the payload
                    # content and check to see if the client already has it.
                    etag = encode_etag(response.content)
                    set_etag(response, etag)

                    if self.are_cache_headers_current(request, etag=etag):
                        response = build_not_modified_from_response(response)
        else:
            response = HttpResponseNotAllowed(self.allowed_methods)

        # Make sure any headers we've collected along the way are in the
        # response.
        for header_name, header_value in headers.items():
            response.setdefault(header_name, header_value)

        return response

    @property
    def __name__(self):
        return self.__class__.__name__

    @property
    def name(self):
        """The name of the resource, used for keys in the payloads.

        If :py:attr:`model` is set, this will be the lowercase version of
        the model name. Otherwise, it will be the lowercase version of this
        resource class's name.

        Subclasses can override this to set an explicit name.
        Type:
            str
        """
        if not hasattr(self, '_name'):
            if self.model:
                self._name = self.model.__name__.lower()
            else:
                self._name = self.__name__.lower()

        return self._name

    @property
    def name_plural(self):
        """The plural name of the object, used for lists.

        If :py:attr:`singleton` is set, this will be the result of
        :py:attr:`name`. Otherwise, it will be pluralized form of
        :py:attr:`name`.

        Subclasses can override this to set an explicit plural name.

        Type:
            str
        """
        if not hasattr(self, '_name_plural'):
            if self.singleton:
                self._name_plural = self.name
            else:
                self._name_plural = self.name + 's'

        return self._name_plural

    @property
    def item_result_key(self):
        """The key for serialized objects in an item payload.

        This defaults to using :py:attr:`name` as the key. Subclasses can
        override this to set an explicit key.

        Type:
            str
        """
        return self.name

    @property
    def list_result_key(self):
        """The key for serialized object lists in a list payload.

        This defaults to using :py:attr:`name_plural` as the key. Subclasses
        can override this to set an explicit key.

        Type:
            str
        """
        return self.name_plural

    @property
    def uri_name(self):
        """The name of the resource in the URI.

        This can be overridden when the name in the URI needs to differ
        from the name used for the resource.

        Type:
            str
        """
        return self.name_plural.replace('_', '-')

    @property
    def link_name(self):
        """The name of the resource for use in a link.

        This can be overridden when the name in the link needs to differ
        from the name used for the resource.

        Type:
            str
        """
        return self.name_plural

    @cached_property
    def uri_template_name(self) -> Optional[str]:
        """The name of the resource for use in URI templates.

        This will be used as the key for this resource in
        :py:class`djblets.webapi.resource.root.RootResource`'s list of URI
        templates. This can be overridden when the URI template name for
        this resource needs to differ from the name used for the resource.

        This must be unique to the resource. If set to ``None`` this
        resource will be excluded from the URI templates list.

        Version Added:
            3.1.0

        Type:
            str or None
        """
        return self.name

    @cached_property
    def uri_template_name_plural(self) -> Optional[str]:
        """The plural name of the resource for use in URI templates.

        This will be used as the key for the list version of this resource in
        :py:class`djblets.webapi.resource.root.RootResource`'s list of URI
        templates. This can be overridden when the URI template name for
        this resource needs to differ from the name used for the resource.

        This must be unique to the resource. If set to ``None`` the list
        version of this resource will be excluded from the URI templates list.

        Version Added:
            3.1.0

        Type:
            str or None
        """
        uri_template_name = self.uri_template_name

        if uri_template_name is None:
            return None
        elif uri_template_name == self.name:
            return self.name_plural
        elif self.singleton:
            return self.uri_template_name
        else:
            return uri_template_name + 's'

    def call_method_view(self, request, method, view, *args, **kwargs):
        """Call the given HTTP method handler view.

        This will just call the given view by default, passing in all
        args and kwargs.

        This can be overridden by subclasses to perform additional
        checks or pass additional data to the view.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            method (str):
                The HTTP method used in the request.

            view (callable):
                The API handler function to call for the HTTP method.

            *args (tuple):
                Positional arguments to pass to the view.

            **kwargs (dict):
                Keyword arguments representing values captured from the URL.
        """
        return view(request, *args, **kwargs)

    def build_response_args(self, request):
        """Build keyword arguments to pass to a response class.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

        Returns:
            dict:
            Keyword arguments to pass to the response class.
        """
        is_list = (request._djblets_webapi_method == 'GET' and
                   not self.singleton and
                   (self.uri_object_key is None or
                    self.uri_object_key not in request._djblets_webapi_kwargs))

        if is_list:
            key = 'list'
        else:
            key = 'item'

        supported_mimetypes = [
            mime[key]
            for mime in self.allowed_mimetypes
            if mime.get(key)
        ]

        mimetype = get_http_requested_mimetype(request, supported_mimetypes)

        if (self.mimetype_vendor and
            mimetype in WebAPIResponse.supported_mimetypes):
            mimetype = self._build_resource_mimetype(mimetype, is_list)

        response_args = {
            'supported_mimetypes': supported_mimetypes,
            'mimetype': mimetype,
        }

        if is_list:
            for mimetype_pair in self.allowed_mimetypes:
                if (mimetype_pair.get('list') == mimetype and
                    mimetype_pair.get('item')):
                    response_args['headers'] = {
                        'Item-Content-Type': mimetype_pair['item'],
                    }
                    break

        return response_args

    def get_object(self, request, id_field=None, *args, **kwargs):
        """Return an object, given the captured parameters from a URL.

        This will perform a query for the object, taking into account
        :py:attr:`model_object_key`, :py:attr:`uri_object_key`, and any
        captured parameters from the URL.

        This requires that :py:attr:`model` and :py:attr:`uri_object_key`` are
        set.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            id_field (str, optional):
                An explicit ID field on the object.

                If not provided, this will default to
                :py:attr:`model_object_key`.

            *args (tuple):
                Positional arguments passed to the API handler method.

            **kwargs (dict):
                Keyword arguments representing values captured from the URL.

        Raises:
            django.core.exceptions.ObjectDoesNotExist:
                The object does not exist in the database.
        """
        assert self.model
        assert self.singleton or self.uri_object_key

        if self.singleton:
            cache_key = '%d' % id(self)
        else:
            id_field = id_field or self.model_object_key
            object_id = kwargs[self.uri_object_key]
            cache_key = '%d:%s:%s' % (id(self), id_field, object_id)

        if cache_key in request._djblets_webapi_object_cache:
            return request._djblets_webapi_object_cache[cache_key]

        if 'is_list' in kwargs:
            # Don't pass this in to _get_queryset, since we're not fetching
            # a list, and don't want the extra optimizations for lists to
            # kick in.
            del kwargs['is_list']

        queryset = self._get_queryset(request, *args, **kwargs)

        if self.singleton:
            obj = queryset.get()
        else:
            obj = queryset.get(**{
                id_field: object_id,
            })

        request._djblets_webapi_object_cache[cache_key] = obj

        return obj

    def post(self, *args, **kwargs):
        """Handle HTTP POST requests.

        This is not meant to be overridden unless there are specific needs.

        This will invoke :py:meth:`create` if doing an HTTP POST on a list
        resource.

        By default, an HTTP POST is not allowed on individual object
        resources.

        Args:
            *args (tuple):
                Positional arguments passed to the view.

            **kwargs (dict):
                Keyword arguments representing values captured from the URL.

        Returns:
            WebAPIResourceHandlerResult:
            The HTTP response, API error, or tuple results from the API
            handler.
        """
        if 'POST' not in self.allowed_methods:
            return HttpResponseNotAllowed(self.allowed_methods)

        if (self.uri_object_key is None or
            kwargs.get(self.uri_object_key, None) is None):
            return self.create(*args, **kwargs)

        # Don't allow POSTs on children by default.
        allowed_methods = list(self.allowed_methods)
        allowed_methods.remove('POST')

        return HttpResponseNotAllowed(allowed_methods)

    def put(self, request, *args, **kwargs):
        """Handle HTTP PUT requests.

        This is not meant to be overridden unless there are specific needs.

        This will invoke :py:meth:`update` if doing an HTTP PUT.

        Args:
            request (django.http.HttpClient):
                The HTTP client from the request.

            *args (tuple):
                Positional arguments passed to the view.

            **kwargs (dict):
                Keyword arguments representing values captured from the URL.

        Returns:
            WebAPIResourceHandlerResult:
            The HTTP response, API error, or tuple results from the API
            handler.
        """
        return self.update(request, *args, **kwargs)

    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    def get(self, request, api_format, *args, **kwargs):
        """Handle HTTP GETs to item resources.

        By default, this will check for access permissions and query for
        the object. It will then return a serialized form of the object.

        This may need to be overridden if needing more complex logic.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            api_format (str):
                An explicit API format requested for the response.

            *args (tuple):
                Positional arguments passed to the view.

            **kwargs (dict):
                Keyword arguments representing values captured from the URL.

        Returns:
            WebAPIResourceHandlerResult:
            The HTTP response, API error, or tuple results from the API
            handler.
        """
        if (not self.model or
            (self.uri_object_key is None and not self.singleton)):
            return HttpResponseNotAllowed(self.allowed_methods)

        try:
            obj = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_access_permissions(request, obj, *args, **kwargs):
            return self.get_no_access_error(request, obj=obj, *args, **kwargs)

        last_modified_timestamp = self.get_last_modified(request, obj)
        etag = self.get_etag(request, obj, **kwargs)

        if self.are_cache_headers_current(request, last_modified_timestamp,
                                          etag):
            response = HttpResponseNotModified()
        else:
            data = {
                self.item_result_key: self.serialize_object(obj,
                                                            request=request,
                                                            *args, **kwargs),
            }

            response = WebAPIResponse(request,
                                      status=200,
                                      obj=data,
                                      api_format=api_format,
                                      **self.build_response_args(request))

        if last_modified_timestamp:
            set_last_modified(response, last_modified_timestamp)

        if etag:
            set_etag(response, etag)

        return response

    @webapi_response_errors(NOT_LOGGED_IN, PERMISSION_DENIED, DOES_NOT_EXIST)
    @webapi_request_fields(
        optional={
            'start': {
                'type': IntFieldType,
                'description': 'The 0-based index of the first result in '
                               'the list. The start index is usually the '
                               'previous start index plus the number of '
                               'previous results. By default, this is 0.',
            },
            'max-results': {
                'type': IntFieldType,
                'description': 'The maximum number of results to return in '
                               'this list. By default, this is 25. There is '
                               'a hard limit of 200; if you need more than '
                               '200 results, you will need to make more '
                               'than one request, using the "next" '
                               'pagination link.',
            }
        },
        allow_unknown=True
    )
    def get_list(self, request, *args, **kwargs):
        """Handle HTTP GETs to list resources.

        By default, this will query for a list of objects and return the
        list in a serialized form.

        This may need to be overridden if needing more complex logic.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple):
                Positional arguments passed to the view.

            **kwargs (dict):
                Keyword arguments representing values captured from the URL.

        Returns:
            WebAPIResourceHandlerResult:
            The HTTP response, API error, or tuple results from the API
            handler.
        """
        data = {
            'links': self.get_links(self.list_child_resources,
                                    request=request, *args, **kwargs),
        }

        if not self.has_list_access_permissions(request, *args, **kwargs):
            return self.get_no_access_error(request, *args, **kwargs)

        if self.model:
            try:
                queryset = self._get_queryset(request, is_list=True,
                                              *args, **kwargs)
            except ObjectDoesNotExist:
                return DOES_NOT_EXIST

            return self.paginated_cls(
                request,
                queryset=queryset,
                results_key=self.list_result_key,
                serialize_object_func=lambda obj:
                    self.get_serializer_for_object(obj).serialize_object(
                        obj, request=request, *args, **kwargs),
                extra_data=data,
                **self.build_response_args(request))
        else:
            return 200, data

    @webapi_login_required
    def create(self, request, api_format, *args, **kwargs):
        """Handle HTTP POST requests to list resources.

        This is used to create a new object on the list, given the data
        provided in the request. It should usually return :http:`201` upon
        success.

        By default, this returns :http:`405`.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            api_format (str):
                An explicit API format requested for the response.

            *args (tuple):
                Positional arguments passed to the view.

            **kwargs (dict):
                Keyword arguments representing values captured from the URL.

        Returns:
            WebAPIResourceHandlerResult:
            The HTTP response, API error, or tuple results from the API
            handler.
        """
        return HttpResponseNotAllowed(self.allowed_methods)

    @webapi_login_required
    def update(self, request, api_format, *args, **kwargs):
        """Handle HTTP PUT requests to object resources.

        This is used to update an object, given full or partial data provided
        in the request. It should usually return :http:`200` upon success.

        By default, this returns :http:`405`.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            api_format (str):
                An explicit API format requested for the response.

            *args (tuple):
                Positional arguments passed to the view.

            **kwargs (dict):
                Keyword arguments representing values captured from the URL.

        Returns:
            WebAPIResourceHandlerResult:
            The HTTP response, API error, or tuple results from the API
            handler.
        """
        return HttpResponseNotAllowed(self.allowed_methods)

    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    def delete(self, request, api_format, *args, **kwargs):
        """Handles HTTP DELETE requests to object resources.

        This is used to delete an object, if the user has permissions to
        do so.

        By default, this deletes the object and returns :http:`204`.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            api_format (str):
                An explicit API format requested for the response.

            *args (tuple):
                Positional arguments passed to the view.

            **kwargs (dict):
                Keyword arguments representing values captured from the URL.

        Returns:
            WebAPIResourceHandlerResult:
            The HTTP response, API error, or tuple results from the API
            handler.
        """
        if not self.model or self.uri_object_key is None:
            return HttpResponseNotAllowed(self.allowed_methods)

        try:
            obj = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_delete_permissions(request, obj, *args, **kwargs):
            return self.get_no_access_error(request, obj=obj, *args, **kwargs)

        obj.delete()

        return 204, {}

    def get_queryset(self, request, is_list=False, *args, **kwargs):
        """Return a queryset used for querying objects or lists of objects.

        Subclasses can override this to filter objects, include related
        objects, or otherwise specialize the queryset.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            is_list (bool, optional):
                Whether this should be returning a queryset for a list
                resource.

                Subclasses can use this to query additional state based on
                query arguments or other criteria.

            *args (tuple):
                Positional arguments passed to the view.

            **kwargs (dict):
                Keyword arguments representing values captured from the URL.

        Returns:
            django.db.models.QuerySet:
            A queryset for objects for this resource.

        Raises:
            django.core.exceptions.ObjectDoesNotExist:
                The object does not exist.

                This may be thrown by an overridden function if the object
                or a parent object does not exist.
        """
        return self.model.objects.all()

    def get_url_patterns(self):
        """Return the Django URL patterns for this object and its children.

        This is used to automatically build up the URL hierarchy for all
        objects. Projects should call this for top-level resources and
        return them in the :file:`urls.py` files.

        Returns:
            list:
            The list of URL patterns.
        """
        urlpatterns = [
            path('',
                 self.__call__,
                 name=self._build_named_url(self.name_plural)),
        ]

        for resource in self.list_child_resources:
            resource._parent_resource = self
            urlpatterns += [
                path(resource.uri_name + '/',
                     include(resource.get_url_patterns())),
            ]

        if self.uri_object_key or self.singleton:
            # If the resource has particular items in it...
            if self.uri_object_key:
                base_regex = r'^(?P<%s>%s)/' % (self.uri_object_key,
                                                self.uri_object_key_regex)
            elif self.singleton:
                base_regex = r'^'

            urlpatterns += [
                re_path(base_regex + r'$',
                        self.__call__,
                        name=self._build_named_url(self.name))
            ]

            for resource in self.item_child_resources:
                resource._parent_resource = self
                child_regex = base_regex + resource.uri_name + r'/'
                urlpatterns += [
                    re_path(child_regex, include(resource.get_url_patterns())),
                ]

        return urlpatterns

    def has_access_permissions(self, request, obj, *args, **kwargs):
        """Return whether the user has read access to the item resource.

        This is used for HTTP GET requests on the item resource. For list
        resources, see :py:meth:`has_list_access_permissions`.

        Subclasses should override this to provide any specific access control
        needed for accessing items.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            obj (object):
                The object to check for permissions.

            *args (tuple):
                Additional positional arguments passed to the view.

            **kwargs (dict):
                Keyword arguments representing values captured from the URL.

        Returns:
            bool:
            ``True`` if the user has access permissions. ``False`` if it
            does not.
        """
        return True

    def has_list_access_permissions(self, request, *args, **kwargs):
        """Return whether the user has read access to the list resource.

        This is used for HTTP GET requests on the list resource. For item
        resources, see :py:meth:`has_access_permissions`.

        By default, this will check the parent resource (if there is one) for
        access permissions.

        Subclasses should override this to provide any specific access control
        needed for accessing lists of items.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple):
                Additional positional arguments passed to the view.

            **kwargs (dict):
                Keyword arguments representing values captured from the URL.

        Returns:
            bool:
            ``True`` if the user has access permissions. ``False`` if it
            does not.
        """
        if self._parent_resource and self.model_parent_key:
            try:
                parent_obj = self._parent_resource.get_object(
                    request, *args, **kwargs)

                return self._parent_resource.has_access_permissions(
                    request, parent_obj, *args, **kwargs)
            except Exception:
                # Other errors, like Does Not Exist, should be caught
                # separately. As of here, we'll allow it to pass, so that
                # the error isn't a Permission Denied when it should be
                # a Does Not Exist.
                pass

        return True

    def has_modify_permissions(self, request, obj, *args, **kwargs):
        """Return whether the user can modify the object.

        This is used for HTTP PUT requests on the item resource.

        Subclasses should override this to provide any specific access control
        needed for modifying items.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            obj (object):
                The object to check for permissions.

            *args (tuple):
                Additional positional arguments passed to the view.

            **kwargs (dict):
                Keyword arguments representing values captured from the URL.

        Returns:
            bool:
            ``True`` if the user has modify permissions. ``False`` if it
            does not.
        """
        return False

    def has_delete_permissions(self, request, obj, *args, **kwargs):
        """Return whether the user can delete this object.

        This is used for HTTP DELETE requests on the list resource.

        Subclasses should override this to provide any specific access control
        needed for deleting items.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            obj (object):
                The object to check for permissions.

            *args (tuple):
                Additional positional arguments passed to the view.

            **kwargs (dict):
                Keyword arguments representing values captured from the URL.

        Returns:
            bool:
            ``True`` if the user has delete permissions. ``False`` if it
            does not.
        """
        return False

    def get_link_serializer(self, field):
        """Return the function to use for serializing a link field.

        This will first look for a function named
        :samp:`serialize_{field}_link` on the resource. If not available or
        not callable, :py:attr:`serialize_link` will be returned.

        Args:
            field (str):
                The field in the resource for which to generate a link.

        Returns:
            callable:
            The link serializer function.
        """
        serialize_link_func = getattr(self, 'serialize_%s_link' % field,
                                      None)

        if not serialize_link_func or not callable(serialize_link_func):
            serialize_link_func = self.serialize_link

        return serialize_link_func

    def serialize_link(self, obj, *args, **kwargs):
        """Return a serialized dictionary for a link.

        This will find the resource serializer for a given object and
        return a dictionary containing information on the link.

        Args:
            obj (object):
                The object being linked to.

            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple):
                Positional arguments passed to the view.

            **kwargs (dict):
                Keyword arguments representing values captured from the URL.

        Returns:
            dict:
            The serialized link information.
        """
        resource = self.get_serializer_for_object(obj)
        assert resource

        return {
            'method': 'GET',
            'href': resource.get_href(obj, *args, **kwargs),
            'title': resource.get_object_title(obj, *args, **kwargs),
        }

    def get_object_title(self, obj, request=None, *args, **kwargs):
        """Return an object's title.

        This is called when generating a link to an object's resource.

        By default, this returns the object's string representation.
        Subclasses can override this to return a different title.

        Args:
            obj (object):
                The object for which to generate a title.

            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Keyword arguments representing values captured from the URL.

        Returns:
            str:
            The object's title.
        """
        return str(obj)

    def serialize_object(self, obj, *args, **kwargs):
        """Return a serialized representation of an object.

        This will generate a dictionary containing information on an object,
        based on the API resource serializer registered for the object type.

        By default, the result will contain each field specified in
        :py:attr:`fields`, and any links to related resources in a ``links``
        key.

        This also takes care of expanding any links into object payloads
        in the list of fields when passing a field name to ``?expand=`` (for
        HTTP GET) or ``expand=`` in the body (for POST or PUT).

        Args:
            obj (object):
                The object to serialize.

            *args (tuple):
                Positional arguments passed to the view.

            request (django.http.HttpRequest, optional):
                The HTTP request from the client.

                This can be ``None``.

            **kwargs (dict):
                Keyword arguments representing values captured from the URL.

        Returns:
            dict:
            The serialized object payload.
        """
        request = kwargs.get('request', None)

        if request:
            if not hasattr(request, '_djblets_webapi_serialize_cache'):
                request._djblets_webapi_serialize_cache = {}

            if obj in request._djblets_webapi_serialize_cache:
                return self._clone_serialized_object(
                    request._djblets_webapi_serialize_cache[obj])

        only_fields = self.get_only_fields(request)
        only_links = self.get_only_links(request)

        data = {}
        links = {}
        expand_info = {}

        if only_links != []:
            links = self.get_links(self.item_child_resources, obj,
                                   *args, **kwargs)

        if hasattr(request, '_djblets_webapi_expanded_resources'):
            # We're nested at least one level down. We'll be operating off of
            # a possible subset of any specified expanded resources. Fields
            # that were handled by a parent resource won't be handled here.
            expanded_resources = request._djblets_webapi_expanded_resources
        else:
            expanded_resources = set(
                request.GET.get('expand', request.POST.get('expand', ''))
                .split(',')
            )
            request._djblets_webapi_expanded_resources = expanded_resources

        if expanded_resources:
            requested_mimetype = get_http_requested_mimetype(
                request, WebAPIResponse.supported_mimetypes)
        else:
            requested_mimetype = None

        # Make a copy of the set of expanded resources. We'll be temporarily
        # removing items as we recurse down into any nested objects, to
        # prevent infinite loops. We'll want to make sure we don't
        # permanently remove these entries, or subsequent list items will
        # be affected.
        orig_expanded_resources = expanded_resources.copy()

        if expanded_resources:
            # Make sure that any given field expansion only applies once,
            # starting at this level. This prevents infinite recursion in the
            # case where there's a loop in the object graph.
            #
            # We'll be restoring these values once we're done serializing
            # this object and its children.
            child_expanded_resources = expanded_resources.copy()

            for field in self.fields.keys():
                if field in expanded_resources:
                    child_expanded_resources.remove(field)

                    if not child_expanded_resources:
                        break

            # If we have any left...
            if child_expanded_resources:
                for resource in self.item_child_resources:
                    if resource.name in child_expanded_resources:
                        child_expanded_resources.remove(resource.name)

                    if resource.name_plural in child_expanded_resources:
                        child_expanded_resources.remove(resource.name_plural)

                    if not child_expanded_resources:
                        break

            request._djblets_webapi_expanded_resources = \
                child_expanded_resources

        for field in self.fields.keys():
            can_include_field = only_fields is None or field in only_fields
            expand_field = field in expanded_resources

            # If we're limiting fields and this one isn't explicitly included,
            # then we're only going to want to process it if there's a chance
            # it'll be linked (as opposed to being expanded).
            if not can_include_field and expand_field:
                continue

            serialize_func = getattr(self, "serialize_%s_field" % field, None)

            if serialize_func and callable(serialize_func):
                value = serialize_func(obj, request=request)
            else:
                value = getattr(obj, field)

                if isinstance(value, models.Manager):
                    if not can_include_field:
                        # This field isn't a single Model, so it can't be
                        # linked below. We can safely bail now before talking
                        # to the database.
                        continue

                    value = value.all()
                elif isinstance(value, models.ForeignKey):
                    value = value.get()

            if isinstance(value, models.Model) and not expand_field:
                serialize_link_func = self.get_link_serializer(field)

                links[field] = serialize_link_func(value, *args, **kwargs)
            elif can_include_field:
                if isinstance(value, QuerySet) and not expand_field:
                    serialize_link_func = self.get_link_serializer(field)

                    data[field] = [
                        serialize_link_func(o, *args, **kwargs)
                        for o in value
                    ]
                elif isinstance(value, QuerySet):
                    objects = list(value)

                    if objects:
                        resource = self.get_serializer_for_object(objects[0])

                        expand_info[field] = {
                            'item_mimetype': resource._build_resource_mimetype(
                                mimetype=requested_mimetype,
                                is_list=False),
                        }

                        data[field] = [
                            resource.serialize_object(o, *args, **kwargs)
                            for o in objects
                        ]
                    else:
                        data[field] = []
                elif isinstance(value, models.Model):
                    resource = self.get_serializer_for_object(value)

                    expand_info[field] = {
                        'item_mimetype': resource._build_resource_mimetype(
                            mimetype=requested_mimetype,
                            is_list=False),
                    }

                    data[field] = resource.serialize_object(
                        value, *args, **kwargs)
                else:
                    data[field] = value

        for resource_name in expanded_resources:
            if (resource_name not in links or
                (only_fields is not None and
                 resource_name not in only_fields)):
                continue

            # Try to find the resource from the child list.
            found = False

            for resource in self.item_child_resources:
                if resource_name in [resource.name, resource.name_plural]:
                    found = True
                    break

            if not found or not resource.model:
                continue

            extra_kwargs = {
                self.uri_object_key: getattr(obj, self.model_object_key),
            }
            extra_kwargs.update(**kwargs)
            extra_kwargs.update(self.get_href_parent_ids(obj, **kwargs))

            data[resource_name] = [
                resource.serialize_object(o, *args, **kwargs)
                for o in resource._get_queryset(
                    is_list=True, *args, **extra_kwargs)
            ]

            expand_info[resource_name] = {
                'list_url': links[resource_name]['href'],
                'list_mimetype': resource._build_resource_mimetype(
                    mimetype=requested_mimetype,
                    is_list=True),
                'item_mimetype': resource._build_resource_mimetype(
                    mimetype=requested_mimetype,
                    is_list=False),
            }

            del links[resource_name]

        if only_links is None:
            data['links'] = links
        elif only_links != []:
            data['links'] = dict([
                (link_name, link_info)
                for link_name, link_info in links.items()
                if link_name in only_links
            ])

        if expand_info:
            data['_expanded'] = expand_info

        # Now that we're done serializing, restore the list of expanded
        # resource for the next call.
        request._djblets_webapi_expanded_resources = orig_expanded_resources

        if request:
            request._djblets_webapi_serialize_cache[obj] = \
                self._clone_serialized_object(data)

        return data

    def get_only_fields(self, request):
        """Return the list of the only fields that the payload should include.

        If the user has requested that no fields should be provided, this
        will return an empty list.

        If all fields will be included in the payload, this will return None.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

        Returns:
            list of str:
            The list of fields, an empty list, or ``None``.
        """
        return self._get_only_items(request, 'only-fields', 'only_fields')

    def get_only_links(self, request):
        """Return the list of the only links that the payload should include.

        If the user has requested that no links should be provided, this
        will return an empty list.

        If all links will be included in the payload, this will return None.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

        Returns:
            list of str:
            The list of links, an empty list, or ``None``.
        """
        return self._get_only_items(request, 'only-links', 'only_links')

    def get_serializer_for_object(self, obj):
        """Return the serializer used to serialize an object.

        This is called when serializing objects for payloads returned
        by this resource instance. It must return the resource instance
        that will be responsible for serializing the given object for the
        payload.

        By default, this calls :py:func:`djblets.webapi.resources.registry.
        get_resource_for_object` to find the appropriate resource.

        Args:
            obj (object):
                The object to serialize.

        Returns:
            WebAPIResource:
            The resource handling serialization, or ``None`` if not found.
        """
        return get_resource_for_object(obj)

    def get_links(self, resources=[], obj=None, request=None,
                  *args, **kwargs):
        """Return a dictionary of links coming off this resource.

        The resulting links will point to the resources passed in
        ``resources``, and will also provide special resources for
        ``self`` (which points back to the official location for this
        resource) and one per HTTP method/operation allowed on this
        resource.

        Args:
            resources (list of WebAPIResource, optional):
                A list of resources for which to generate additional links.

            obj (object, optional):
                The object being serialized, for use as a base for resource
                URLs.

            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple):
                Additional positional arguments passed to the view.

            **kwargs (dict):
                Keyword arguments representing values captured from the URL.

        Returns:
            dict:
            A dictionary of link names to link information.
        """
        links = {}
        base_href = None

        if obj:
            base_href = self.get_href(obj, request, *args, **kwargs)

        if not base_href:
            # We may have received None from the URL above.
            if request:
                base_href = request.build_absolute_uri()
            else:
                base_href = ''

        links['self'] = {
            'method': 'GET',
            'href': base_href,
        }

        # base_href without any query arguments.
        i = base_href.find('?')

        if i != -1:
            clean_base_href = base_href[:i]
        else:
            clean_base_href = base_href

        if 'POST' in self.allowed_methods and not obj:
            links['create'] = {
                'method': 'POST',
                'href': clean_base_href,
            }

        if 'PUT' in self.allowed_methods and obj:
            links['update'] = {
                'method': 'PUT',
                'href': clean_base_href,
            }

        if 'DELETE' in self.allowed_methods and obj:
            links['delete'] = {
                'method': 'DELETE',
                'href': clean_base_href,
            }

        for resource in resources:
            links[resource.link_name] = {
                'method': 'GET',
                'href': '%s%s/' % (clean_base_href, resource.uri_name),
            }

        related_links = self.get_related_links(obj, request, *args, **kwargs)

        for key, info in related_links.items():
            links[key] = {
                'method': info['method'],
                'href': info['href'],
            }

            if 'title' in info:
                links[key]['title'] = info['title']

        return links

    def get_related_links(self, obj=None, request=None, *args, **kwargs):
        """Return links related to this resource.

        The result should be a dictionary of link names to a dictionary of
        information. See
        :py:class:`djblets.webapi.responses.WebAPIResponseLink` for the
        available keys for each link.

        Args:
            obj (object, optional):
                The object that the resources will be related to.

            request (django.http.HttpRequest, optional):
                The HTTP request from the client.

            *args (tuple):
                Positional arguments passed to the view.

            **kwargs (tuple):
                Keyword arguments representing values captured from the URL.

        Returns:
            djblets.webapi.responses.WebAPIResponseLinks:
            The dictionary of related links.
        """
        return {}

    def get_href(self, obj, request, *args, **kwargs):
        """Return the absolute URL for an object.

        This will attempt to build a URL that points to the object's item
        resource.

        If :py:attr:`uri_object_key` is set, this will call
        :py:meth:`get_item_url`, passing the model's key (defined as
        :py:attr:`model_object_key`) as :py:attr:`uri_object_key`, along with
        any parent IDs returned from :py:meth:`get_href_parent_ids`.

        Args:
            obj (object):
                The object being linked to.

            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple):
                Positional arguments passed to the view.

            **kwargs (dict):
                Keyword arguments representing values captured from the URL.

                These will be passed to :py:meth:`get_href_parent_ids`.

        Returns:
            str:
            The resulting URL to the object, or ``None`` if it could not be
            generated.
        """
        if not self.uri_object_key:
            return None

        href_kwargs = {
            self.uri_object_key: getattr(obj, self.model_object_key),
        }
        href_kwargs.update(self.get_href_parent_ids(obj, **kwargs))

        return self.get_item_url(request=request, **href_kwargs)

    def get_list_url(self, **kwargs):
        """Return the absolute URL to the list version of this resource.

        This will generate a URL for the list resource, given the provided
        arguments for the URL pattern.

        By default, this calls :py:meth:`build_resource_url` with
        :py:attr:`name_plural` and the provided keyword arguments.

        Args:
            **kwargs (dict):
                Keyword arguments representing values captured from the URL.

                These will be passed to :py:meth:`build_resource_url`.

        Returns:
            str:
            The resulting absolute URL to the list resource.
        """
        return self.build_resource_url(self.name_plural, **kwargs)

    def get_item_url(self, **kwargs):
        """Return the absolute URL to the item version of this resource.

        This will generate a URL for the item resource, given the provided
        arguments for the URL pattern.

        By default, this calls :py:meth:`build_resource_url` with
        :py:attr:`name` and the provided keyword arguments.

        Args:
            **kwargs (dict):
                Keyword arguments representing values captured from the URL.

                These will be passed to :py:meth:`build_resource_url`.

        Returns:
            str:
            The resulting absolute URL to the item resource.
        """
        return self.build_resource_url(self.name, **kwargs)

    def build_resource_url(self, name, request=None, **kwargs):
        """Build a resource URL for the given name and keyword arguments.

        This can be overridden by subclasses that have special requirements
        for URL resolution.

        Args:
            name (str):
                The name of the resource.

            request (django.http.HttpRequest):
                The HTTP request from the client.

            **kwargs (dict):
                Keyword arguments representing values captured from the URL.

                These will be passed to :py:meth:`_build_named_url`.

        Returns:
            str:
            The resulting absolute URL to the resource.
        """
        url = reverse(self._build_named_url(name), kwargs=kwargs)

        if request:
            url = request.build_absolute_uri(url)

        return url

    def get_href_parent_ids(self, obj, **kwargs):
        """Return a dictionary mapping parent object keys to object values.

        This will walk up the resource tree and return a mapping of parent
        URI object keys to values in the object instances. These are meant to
        be used to generate a full URL back to this resource.

        Each parent object's resource class will be used to handle that level
        of the tree. The resource's :py:attr:`model_parent_key` must be
        provided in order to process that level or higher in the tree.

        Args:
            obj (object):
                The object for which to return parent IDs.

            **kwargs (dict):
                Keyword arguments representing values captured from the URL.

        Returns:
            dict:
            A mapping of object IDs to values.
        """
        parent_ids = {}

        if self._parent_resource and self.model_parent_key:
            parent_obj = self.get_parent_object(obj)
            parent_ids = self._parent_resource.get_href_parent_ids(
                parent_obj, **kwargs)

            if self._parent_resource.uri_object_key:
                parent_ids[self._parent_resource.uri_object_key] = \
                    getattr(parent_obj, self._parent_resource.model_object_key)

        return parent_ids

    def get_parent_object(self, obj):
        """Return the parent of an object.

        By default, this uses :py:attr:`model_parent_key` to figure out the
        parent.

        Subclasses can override this for more complex behavior.

        Args:
            obj (object):
                The object for which to return a parent.

        Returns:
            object:
            The parent object, or ``None`` if not found.
        """
        parent_obj = getattr(obj, self.model_parent_key)

        if isinstance(parent_obj, (models.Manager, models.ForeignKey)):
            parent_obj = parent_obj.get()

        return parent_obj

    def get_last_modified(self, request, obj):
        """Return the last-modified timestamp of an object.

        By default, this uses :py:attr:`last_modified_field` to determine what
        field in the model represents the last-modified timestamp of the
        object.

        Subclasses can override this for more complex behavior.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            obj (object):
                The object for which to return a last-modified timestamp.

        Returns:
            datetime.datetime:
            The last-modified timestamp, or ``None`` if not found.
        """
        if self.last_modified_field:
            return getattr(obj, self.last_modified_field)

        return None

    def get_etag(self, request, obj, *args, **kwargs):
        """Return the ETag representing the state of the object.

        By default, this uses :py:attr:`etag_field` to determine what field in
        the model is unique enough to represent the state of the object.

        Subclasses can override this for more complex behavior. Any overridden
        functions should make sure to pass the result through
        :py:meth:`encode_etag` before returning a value.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            obj (object):
                The object for which to return an ETag.

            *args (tuple):
                Additional positional arguments passed to the view.

            **kwargs (dict):
                Keyword arguments representing values captured from the URL.

        Returns:
            str:
            The resulting encoded ETag, or ``None`` if one could not be
            generated.
        """
        if self.etag_field:
            return self.encode_etag(
                request,
                str(getattr(obj, self.etag_field)))

        return None

    def encode_etag(self, request, etag, *args, **kwargs):
        """Return an encoded ETag for usage in a header.

        This will take a precomputed ETag, augment it with additional
        information, encode it as a SHA1, and return it.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            etag (str):
                The ETag to encode.

            *args (tuple, unused):
                Additional positional arguments passed to the view.

            **kwargs (dict, unused):
                Keyword arguments representing values captured from the URL.

        Returns:
            str:
            The encoded ETag.
        """
        return encode_etag('%s:%s' % (request.user.username, etag))

    def are_cache_headers_current(self, request, last_modified=None,
                                  etag=None):
        """Return whether cache headers from the client are current.

        This will compare the optionally-provided timestamp and ETag against
        any conditional cache headers sent by the client to determine if
        the headers are current. If they are, the caller can return
        :py:class:`~django.http.HttpResponseNotModified` instead of a payload.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            last_modified (datetime.datetime, optional):
                The current last-modified timestamp for the object, if
                available.

            etag (str, optional):
                The current ETag for the payload, if available.

        Returns:
            bool:
            ``True`` if the client's cache headers represent a current version
            of the resource payload. ``False`` if they do not.
        """
        return ((last_modified and
                 get_modified_since(request, last_modified)) or
                (etag and etag_if_none_match(request, etag)))

    def get_no_access_error(self, request, *args, **kwargs):

        """Return an appropriate error when access is denied.

        By default, this will return :py:data:`~djblets.webapi.errors.
        PERMISSION_DENIED` if the user is logged in, and
        :py:data:`~djblets.webapi.errors.NOT_LOGGED_IN` if the user is
        anonymous.

        Subclasses can override this to return different or more detailed
        errors.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple, unused):
                Additional positional arguments passed to the view.

            **kwargs (dict, unused):
                Keyword arguments representing values captured from the URL.

        Returns:
            djblets.webapi.errors.WebAPIError:
            The API error to send to the client.
        """
        if request.user.is_authenticated:
            logger.warning('%s %s: user %s does not have '
                           'permission to access this resource.',
                           request.method, request.path,
                           request.user.username,
                           extra={'request': request})
            return PERMISSION_DENIED
        else:
            return NOT_LOGGED_IN

    def _build_resource_mimetype(self, mimetype, is_list):
        """Return a mimetype with vendor, list, and resource information.

        The resulting mimetype will be based on the provided mimetype,
        :py:attr:`mimetype_vendor`, :py:attr:`mimetype_list_resource_name`,
        and :py:attr:`mimetype_item_resource_name`.

        List mimetypes will be in the form of
        :samp:`{category}/vnd.{vendor}.{list-name}+{format}`.

        Item mimetypes will be in the form of
        :samp:`{category}/vnd.{vendor}.{item-name}+{format}`.

        Args:
            mimetype (str):
                The base mimetype used for building the resource mimetype.

            is_list (bool):
                Whether to build a list mimetype instead of an item mimetype.

        Returns:
            str:
            The resulting mimetype.
        """
        if is_list:
            resource_name = (self.mimetype_list_resource_name or
                             self.name_plural.replace('_', '-'))
        else:
            resource_name = (self.mimetype_item_resource_name or
                             self.name.replace('_', '-'))

        return self._build_vendor_mimetype(mimetype, resource_name)

    def _build_error_mimetype(self, request):
        """Return a mimetype used for errors.

        The mimetype will be based off the mimetype requested for this
        resource.  The resulting mimetype will be in the form of
        :samp:`{category}/vnd.{vendor}.error+{format}`.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

        Returns:
            str:
            The resulting error mimetype, or ``None`` if a requested mimetype
            required for this error could not be found.
        """
        mimetype = get_http_requested_mimetype(
            request, WebAPIResponse.supported_mimetypes)

        if self.mimetype_vendor:
            mimetype = self._build_vendor_mimetype(mimetype, 'error')

        return mimetype

    def _build_vendor_mimetype(self, mimetype, name):
        """Return a mimetype with vendor information.

        This will take a mimetype and return a version that includes vendor
        information, based on :py:attr:`mimetype_vendor`.

        For a mimetype of :samp:`{category}/{format}`, the resulting mimetype
        will be in the form of :samp:`{category}/vnd.{vendor}.{name}+{format}`.

        Args:
            mimetype (str):
                The original mimetype to convert to a vendor mimetype.

            name (str):
                The name of the resource to include in the mimetype.

        Returns:
            str:
            The resulting mimetype.
        """
        parts = mimetype.split('/')

        return '%s/vnd.%s.%s+%s' % (parts[0],
                                    self.mimetype_vendor,
                                    name,
                                    parts[1])

    def _build_named_url(self, name):
        """Return a Django URL name for a given resource.

        This will normalize the provided name and convert it into a Django
        URL name that can be used for building URL patterns or links.

        Args:
            name (str):
                The name of the resource to normalize and include.

        Returns:
            str:
            The resulting URL name.
        """
        return '%s-resource' % name.replace('_', '-')

    def _get_only_items(self, request, query_param_name, post_field_name):
        """Return a list of "only" items for filtering fields or links.

        This will look up the provided names in the HTTP request, looking
        for a caller-provided list of names to return.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            query_param_name (str):
                The query parameter name used for HTTP GET requests.

            post_field_name (str):
                The field name used in POST/PUT request bodies.
        """
        if request:
            only = request.GET.get(query_param_name,
                                   request.POST.get(post_field_name, None))

            if only is not None:
                if only:
                    return only.split(',')
                else:
                    return []

        return None

    def _get_queryset(self, request, is_list=False, *args, **kwargs):
        """Return an optimized queryset for looking up objects.

        This wraps :py:meth:`get_queryset` and then optimizes the returned
        queryset to help fetch related objects more efficiently.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            is_list (bool, optional):
                Whether the caller is querying for use in a list resource.

            *args (tuple, unused):
                Additional positional arguments passed to the view.

            **kwargs (dict, unused):
                Keyword arguments representing values captured from the URL.

        Returns:
            django.db.models.QuerySet:
            The resulting optimized queryset.
        """
        queryset = self.get_queryset(request, is_list=is_list, *args, **kwargs)

        if not hasattr(self, '_select_related_fields'):
            self._select_related_fields = []

            for field in self.fields.keys():
                if hasattr(self, 'serialize_%s_field' % field):
                    continue

                field_type = getattr(self.model, field, None)

                if field_type and isinstance(field_type, fkey_descriptors):
                    self._select_related_fields.append(field)

        if self._select_related_fields:
            queryset = \
                queryset.select_related(*self._select_related_fields)

        if is_list:
            if not hasattr(self, '_prefetch_related_fields'):
                self._prefetch_related_fields = []

                for field in self.fields.keys():
                    if hasattr(self, 'serialize_%s_field' % field):
                        continue

                    field_type = getattr(self.model, field, None)

                    if field_type and isinstance(field_type, m2m_descriptors):
                        self._prefetch_related_fields.append(field)

            if self._prefetch_related_fields:
                queryset = \
                    queryset.prefetch_related(*self._prefetch_related_fields)

        return queryset

    def _clone_serialized_object(self, obj):
        """Clone a serialized object, for storing in the cache.

        This works similarly to :py:func:`copy.deepcopy`, but is smart enough
        to only copy primitive types (dictionaries, lists, etc.) and won't
        interfere with model instances.

        :py:func:`~copy.deepcopy` should be smart enough to do that, and is
        documented as being smart enough, but Django models provide some
        functions that cause it to dig in further than it should, eventually
        breaking in some cases.

        If you want the job done right, do it yourself.

        Args:
            obj (object):
                The object to serialize and clone.

        Returns:
            object:
            The resulting cloned object.
        """
        if isinstance(obj, dict):
            return dict(
                (key, self._clone_serialized_object(value))
                for key, value in obj.items()
            )
        elif isinstance(obj, list):
            return [
                self._clone_serialized_object(value)
                for value in obj
            ]
        else:
            return obj
