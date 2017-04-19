"""Base class for a resource in an API."""

from __future__ import unicode_literals

import logging
import warnings

from django.conf.urls import include, patterns, url
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models.fields.related import (
    ManyRelatedObjectsDescriptor,
    ReverseManyRelatedObjectsDescriptor,
    ReverseSingleRelatedObjectDescriptor)
from django.db.models.query import QuerySet
from django.http import (HttpResponseNotAllowed, HttpResponse,
                         HttpResponseNotModified)
from django.utils import six
from django.views.decorators.vary import vary_on_headers

from djblets.util.http import (get_modified_since, encode_etag,
                               etag_if_none_match,
                               set_last_modified, set_etag,
                               get_http_requested_mimetype)
from djblets.urls.patterns import never_cache_patterns
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
                                   WebAPIError)


logger = logging.getLogger(__name__)


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

    # Configuration
    model = None
    fields = {}
    uri_object_key_regex = r'[0-9]+'
    uri_object_key = None
    model_object_key = 'pk'
    model_parent_key = None
    last_modified_field = None
    etag_field = None
    autogenerate_etags = False
    singleton = False
    list_child_resources = []
    item_child_resources = []
    allowed_methods = ('GET',)
    mimetype_vendor = None
    mimetype_list_resource_name = None
    mimetype_item_resource_name = None
    allowed_mimetypes = [
        {'list': mime, 'item': mime}
        for mime in WebAPIResponse.supported_mimetypes
    ]

    #: The class to use for paginated results in get_list.
    paginated_cls = WebAPIResponsePaginated

    # State
    method_mapping = {
        'GET': 'get',
        'POST': 'post',
        'PUT': 'put',
        'DELETE': 'delete',
    }

    _parent_resource = None
    _mimetypes_cache = None

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
        """Invokes the correct HTTP handler based on the type of request."""
        if not hasattr(request, '_djblets_webapi_object_cache'):
            request._djblets_webapi_object_cache = {}

        auth_result = check_login(request)

        if isinstance(auth_result, tuple):
            auth_success, auth_message, auth_headers = auth_result

            if not auth_success:
                err = LOGIN_FAILED

                if auth_message:
                    err = err.with_message(auth_message)

                return WebAPIResponseError(
                    request,
                    err=err,
                    headers=auth_headers or {},
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

        if view and six.callable(view):
            result = self.call_method_view(
                request, method, view, api_format=api_format, *args, **kwargs)

            if isinstance(result, WebAPIResponse):
                return result
            elif isinstance(result, WebAPIError):
                return WebAPIResponseError(
                    request,
                    err=result,
                    api_format=api_format,
                    mimetype=self._build_error_mimetype(request))
            elif isinstance(result, tuple):
                headers = {}

                if method == 'GET':
                    request_params = request.GET
                else:
                    request_params = request.POST

                if len(result) == 3:
                    headers = result[2]

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
                    return WebAPIResponseError(
                        request,
                        err=result[0],
                        headers=headers,
                        extra_params=result[1],
                        api_format=api_format,
                        mimetype=self._build_error_mimetype(request))
                else:
                    response_args = self.build_response_args(request)
                    headers.update(response_args.pop('headers', {}))
                    return WebAPIResponse(
                        request,
                        status=result[0],
                        obj=result[1],
                        headers=headers,
                        api_format=api_format,
                        encoder_kwargs=dict({
                            'calling_resource': self,
                        }, **kwargs),
                        **response_args)
            elif isinstance(result, HttpResponse):
                return result
            else:
                raise AssertionError(result)
        else:
            return HttpResponseNotAllowed(self.allowed_methods)

    def call_method_view(self, request, method, view, *args, **kwargs):
        """Calls the given method view.

        This will just call the given view by default, passing in all
        args and kwargs.

        This can be overridden by subclasses to perform additional
        checks or pass additional data to the view.
        """
        return view(request, *args, **kwargs)

    @property
    def __name__(self):
        return self.__class__.__name__

    @property
    def name(self):
        """Returns the name of the object, used for keys in the payloads."""
        if not hasattr(self, '_name'):
            if self.model:
                self._name = self.model.__name__.lower()
            else:
                self._name = self.__name__.lower()

        return self._name

    @property
    def name_plural(self):
        """Returns the plural name of the object, used for lists."""
        if not hasattr(self, '_name_plural'):
            if self.singleton:
                self._name_plural = self.name
            else:
                self._name_plural = self.name + 's'

        return self._name_plural

    @property
    def item_result_key(self):
        """Returns the key for single objects in the payload."""
        return self.name

    @property
    def list_result_key(self):
        """Returns the key for lists of objects in the payload."""
        return self.name_plural

    @property
    def uri_name(self):
        """Returns the name of the resource in the URI.

        This can be overridden when the name in the URI needs to differ
        from the name used for the resource.
        """
        return self.name_plural.replace('_', '-')

    @property
    def link_name(self):
        """Returns the name of the resource for use in a link.

        This can be overridden when the name in the link needs to differ
        from the name used for the resource.
        """
        return self.name_plural

    def _build_resource_mimetype(self, mimetype, is_list):
        if is_list:
            resource_name = (self.mimetype_list_resource_name or
                             self.name_plural.replace('_', '-'))
        else:
            resource_name = (self.mimetype_item_resource_name or
                             self.name.replace('_', '-'))

        return self._build_vendor_mimetype(mimetype, resource_name)

    def _build_error_mimetype(self, request):
        mimetype = get_http_requested_mimetype(
            request, WebAPIResponse.supported_mimetypes)

        if self.mimetype_vendor:
            mimetype = self._build_vendor_mimetype(mimetype, 'error')

        return mimetype

    def _build_vendor_mimetype(self, mimetype, name):
        parts = mimetype.split('/')

        return '%s/vnd.%s.%s+%s' % (parts[0],
                                    self.mimetype_vendor,
                                    name,
                                    parts[1])

    def build_response_args(self, request):
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
        """Returns an object, given captured parameters from a URL.

        This will perform a query for the object, taking into account
        ``model_object_key``, ``uri_object_key``, and any captured parameters
        from the URL.

        This requires that ``model`` and ``uri_object_key`` be set.

        Throws django.core.exceptions.ObjectDoesNotExist if the requested
        object does not exist.
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
        """Handles HTTP POSTs.

        This is not meant to be overridden unless there are specific needs.

        This will invoke ``create`` if doing an HTTP POST on a list resource.

        By default, an HTTP POST is not allowed on individual object
        resourcces.
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
        """Handles HTTP PUTs.

        This is not meant to be overridden unless there are specific needs.

        This will just invoke ``update``.
        """
        return self.update(request, *args, **kwargs)

    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    def get(self, request, api_format, *args, **kwargs):
        """Handles HTTP GETs to individual object resources.

        By default, this will check for access permissions and query for
        the object. It will then return a serialized form of the object.

        This may need to be overridden if needing more complex logic.
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
            return HttpResponseNotModified()

        data = {
            self.item_result_key: self.serialize_object(obj, request=request,
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
                'type': int,
                'description': 'The 0-based index of the first result in '
                               'the list. The start index is usually the '
                               'previous start index plus the number of '
                               'previous results. By default, this is 0.',
            },
            'max-results': {
                'type': int,
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
        """Handles HTTP GETs to list resources.

        By default, this will query for a list of objects and return the
        list in a serialized form.
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
        """Handles HTTP POST requests to list resources.

        This is used to create a new object on the list, given the
        data provided in the request. It should usually return
        HTTP 201 Created upon success.

        By default, this returns HTTP 405 Method Not Allowed.
        """
        return HttpResponseNotAllowed(self.allowed_methods)

    @webapi_login_required
    def update(self, request, api_format, *args, **kwargs):
        """Handles HTTP PUT requests to object resources.

        This is used to update an object, given full or partial data provided
        in the request. It should usually return HTTP 200 OK upon success.

        By default, this returns HTTP 405 Method Not Allowed.
        """
        return HttpResponseNotAllowed(self.allowed_methods)

    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    def delete(self, request, api_format, *args, **kwargs):
        """Handles HTTP DELETE requests to object resources.

        This is used to delete an object, if the user has permissions to
        do so.

        By default, this deletes the object and returns HTTP 204 No Content.
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
        """Returns a queryset used for querying objects or lists of objects.

        Throws django.core.exceptions.ObjectDoesNotExist if the requested
        object does not exist.

        This can be overridden to filter the object list, such as for hiding
        non-public objects.

        The ``is_list`` parameter can be used to specialize the query based
        on whether an individual object or a list of objects is being queried.
        """
        return self.model.objects.all()

    def get_url_patterns(self):
        """Returns the Django URL patterns for this object and its children.

        This is used to automatically build up the URL hierarchy for all
        objects. Projects should call this for top-level resources and
        return them in the ``urls.py`` files.
        """
        urlpatterns = never_cache_patterns(
            '',
            url(r'^$', self, name=self._build_named_url(self.name_plural)),
        )

        for resource in self.list_child_resources:
            resource._parent_resource = self
            child_regex = r'^' + resource.uri_name + r'/'
            urlpatterns += patterns(
                '',
                url(child_regex, include(resource.get_url_patterns())),
            )

        if self.uri_object_key or self.singleton:
            # If the resource has particular items in it...
            if self.uri_object_key:
                base_regex = r'^(?P<%s>%s)/' % (self.uri_object_key,
                                                self.uri_object_key_regex)
            elif self.singleton:
                base_regex = r'^'

            urlpatterns += never_cache_patterns(
                '',
                url(base_regex + r'$', self,
                    name=self._build_named_url(self.name))
            )

            for resource in self.item_child_resources:
                resource._parent_resource = self
                child_regex = base_regex + resource.uri_name + r'/'
                urlpatterns += patterns(
                    '',
                    url(child_regex, include(resource.get_url_patterns())),
                )

        return urlpatterns

    def has_access_permissions(self, request, obj, *args, **kwargs):
        """Returns whether or not the user has read access to this object."""
        return True

    def has_list_access_permissions(self, request, *args, **kwargs):
        """Returns whether or not the user has read access to this list."""
        if self._parent_resource and self.model_parent_key:
            try:
                parent_obj = self._parent_resource.get_object(
                    request, *args, **kwargs)

                return self._parent_resource.has_access_permissions(
                    request, parent_obj, *args, **kwargs)
            except:
                # Other errors, like Does Not Exist, should be caught
                # separately. As of here, we'll allow it to pass, so that
                # the error isn't a Permission Denied when it should be
                # a Does Not Exist.
                pass

        return True

    def has_modify_permissions(self, request, obj, *args, **kwargs):
        """Returns whether or not the user can modify this object."""
        return False

    def has_delete_permissions(self, request, obj, *args, **kwargs):
        """Returns whether or not the user can delete this object."""
        return False

    def get_link_serializer(self, field):
        """Return the function to use for serializing a link field."""
        serialize_link_func = getattr(self, 'serialize_%s_link' % field,
                                      None)

        if not serialize_link_func or not six.callable(serialize_link_func):
            serialize_link_func = self.serialize_link

        return serialize_link_func

    def serialize_link(self, obj, *args, **kwargs):
        """Serialize a link to the object into a Python dictionary."""
        resource = self.get_serializer_for_object(obj)
        assert resource

        return {
            'method': 'GET',
            'href': resource.get_href(obj, *args, **kwargs),
            'title': six.text_type(obj),
        }

    def serialize_object(self, obj, *args, **kwargs):
        """Serializes the object into a Python dictionary."""
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

        if only_links != []:
            links = self.get_links(self.item_child_resources, obj,
                                   *args, **kwargs)

        if hasattr(request, '_djblets_webapi_expanded_resources'):
            expanded_resources = request._djblets_webapi_expanded_resources
        else:
            expand = request.GET.get('expand', request.POST.get('expand', ''))
            expanded_resources = expand.split(',')
            request._djblets_webapi_expanded_resources = expanded_resources

        # Make a copy of the list of expanded resources. We'll be temporarily
        # removing items as we recurse down into any nested objects, to
        # prevent infinite loops. We'll want to make sure we don't
        # permanently remove these entries, or subsequent list items will
        # be affected.
        orig_expanded_resources = list(expanded_resources)

        for field in six.iterkeys(self.fields):
            can_include_field = only_fields is None or field in only_fields
            expand_field = field in expanded_resources

            # If we're limiting fields and this one isn't explicitly included,
            # then we're only going to want to process it if there's a chance
            # it'll be linked (as opposed to being expanded).
            if not can_include_field and expand_field:
                continue

            serialize_func = getattr(self, "serialize_%s_field" % field, None)

            if serialize_func and six.callable(serialize_func):
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

            # Make sure that any given field expansion only applies once. This
            # prevents infinite recursion in the case where there's a loop in
            # the object graph.
            #
            # We'll be restoring these values once we're done serializing
            # objects.
            if expand_field:
                request._djblets_webapi_expanded_resources.remove(field)

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
                        data[field] = [
                            resource.serialize_object(o, *args, **kwargs)
                            for o in objects
                        ]
                    else:
                        data[field] = []
                elif isinstance(value, models.Model):
                    resource = self.get_serializer_for_object(value)
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

            del links[resource_name]

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

        if only_links is None:
            data['links'] = links
        elif only_links != []:
            data['links'] = dict([
                (link_name, link_info)
                for link_name, link_info in six.iteritems(links)
                if link_name in only_links
            ])

        # Now that we're done serializing, restore the list of expanded
        # resource for the next call.
        request._djblets_webapi_expanded_resources = orig_expanded_resources

        if request:
            request._djblets_webapi_serialize_cache[obj] = \
                self._clone_serialized_object(data)

        return data

    def get_only_fields(self, request):
        """Returns the list of the only fields that the payload should include.

        If the user has requested that no fields should be provided, this
        will return an empty list.

        If all fields will be included in the payload, this will return None.
        """
        return self._get_only_items(request, 'only-fields', 'only_fields')

    def get_only_links(self, request):
        """Returns the list of the only links that the payload should include.

        If the user has requested that no links should be provided, this
        will return an empty list.

        If all links will be included in the payload, this will return None.
        """
        return self._get_only_items(request, 'only-links', 'only_links')

    def _get_only_items(self, request, query_param_name, post_field_name):
        if request:
            only = request.GET.get(query_param_name,
                                   request.POST.get(post_field_name, None))

            if only is not None:
                if only:
                    return only.split(',')
                else:
                    return []

        return None

    def get_serializer_for_object(self, obj):
        """Returns the serializer used to serialize an object.

        This is called when serializing objects for payloads returned
        by this resource instance. It must return the resource instance
        that will be responsible for serializing the given object for the
        payload.

        By default, this calls ``get_resource_for_object`` to find the
        appropriate resource.
        """
        return get_resource_for_object(obj)

    def get_links(self, resources=[], obj=None, request=None,
                  *args, **kwargs):
        """Returns a dictionary of links coming off this resource.

        The resulting links will point to the resources passed in
        ``resources``, and will also provide special resources for
        ``self`` (which points back to the official location for this
        resource) and one per HTTP method/operation allowed on this
        resource.
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

        for key, info in six.iteritems(
                self.get_related_links(obj, request, *args, **kwargs)):
            links[key] = {
                'method': info['method'],
                'href': info['href'],
            }

            if 'title' in info:
                links[key]['title'] = info['title']

        return links

    def get_related_links(self, obj=None, request=None, *args, **kwargs):
        """Returns links related to this resource.

        The result should be a dictionary of link names to a dictionary of
        information. The information should contain:

        * 'method' - The HTTP method
        * 'href' - The URL
        * 'title' - The title of the link (optional)
        * 'resource' - The WebAPIResource instance
        * 'list-resource' - True if this links to a list resource (optional)
        """
        return {}

    def get_href(self, obj, request, *args, **kwargs):
        """Returns the URL for this object."""
        if not self.uri_object_key:
            return None

        href_kwargs = {
            self.uri_object_key: getattr(obj, self.model_object_key),
        }
        href_kwargs.update(self.get_href_parent_ids(obj, **kwargs))

        return self.get_item_url(request=request, **href_kwargs)

    def get_list_url(self, **kwargs):
        """Return the URL to the list version of this resource.

        This will generate a URL for the list resource, given the provided
        arguments for the URL pattern.

        Args:
            kwargs (dict): The keyword arguments needed for URL resolution.

        Returns:
            unicode: The resulting absolute URL to the list resource.
        """
        return self.build_resource_url(self.name_plural, **kwargs)

    def get_item_url(self, **kwargs):
        """Return the URL to the item version of this resource.

        This will generate a URL for the item resource, given the provided
        arguments for the URL pattern.

        Args:
            kwargs (dict): The keyword arguments needed for URL resolution.

        Returns:
            unicode: The resulting absolute URL to the item resource.
        """
        return self.build_resource_url(self.name, **kwargs)

    def build_resource_url(self, name, request=None, **kwargs):
        """Build a resource URL for the given name and keyword arguments.

        This can be overridden by subclasses that have special requirements
        for URL resolution.

        Args:
            name (unicode):
                The name of the resource.

            request (HttpRequest):
                The HTTP request from the client.

            kwargs (dict):
                The keyword arguments needed for URL resolution.

        Returns:
            unicode: The resulting absolute URL to the resource.
        """
        url = reverse(self._build_named_url(name), kwargs=kwargs)

        if request:
            url = request.build_absolute_uri(url)

        return url

    def get_href_parent_ids(self, obj, **kwargs):
        """Returns a dictionary mapping parent object keys to their values for
        an object.
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
        """Returns the parent of an object.

        By default, this uses ``model_parent_key`` to figure out the parent,
        but it can be overridden for more complex behavior.
        """
        parent_obj = getattr(obj, self.model_parent_key)

        if isinstance(parent_obj, (models.Manager, models.ForeignKey)):
            parent_obj = parent_obj.get()

        return parent_obj

    def get_last_modified(self, request, obj):
        """Returns the last modified timestamp of an object.

        By default, this uses ``last_modified_field`` to determine what
        field in the model represents the last modified timestamp of
        the object.

        This can be overridden for more complex behavior.
        """
        if self.last_modified_field:
            return getattr(obj, self.last_modified_field)

        return None

    def get_etag(self, request, obj, *args, **kwargs):
        """Returns the ETag representing the state of the object.

        By default, this uses ``etag_field`` to determine what field in
        the model is unique enough to represent the state of the object.

        This can be overridden for more complex behavior. Any overridden
        functions should make sure to pass the result through
        ``encode_etag`` before returning a value.
        """
        if self.etag_field:
            etag = six.text_type(getattr(obj, self.etag_field))
        elif self.autogenerate_etags:
            etag = self.generate_etag(obj, self.fields, request=request,
                                      encode_etag=False, **kwargs)
        else:
            etag = None

        if etag:
            etag = self.encode_etag(request, etag)

        return etag

    def encode_etag(self, request, etag, *args, **kwargs):
        """Encodes an ETag for usage in a header.

        This will take a precomputed ETag, augment it with additional
        information, encode it as a SHA1, and return it.
        """
        return encode_etag('%s:%s' % (request.user.username, etag))

    def generate_etag(self, obj, fields, request, encode_etag=True, **kwargs):
        """Generates an ETag from the serialized values of all given fields.

        When called by legacy code, the resulting ETag will be encoded.
        All consumers are expected to update their get_etag() methods to
        call encode_etag() directly, and to pass encode_etag=False to this
        function.

        In a future version, the encode_etag parameter will go away, and
        this function's behavior will change to not return encoded ETags.
        """
        etag = repr(self.serialize_object(obj, request=request, **kwargs))

        # In Djblets 0.8.15, the responsibility for encoding moved to
        # get_etag(). However, legacy callers may end up calling
        # generate_etag, expecting the result to be encoded. In this case,
        # we want to perform the encoding and warn about deprecation.
        #
        # Future versions of Djblets will remove the encode_etag argument.
        if encode_etag:
            warnings.warn('WebAPIResource.generate_etag will stop generating '
                          'encoded ETags in 0.9.x. Update your get_etag() '
                          'method to pass encode_etag=False to this function '
                          'and to call encode_etag() on the result instead.',
                          DeprecationWarning)
            etag = self.encode_etag(request, etag)

        return etag

    def are_cache_headers_current(self, request, last_modified=None,
                                  etag=None):
        """Determines if cache headers from the client are current.

        This will compare the optionally-provided timestamp and ETag against
        any conditional cache headers sent by the client to determine if
        the headers are current. If they are, the caller can return
        HttpResponseNotModified instead of a payload.
        """
        return ((last_modified and
                 get_modified_since(request, last_modified)) or
                (etag and etag_if_none_match(request, etag)))

    def get_no_access_error(self, request, *args, **kwargs):
        """Returns an appropriate error when access is denied.

        By default, this will return PERMISSION_DENIED if the user is logged
        in, and NOT_LOGGED_IN if the user is anonymous.

        Subclasses can override this to return different or more detailed
        errors.
        """
        if request.user.is_authenticated():
            logger.warning('%s %s: user %s does not have '
                           'permission to access this resource.',
                           request.method, request.path,
                           request.user.username)
            return PERMISSION_DENIED
        else:
            return NOT_LOGGED_IN

    def _build_named_url(self, name):
        """Builds a Django URL name from the provided name."""
        return '%s-resource' % name.replace('_', '-')

    def _get_queryset(self, request, is_list=False, *args, **kwargs):
        """Returns an optimized queryset.

        This calls out to the resource's get_queryset(), and then performs
        some optimizations to better fetch related objects, reducing future
        lookups in this request.
        """
        queryset = self.get_queryset(request, is_list=is_list, *args, **kwargs)

        if not hasattr(self, '_select_related_fields'):
            self._select_related_fields = []

            for field in six.iterkeys(self.fields):
                if hasattr(self, 'serialize_%s_field' % field):
                    continue

                field_type = getattr(self.model, field, None)

                if (field_type and
                    isinstance(field_type,
                               ReverseSingleRelatedObjectDescriptor)):
                    self._select_related_fields.append(field)

        if self._select_related_fields:
            queryset = \
                queryset.select_related(*self._select_related_fields)

        if is_list:
            if not hasattr(self, '_prefetch_related_fields'):
                self._prefetch_related_fields = []

                for field in six.iterkeys(self.fields):
                    if hasattr(self, 'serialize_%s_field' % field):
                        continue

                    field_type = getattr(self.model, field, None)

                    if (field_type and
                        isinstance(field_type,
                                   (ReverseManyRelatedObjectsDescriptor,
                                    ManyRelatedObjectsDescriptor))):
                        self._prefetch_related_fields.append(field)

            if self._prefetch_related_fields:
                queryset = \
                    queryset.prefetch_related(*self._prefetch_related_fields)

        return queryset

    def _clone_serialized_object(self, obj):
        """Clone a serialized object, for storing in the cache.

        This works similarly to deepcopy(), but is smart enough to only
        copy primitive types (dictionaries, lists, etc.) and won't
        interfere with model instances.

        deepcopy() should be smart enough to do that, and is documented
        as being smart enough, but Django models provide some functions
        that cause deepcopy() to dig in further than it should, eventually
        breaking in some cases.

        If you want the job done right, do it yourself.
        """
        if isinstance(obj, dict):
            return dict(
                (key, self._clone_serialized_object(value))
                for key, value in six.iteritems(obj)
            )
        elif isinstance(obj, list):
            return [
                self._clone_serialized_object(value)
                for value in obj
            ]
        else:
            return obj
