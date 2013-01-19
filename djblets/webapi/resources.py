try:
    from hashlib import sha1
except ImportError:
    from sha import sha as sha1

from django.conf.urls.defaults import include, patterns, url
from django.contrib.auth.models import User, Group
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models.query import QuerySet
from django.http import HttpResponseNotAllowed, HttpResponse, \
                        HttpResponseNotModified
from django.views.decorators.vary import vary_on_headers

from djblets.util.decorators import augment_method_from
from djblets.util.http import get_modified_since, etag_if_none_match, \
                              set_last_modified, set_etag, \
                              get_http_requested_mimetype
from djblets.util.misc import never_cache_patterns
from djblets.webapi.auth import check_login
from djblets.webapi.core import WebAPIResponse, \
                                WebAPIResponseError, \
                                WebAPIResponsePaginated, \
                                SPECIAL_PARAMS
from djblets.webapi.decorators import webapi_login_required, \
                                      webapi_request_fields, \
                                      webapi_response_errors
from djblets.webapi.errors import DOES_NOT_EXIST, \
                                  NOT_LOGGED_IN, \
                                  PERMISSION_DENIED, \
                                  WebAPIError


_model_to_resources = {}
_name_to_resources = {}
_class_to_resources = {}


class WebAPIResource(object):
    """A resource living at a specific URL, representing an object or list
    of objects.

    A WebAPIResource is a RESTful resource living at a specific URL. It
    can represent either an object or a list of objects, and can respond
    to various HTTP methods (GET, POST, PUT, DELETE).

    Subclasses are expected to override functions and variables in order to
    provide specific functionality, such as modifying the resource or
    creating a new resource.


    Representing Models
    -------------------

    Most resources will have ``model`` set to a Model subclass, and
    ``fields`` set to list the fields that would be shown when

    Each resource will also include a ``link`` dictionary that maps
    a key (resource name or action) to a dictionary containing the URL
    (``href``) and the HTTP method that's to be used for that URL
    (``method``). This will include a special ``self`` key that links to
    that resource's actual location.

    An example of this might be::

       'links': {
           'self': {
               'method': 'GET',
               'href': '/path/to/this/resource/'
           },
           'update': {
               'method': 'PUT',
               'href': '/path/to/this/resource/'
           }
       }

    Resources associated with a model may want to override the ``get_queryset``
    function to return a queryset with a more specific query.

    By default, an individual object's key name in the resulting payloads
    will be set to the lowercase class name of the object, and the plural
    version used for lists will be the same but with 's' appended to it. This
    can be overridden by setting ``name`` and ``name_plural``.


    Matching Objects
    ----------------

    Objects are generally queried by their numeric object ID and mapping that
    to the object's ``pk`` attribute. For this to work, the ``uri_object_key``
    attribute must be set to the name in the regex for the URL that will
    be captured and passed to the handlers for this resource. The
    ``uri_object_key_regex`` attribute can be overridden to specify the
    regex for matching this ID (useful for capturing names instead of
    numeric IDs) and ``model_object_key`` can be overridden to specify the
    model field that will be matched against.


    Parents and URLs
    ----------------

    Resources typically have a parent resource, of which the resource is
    a subclass. Resources will often list their children (by setting
    ``list_child_resources`` and ``item_child_resources`` in a subclass
    to lists of other WebAPIResource instances). This makes the entire tree
    navigatable. The URLs are built up automatically, so long as the result
    of get_url_patterns() from top-level resources are added to the Django
    url_patterns variables commonly found in urls.py.

    Child objects should set the ``model_parent_key`` variable to the
    field name of the object's parent in the resource hierarchy. This
    allows WebAPIResource to build a URL with the right values filled in in
    order to make a URL to this object.

    If the parent is dynamic based on certain conditions, then the
    ``get_parent_object`` function can be overridden instead.


    Object Serialization
    --------------------

    Objects are serialized through the ``serialize_object`` function.
    This rarely needs to be overridden, but can be called from WebAPIEncoders
    in order to serialize the object. By default, this will loop through
    the ``fields`` variable and add each value to the resulting dictionary.

    Values can be specially serialized by creating functions in the form of
    ``serialize_<fieldname>_field``. These functions take the object being
    serialized and must return a value that can be fed to the encoder.


    Handling Requests
    -----------------

    WebAPIResource calls the following functions based on the type of
    HTTP request:

      * ``get`` - HTTP GET for individual objects.
      * ``get_list`` - HTTP GET for resources representing lists of objects.
      * ``create`` - HTTP POST on resources representing lists of objects.
                     This is expected to return the object and an HTTP
                     status of 201 CREATED, on success.
      * ``update`` - HTTP PUT on individual objects to modify their state
                     based on full or partial data.
      * ``delete`` - HTTP DELETE on an individual object. This is expected
                     to return a status of HTTP 204 No Content on success.
                     The default implementation just deletes the object.

    Any function that is not implemented will return an HTTP 405 Method
    Not Allowed. Functions that have handlers provided should set
    ``allowed_methods`` to a tuple of the HTTP methods allowed. For example::

        allowed_methods = ('GET', POST', 'DELETE')

    These functions are passed an HTTPRequest and a list of arguments
    captured in the URL and are expected to return standard HTTP response
    codes, along with a payload in most cases. The functions can return any of:

      * A HttpResponse
      * A WebAPIResponse
      * A WebAPIError
      * A tuple of (WebAPIError, Payload)
      * A tuple of (WebAPIError, Payload Dictionary, Headers Dictionary)
      * A tuple of (HTTP status, Payload)
      * A tuple of (HTTP status, Payload Dictionary, Headers Dictionary)

    In general, it's best to return one of the tuples containing an HTTP
    status, and not any object, but there are cases where an object is
    necessary.

    Commonly, a handler will need to fetch parent objects in order to make
    some request. The values for all captured object IDs in the URL are passed
    to the handler, but it's best to not use these directly. Instead, the
    handler should accept a **kwargs parameter, and then call the parent
    resource's ``get_object`` function and pass in that **kwargs. For example::

      def create(self, request, *args, **kwargs):
          try:
              my_parent = myParentResource.get_object(request, *args, **kwargs)
          except ObjectDoesNotExist:
              return DOES_NOT_EXIST


    Expanding Resources
    -------------------

    The resulting data returned from a resource will by default provide
    links to child resources. If a lot of aggregated data is needed, then
    instead of making several queries the caller can use the ``?expand=``
    parameter. This takes a comma-separated list of keys in the resource
    names found in the payloads and expands them instead of linking to them.

    This can result in really large downloads, if deep expansion is made
    when accessing lists of resources. However, it can also result in less
    strain on the server if used correctly.


    Faking HTTP Methods
    -------------------

    There are clients that can't actually request anything but HTTP POST
    and HTTP GET. An HTML form is one such example, and Flash applications
    are another. For these cases, an HTTP POST can be made, with a special
    ``_method`` parameter passed to the URL. This can be set to the HTTP
    method that's desired. For example, ``PUT`` or ``DELETE``.


    Permissions
    -----------

    Unless overridden, an object cannot be modified, created, or deleted
    if the user is not logged in and if an appropriate permission function
    does not return True. These permission functions are:

    * ``has_access_permissions`` - Used for HTTP GET calls. Returns True
                                   by default.
    * ``has_modify_permissions`` - Used for HTTP POST or PUT calls, if
                                   called by the subclass. Returns False
                                   by default.
    * ``has_delete_permissions`` - Used for HTTP DELETE permissions. Returns
                                   False by default.


    Browser Caching
    ---------------

    To improve performance, resources can make use of browser-side caching.
    If a resource is accessed more than once, and it hasn't changed,
    the resource will return an :http:`304`.

    There are two methods for caching: Last Modified headers, and ETags.

    Last Modified
    ~~~~~~~~~~~~~

    A resource can set ``last_modified_field`` to the name of a DateTimeField
    in the model. This will be used to determine if the resource has changed
    since the last request.

    If a bit more work is needed, the ``get_last_modified`` function
    can instead be overridden. This takes the request and object and is
    expected to return a timestamp.

    ETags
    ~~~~~

    ETags are arbitrary, unique strings that represent the state of a resource.
    There should only ever be one possible ETag per state of the resource.

    A resource can set the ``etag_field`` to the name of a field in the
    model.

    If no field really works, ``autogenerate_etags`` can be set. This will
    generate a suitable ETag based on all fields in the resource. For this
    to work correctly, no custom data can be added to the payload, and
    links cannot be dynamic.

    If more work is needed, the ``get_etag`` function can instead be
    overridden. It will take a request and object and is expected to return
    a string.


    Mimetypes
    ---------

    Resources should list the possible mimetypes they'll accept and return in
    :py:attr:`allowed_mimetypes`. Each entry in the list is a dictionary
    with 'list' containing a mimetype for resource lists, and 'item'
    containing the equivalent mimetype for a resource item. In the case of
    a singleton, 'item' will contain the mimetype. If the mimetype is not
    applicable to one of the resource forms, the corresponding entry
    should contain None.

    Entries in these lists are checked against the mimetypes requested in the
    HTTP Accept header, and, by default, the returned data will be sent in
    that mimetype. If the requested data is a resource list, the corresponding
    resource item mimetype will also be sent in the 'Item-Content-Type'
    header.

    By default, this lists will have entries with both 'list' and 'item'
    containing :mimetype:`application/json` and :mimetype:`application/xml`,
    along with any resource-specific mimetypes, if used.

    Resource-specific Mimetypes
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    In order to better identify resources, resources can provide their
    own custom mimetypes. These are known as vendor-specific mimetypes, and
    are subsets of :mimetype:`application/json` and :mimetype:`application/xml`.
    An example would be :mimetype:`application/vnd.example.com.myresource+json`.

    To enable this on a resource, set :py:attr:`mimetype_vendor` to the
    vendor name. This is often a domain name. For example::

        mimetype_vendor = 'djblets.org'

    The resource names will then be generated based on the name of the
    resource (:py:attr:`name_plural` for resource lists, :py:attr:`name` for
    resource items and singletons). These can be customized as well::

        mimetype_list_resource_name = 'myresource-list'
        mimetype_item_resource_name = 'myresource'

    When these are used, any client requesting either the resource-specific
    mimetype or the more generic mimetype will by default receive a payload
    with the resource-specific mimetype. This makes it easier to identify
    the schema of resource data without hard-coding any knowledge of the
    URI.
    """

    # Configuration
    model = None
    fields = {}
    uri_object_key_regex = '[0-9]+'
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
    allowed_list_mimetypes = list(WebAPIResponse.supported_mimetypes)
    allowed_item_mimetypes = list(WebAPIResponse.supported_mimetypes)
    allowed_mimetypes = [
        {'list': mime, 'item': mime}
        for mime in WebAPIResponse.supported_mimetypes
    ]

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

        # TODO: allowed_list_mimetypes and allowed_item_mimetypes
        # will be deprecated in version 0.7 of djblets. This code
        # maintains backwards compatibility for these lists while
        # code is moved to the new allowed_mimetypes attribute.
        # The following code block may be removed for version 0.7
        # to remove the backwards compatibility.
        item_mimetypes = []
        list_mimetypes = []

        # Copy this list, because otherwise we may modify the class-level version of it.
        self.allowed_mimetypes = list(self.allowed_mimetypes)

        for mime in self.allowed_mimetypes:
            item_mimetypes.append(mime['item'])
            list_mimetypes.append(mime['list'])

        for mimetype in self.allowed_item_mimetypes:
            if mimetype not in item_mimetypes:
                self.allowed_mimetypes.append({
                    'list': None,
                    'item': mimetype,
                })

        for mimetype in self.allowed_list_mimetypes:
            if mimetype not in list_mimetypes:
                self.allowed_mimetypes.append({
                    'list': mimetype,
                    'item': None,
                })

        if self.mimetype_vendor:
            self.allowed_item_mimetypes = list(self.allowed_item_mimetypes)
            self.allowed_list_mimetypes = list(self.allowed_list_mimetypes)

            # Add resource-specific versions of supported mimetypes
            for mimetypes, is_list in [(self.allowed_item_mimetypes, False),
                                       (self.allowed_list_mimetypes, True)]:
                for mimetype in WebAPIResponse.supported_mimetypes:
                    if mimetype in mimetypes:
                        mimetypes.append(
                            self._build_resource_mimetype(mimetype, is_list))
        # End of compatibility code.

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
                    if (mimetype_pair[key] in
                        WebAPIResponse.supported_mimetypes):
                        vend_mimetype_pair[key] = \
                            self._build_resource_mimetype(mimetype_pair[key],
                                                          is_list)

                if vend_mimetype_pair['list'] or vend_mimetype_pair['item']:
                    self.allowed_mimetypes.append(vend_mimetype_pair)

    @vary_on_headers('Accept', 'Cookie')
    def __call__(self, request, api_format=None, *args, **kwargs):
        """Invokes the correct HTTP handler based on the type of request."""
        check_login(request)

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
            # data, so they do not parse it. However, that gives us no clean way
            # of accessing the data. So we pretend it's POST for a second in
            # order to parse.
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
            result = view(request, api_format=api_format, *args, **kwargs)

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
                        **response_args)
            elif isinstance(result, HttpResponse):
                return result
            else:
                raise AssertionError(result)
        else:
            return HttpResponseNotAllowed(self.allowed_methods)

    @property
    def __name__(self):
        return self.__class__.__name__

    @property
    def name(self):
        """Returns the name of the object, used for keys in the payloads."""
        if self.model:
            return self.model.__name__.lower()
        else:
            return self.__name__.lower()

    @property
    def name_plural(self):
        """Returns the plural name of the object, used for lists."""
        if self.singleton:
            return self.name
        else:
            return self.name + 's'

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

    def _build_resource_mimetype(self, mimetype, is_list):
        if is_list:
            resource_name = self.mimetype_list_resource_name or \
                            self.name_plural.replace('_', '-')
        else:
            resource_name = self.mimetype_item_resource_name or \
                            self.name.replace('_', '-')

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
            if mime[key]
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
                if (mimetype_pair['list'] == mimetype and
                    mimetype_pair['item']):
                    response_args['headers'] = {
                        'Item-Content-Type': mimetype_pair['item'],
                    }
                    break

        return response_args

    def get_object(self, request, *args, **kwargs):
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

        queryset = self.get_queryset(request, *args, **kwargs).select_related()

        if self.singleton:
            return queryset.get()
        else:
            return queryset.get(**{
                self.model_object_key: kwargs[self.uri_object_key]
            })

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
        except self.model.DoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_access_permissions(request, obj, *args, **kwargs):
            if request.user.is_authenticated():
                return PERMISSION_DENIED
            else:
                return NOT_LOGGED_IN

        last_modified_timestamp = self.get_last_modified(request, obj)

        if (last_modified_timestamp and
            get_modified_since(request, last_modified_timestamp)):
            return HttpResponseNotModified()

        etag = self.get_etag(request, obj)

        if etag and etag_if_none_match(request, etag):
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

    @webapi_request_fields(
        optional={
            'start': {
                'type': int,
                'description': 'The 0-based index of the first result in the '
                               'list. The start index is usually the previous '
                               'start index plus the number of previous '
                               'results. By default, this is 0.',
            },
            'max-results': {
                'type': int,
                'description': 'The maximum number of results to return in '
                               'this list. By default, this is 25.',
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

        if self.model:
            try:
                queryset = self.get_queryset(request, is_list=True,
                                             *args, **kwargs).select_related()
            except ObjectDoesNotExist:
                return DOES_NOT_EXIST

            return WebAPIResponsePaginated(
                request,
                queryset=queryset,
                results_key=self.list_result_key,
                serialize_object_func =
                    lambda obj: get_resource_for_object(obj).serialize_object(
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
        except self.model.DoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_delete_permissions(request, obj, *args, **kwargs):
            if request.user.is_authenticated():
                return PERMISSION_DENIED
            else:
                return NOT_LOGGED_IN

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
        urlpatterns = never_cache_patterns('',
            url(r'^$', self, name=self._build_named_url(self.name_plural)),
        )

        for resource in self.list_child_resources:
            resource._parent_resource = self
            child_regex = r'^' + resource.uri_name + '/'
            urlpatterns += patterns('',
                url(child_regex, include(resource.get_url_patterns())),
            )

        if self.uri_object_key or self.singleton:
            # If the resource has particular items in it...
            if self.uri_object_key:
                base_regex = r'^(?P<%s>%s)/' % (self.uri_object_key,
                                                self.uri_object_key_regex)
            elif self.singleton:
                base_regex = r'^'

            urlpatterns += never_cache_patterns('',
                url(base_regex + '$', self,
                    name=self._build_named_url(self.name))
            )

            for resource in self.item_child_resources:
                resource._parent_resource = self
                child_regex = base_regex + resource.uri_name + '/'
                urlpatterns += patterns('',
                    url(child_regex, include(resource.get_url_patterns())),
                )

        return urlpatterns

    def has_access_permissions(self, request, obj, *args, **kwargs):
        """Returns whether or not the user has read access to this object."""
        return True

    def has_modify_permissions(self, request, obj, *args, **kwargs):
        """Returns whether or not the user can modify this object."""
        return False

    def has_delete_permissions(self, request, obj, *args, **kwargs):
        """Returns whether or not the user can delete this object."""
        return False

    def serialize_object(self, obj, *args, **kwargs):
        """Serializes the object into a Python dictionary."""
        data = {
            'links': self.get_links(self.item_child_resources, obj,
                                    *args, **kwargs),
        }

        request = kwargs.get('request', None)
        expand = request.GET.get('expand', request.POST.get('expand', ''))
        expanded_resources = expand.split(',')

        for field in list(self.fields):
            serialize_func = getattr(self, "serialize_%s_field" % field, None)

            if serialize_func and callable(serialize_func):
                value = serialize_func(obj, request=request)
            else:
                value = getattr(obj, field)

                if isinstance(value, models.Manager):
                    value = value.all()
                elif isinstance(value, models.ForeignKey):
                    value = value.get()

            expand_field = field in expanded_resources

            if isinstance(value, models.Model) and not expand_field:
                resource = get_resource_for_object(value)
                assert resource

                data['links'][field] = {
                    'method': 'GET',
                    'href': resource.get_href(value, *args, **kwargs),
                    'title': unicode(value),
                }
            elif isinstance(value, QuerySet) and not expand_field:
                data[field] = [
                    {
                        'method': 'GET',
                        'href': get_resource_for_object(o).get_href(
                                    o, *args, **kwargs),
                        'title': unicode(o),
                    }
                    for o in value.all()
                ]
            else:
                data[field] = value

        for resource_name in expanded_resources:
            if resource_name not in data['links']:
                continue

            # Try to find the resource from the child list.
            found = False

            for resource in self.item_child_resources:
                if resource_name in [resource.name, resource.name_plural]:
                    found = True
                    break

            if not found or not resource.model:
                continue

            del data['links'][resource_name]

            extra_kwargs = {
                self.uri_object_key: getattr(obj, self.model_object_key),
            }
            extra_kwargs.update(**kwargs)
            extra_kwargs.update(self.get_href_parent_ids(obj))

            data[resource_name] = resource.get_queryset(
                is_list=True, *args, **extra_kwargs)

        return data

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
            links[resource.name_plural] = {
                'method': 'GET',
                'href': '%s%s/' % (clean_base_href, resource.uri_name),
            }

        for key, info in self.get_related_links(obj, request,
                                                *args, **kwargs).iteritems():
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
        href_kwargs.update(self.get_href_parent_ids(obj))

        return request.build_absolute_uri(
            reverse(self._build_named_url(self.name), kwargs=href_kwargs))

    def get_href_parent_ids(self, obj):
        """Returns a dictionary mapping parent object keys to their values for
        an object.
        """
        parent_ids = {}

        if self._parent_resource and self.model_parent_key:
            parent_obj = self.get_parent_object(obj)
            parent_ids = self._parent_resource.get_href_parent_ids(parent_obj)

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

    def get_etag(self, request, obj):
        """Returns the ETag representing the state of the object.

        By default, this uses ``etag_field`` to determine what field in
        the model is unique enough to represent the state of the object.

        This can be overridden for more complex behavior.
        """
        if self.etag_field:
            return unicode(getattr(obj, self.etag_field))
        elif self.autogenerate_etags:
            return self.generate_etag(obj, self.fields, request=request)

        return None

    def generate_etag(self, obj, fields, request):
        """Generates an ETag from the serialized values of all given fields."""
        values = []

        for field in fields:
            serialize_func = getattr(self, "serialize_%s_field" % field, None)

            if serialize_func and callable(serialize_func):
                values.append(serialize_func(obj, request=request))
            else:
                values.append(unicode(getattr(obj, field)))

        return sha1(':'.join(fields)).hexdigest()

    def _build_named_url(self, name):
        """Builds a Django URL name from the provided name."""
        return '%s-resource' % name.replace('_', '-')


class RootResource(WebAPIResource):
    """The root of a resource tree.

    This is meant to be instantiated with a list of immediate child
    resources. The result of ``get_url_patterns`` should be included in
    a project's ``urls.py``.
    """
    name = 'root'
    singleton = True

    def __init__(self, child_resources=[], include_uri_templates=True):
        super(RootResource, self).__init__()
        self.list_child_resources = child_resources
        self._uri_templates = {}
        self._include_uri_templates = include_uri_templates

    def get_etag(self, request, obj, *args, **kwargs):
        return sha1('%s:%s' %
                    (self._include_uri_templates,
                     ':'.join(repr(self.list_child_resources)))).hexdigest()

    def get(self, request, *args, **kwargs):
        """
        Retrieves the list of top-level resources, and a list of
        :term:`URI templates` for accessing any resource in the tree.
        """
        etag = self.get_etag(request, None)

        if etag_if_none_match(request, etag):
            return HttpResponseNotModified()

        data = {
            'links': self.get_links(self.list_child_resources,
                                    request=request, *args, **kwargs),
        }

        if self._include_uri_templates:
            data['uri_templates'] = self.get_uri_templates(request, *args,
                                                           **kwargs)

        return 200, data, {
            'ETag': etag,
        }

    def get_uri_templates(self, request, *args, **kwargs):
        """Returns all URI templates in the resource tree.

        REST APIs can be very chatty if a client wants to be well-behaved
        and crawl the resource tree asking for the links, instead of
        hard-coding the paths. The benefit is that they can keep from
        breaking when paths change. The downside is that it can take many
        HTTP requests to get the right resource.

        This list of all URI templates allows clients who know the resource
        name and the data they care about to simply plug them into the
        URI template instead of trying to crawl over the whole tree. This
        can make things far more efficient.
        """
        if not self._uri_templates:
            self._uri_templates = {}
            base_href = request.build_absolute_uri()

            for name, href in self._walk_resources(self, base_href):
                self._uri_templates[name] = href

        return self._uri_templates

    def _walk_resources(self, resource, list_href):
        yield resource.name_plural, list_href

        for child in resource.list_child_resources:
            child_href = list_href + child.uri_name + '/'

            for name, href in self._walk_resources(child, child_href):
                yield name, href

        if resource.uri_object_key:
            object_href = '%s{%s}/' % (list_href, resource.uri_object_key)

            yield resource.name, object_href

            for child in resource.item_child_resources:
                child_href = object_href + child.uri_name + '/'

                for name, href in self._walk_resources(child, child_href):
                    yield name, href


class UserResource(WebAPIResource):
    """A default resource for representing a Django User model."""
    model = User
    fields = {
        'id': {
            'type': int,
            'description': 'The numeric ID of the user.',
        },
        'username': {
            'type': str,
            'description': "The user's username.",
        },
        'first_name': {
            'type': str,
            'description': "The user's first name.",
        },
        'last_name': {
            'type': str,
            'description': "The user's last name.",
        },
        'fullname': {
            'type': str,
            'description': "The user's full name (first and last).",
        },
        'email': {
            'type': str,
            'description': "The user's e-mail address",
        },
        'url': {
            'type': str,
            'description': "The URL to the user's page on the site. "
                           "This is deprecated and will be removed in a "
                           "future version.",
        },
    }

    uri_object_key = 'username'
    uri_object_key_regex = '[A-Za-z0-9@\._-]+'
    model_object_key = 'username'
    autogenerate_etags = True

    allowed_methods = ('GET',)

    def serialize_fullname_field(self, user, **kwargs):
        return user.get_full_name()

    def serialize_url_field(self, user, **kwargs):
        return user.get_absolute_url()

    def has_modify_permissions(self, request, user, *args, **kwargs):
        """Returns whether or not the user can modify this object."""
        return request.user.is_authenticated() and user.pk == request.user.pk

    @augment_method_from(WebAPIResource)
    def get_list(self, *args, **kwargs):
        """Retrieves the list of users on the site."""
        pass


class GroupResource(WebAPIResource):
    """A default resource for representing a Django Group model."""
    model = Group
    fields = ('id', 'name')

    uri_object_key = 'group_name'
    uri_object_key_regex = '[A-Za-z0-9_-]+'
    model_object_key = 'name'
    autogenerate_etags = True

    allowed_methods = ('GET',)


def register_resource_for_model(model, resource):
    """Registers a resource as the official location for a model.

    ``resource`` can be a callable function that takes an instance of
    ``model`` and returns a ``WebAPIResource``.
    """
    _model_to_resources[model] = resource


def unregister_resource_for_model(model):
    """Removes the official location for a model."""
    del _model_to_resources[model]


def get_resource_for_object(obj):
    """Returns the resource for an object."""
    resource = _model_to_resources.get(obj.__class__, None)

    if not isinstance(resource, WebAPIResource) and callable(resource):
        resource = resource(obj)

    return resource


def get_resource_from_name(name):
    """Returns the resource of the specified name."""
    return _name_to_resources.get(name, None)

def get_resource_from_class(klass):
    """Returns the resource with the specified resource class."""
    return _class_to_resources.get(klass, None)

def unregister_resource(resource):
    """Unregisters a resource from the caches."""
    del _name_to_resources[resource.name]
    del _name_to_resources[resource.name_plural]
    del _class_to_resources[resource.__class__]


user_resource = UserResource()
group_resource = GroupResource()

# These are good defaults, and will be overridden if another class calls
# register_resource_for_model on these models.
register_resource_for_model(User, user_resource)
register_resource_for_model(Group, group_resource)
