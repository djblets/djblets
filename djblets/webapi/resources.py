from django.conf.urls.defaults import include, patterns, url
from django.contrib.auth.models import User, Group
from django.core.urlresolvers import reverse, NoReverseMatch
from django.db import models
from django.http import HttpResponseNotAllowed, HttpResponse

from djblets.util.misc import never_cache_patterns
from djblets.webapi.core import WebAPIResponse, WebAPIResponseError, \
                                WebAPIResponsePaginated
from djblets.webapi.decorators import webapi_login_required
from djblets.webapi.errors import WebAPIError, DOES_NOT_EXIST, \
                                  PERMISSION_DENIED


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

    Resource associated with a model may want to override the ``get_queryset``
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
    """

    # Configuration
    model = None
    fields = ()
    uri_object_key_regex = '[0-9]+'
    uri_object_key = None
    model_object_key = 'pk'
    model_parent_key = None
    list_child_resources = []
    item_child_resources = []
    allowed_methods = ('GET',)

    # State
    method_mapping = {
        'GET': 'get',
        'POST': 'post',
        'PUT': 'put',
        'DELETE': 'delete',
    }

    _parent_resource = None

    def __call__(self, request, api_format="json", *args, **kwargs):
        """Invokes the correct HTTP handler based on the type of request."""
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

        request.PUT = request.POST


        if method in self.allowed_methods:
            if (method == "GET" and
                (self.uri_object_key is not None and
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
                return WebAPIResponseError(request, err=result,
                                           api_format=api_format)
            elif isinstance(result, tuple):
                headers = {}

                if len(result) == 3:
                    headers = result[2]

                if isinstance(result[0], WebAPIError):
                    return WebAPIResponseError(request,
                                               err=result[0],
                                               headers=headers,
                                               extra_params=result[1],
                                               api_format=api_format)
                else:
                    return WebAPIResponse(request,
                                          status=result[0],
                                          obj=result[1],
                                          headers=headers,
                                          api_format=api_format)
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

    def get_object(self, request, *args, **kwargs):
        """Returns an object, given captured parameters from a URL.

        This will perform a query for the object, taking into account
        ``model_object_key``, ``uri_object_key``, and any captured parameters
        from the URL.

        This requires that ``model`` and ``uri_object_key`` be set.
        """
        assert self.model
        assert self.uri_object_key

        queryset = self.get_queryset(request, *args, **kwargs)

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

    def get(self, request, *args, **kwargs):
        """Handles HTTP GETs to individual object resources.

        By default, this will check for access permissions and query for
        the object. It will then return a serialized form of the object.

        This may need to be overridden if needing more complex logic.
        """
        if not self.model or self.uri_object_key is None:
            return HttpResponseNotAllowed(self.allowed_methods)

        try:
            obj = self.get_object(request, *args, **kwargs)
        except self.model.DoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_access_permissions(request, obj, *args, **kwargs):
            return PERMISSION_DENIED

        return 200, {
            self.item_result_key: self.serialize_object(obj, request=request,
                                                        *args, **kwargs),
        }

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
            return WebAPIResponsePaginated(
                request,
                queryset=self.get_queryset(request, is_list=True,
                                           *args, **kwargs),
                results_key=self.list_result_key,
                extra_data=data)
        else:
            return data

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
    def delete(self, request, api_format, *args, **kwargs):
        """Handles HTTP DELETE requests to object resources.

        This is used to delete an object, if the user has permissions to
        do so.

        By default, this deletes the object and returns HTTP 204 No Content.
        """
        if not self.model or self.uri_object_key is None:
            return HttpResponseNotAllowed(self.allowed_methods)

        try:
            queryset = self.get_queryset(request, *args, **kwargs)
            obj = queryset.get(**{
                self.model_object_key: kwargs[self.uri_object_key]
            })
        except self.model.DoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_delete_permissions(request, obj, *args, **kwargs):
            return PERMISSION_DENIED

        obj.delete()

        return 204, {}

    def get_queryset(self, request, is_list=False, *args, **kwargs):
        """Returns a queryset used for querying objects or lists of objects.

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

        if self.uri_object_key:
            # If the resource has particular items in it...
            base_regex = r'^(?P<%s>%s)/' % (self.uri_object_key,
                                            self.uri_object_key_regex)

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
        data = {}

        for field in self.fields:
            serialize_func = getattr(self, "serialize_%s_field" % field, None)

            if serialize_func and callable(serialize_func):
                value = serialize_func(obj)
            else:
                value = getattr(obj, field)

                if isinstance(value, models.Manager):
                    value = value.all()
                elif isinstance(value, models.ForeignKey):
                    value = value.get()

            data[field] = value

        data['links'] = \
            self.get_links(self.item_child_resources, obj, *args, **kwargs)

        return data

    def get_links(self, resources=[], obj=None, request=None,
                  *args, **kwargs):
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

        return links

    def get_href(self, obj, request, *args, **kwargs):
        """Returns the URL for this object."""
        if not self.uri_object_key:
            return None

        href_kwargs = {
            self.uri_object_key: getattr(obj, self.model_object_key),
        }
        href_kwargs.update(self.get_href_parent_ids(obj))

        try:
            return request.build_absolute_uri(
                reverse(self._build_named_url(self.name),
                        kwargs=href_kwargs))
        except NoReverseMatch:
            return None

    def get_href_parent_ids(self, obj):
        """Returns a dictionary mapping parent object keys to their values for
        an object.
        """
        parent_ids = {}

        if self._parent_resource and self.model_parent_key:
            assert self._parent_resource.uri_object_key

            parent_obj = self.get_parent_object(obj)
            parent_ids = self._parent_resource.get_href_parent_ids(parent_obj)
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
    name_plural = 'root'

    def __init__(self, child_resources=[], include_uri_templates=True):
        super(RootResource, self).__init__()
        self.list_child_resources = child_resources
        self._uri_templates = {}
        self._include_uri_templates = include_uri_templates

    def get(self, request, *args, **kwargs):
        data = {
            'links': self.get_links(self.list_child_resources,
                                    request=request, *args, **kwargs),
        }

        if self._include_uri_templates:
            data['uri_templates'] = self.get_uri_templates(request, *args,
                                                           **kwargs)

        return 200, data

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
    fields = (
        'id', 'username', 'first_name', 'last_name', 'fullname',
        'email', 'url'
    )

    uri_object_key = 'username'
    uri_object_key_regex = '[A-Za-z0-9_-]+'
    model_object_key = 'username'

    allowed_methods = ('GET',)

    def serialize_fullname_field(self, user):
        return user.get_full_name()

    def serialize_url_field(self, user):
        return user.get_absolute_url()

    def has_modify_permissions(self, request, user, *args, **kwargs):
        """Returns whether or not the user can modify this object."""
        return request.user.is_authenticated() and user.pk == request.user.pk


class GroupResource(WebAPIResource):
    """A default resource for representing a Django Group model."""
    model = Group
    fields = ('id', 'name')

    uri_object_key = 'group_name'
    uri_object_key_regex = '[A-Za-z0-9_-]+'
    model_object_key = 'name'

    allowed_methods = ('GET',)


user_resource = UserResource()
group_resource = GroupResource()
