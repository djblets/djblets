.. _writing-api-resources:

=========================
Writing Web API Resources
=========================

.. py:currentmodule:: djblets.webapi.resources.base


Overview
--------

:py:class:`~WebAPIResource` is used to write REST API resources. A resource
lives at a specific, stable URL, can represent either an object or a list of
objects, and can respond to various HTTP methods (GET, POST, PUT, DELETE).

Subclasses of :py:class:`~WebAPIResource` are expected to override functions
and variables in order to provide specific functionality, such as modifying or
creating new objects.

This guide will go over the capabilities and responsibilities of resource
subclasses.


Representing Models
-------------------

Most resources will :py:attr:`WebAPIResource.model` set to a
:py:class:`~django.db.models.Model` subclass, and
:py:attr:`WebAPIResource.fields` set to a dictionary defining the fields to
return in the resource payloads.

Each resource will also include a ``link`` dictionary that maps
a key (resource name or action) to a dictionary containing the URL
(``href``) and the HTTP method that's to be used for that URL
(``method``). This will include a special ``self`` key that links to
that resource's actual location.

An example of this might be:

.. code-block:: javascript

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

Resources associated with a model may want to override
:py:meth:`WebAPIResource.get_queryset` to return a queryset with a more
specific query.

By default, an individual object's key name in the resulting payloads
will be set to the lowercase class name of the object, and the plural
version used for lists will be the same but with "s" appended to it. This
can be overridden by setting :py:attr:`WebAPIResource.name` and
:py:attr:`WebAPIResource.name_plural`.


Non-Database Models
-------------------

Resources are not always backed by a database model. It's often useful to
work with lists of objects or data computed within the request.

In these cases, most resources will still want to set
:py:attr:`WebAPIResource.model` to some sort of class and provide a
:py:attr:`WebAPIResource.fields` dictionary. It's expected that the fields
will all exist as attributes on an instance of the model, or that a serializer
function will exist for the field.

These resources will then to define a :py:meth:`WebAPIResource.get_queryset`
that returns a :py:class:`~djblets.db.query.LocalDataQuerySet` containing the
list of items to return in the resource. This will allow standard resource
functionality like pagination to work.


Matching Objects
----------------

Objects are generally queried by their numeric object ID and mapping that to
the object's ``pk`` attribute. For this to work, the
:py:attr:`WebAPIResource.uri_object_key` attribute must be set to the name in
the regex for the URL that will be captured and passed to the handlers for
this resource. The :py:attr:`WebAPIResource.uri_object_key_regex` attribute
can be overridden to specify the regex for matching this ID (useful for
capturing names instead of numeric IDs) and
:py:attr:`WebAPIResource.model_object_key` can be overridden to specify the
model field that will be matched against.


Parents and URLs
----------------

Resources typically have a parent resource, of which the resource is a
subclass. Resources will often list their children (by setting
:py:attr:`WebAPIResource.list_child_resources` and
:py:attr:`WebAPIResource.item_child_resources` in a subclass to lists of other
WebAPIResource instances). This makes the entire tree navigatable. The URLs
are built up automatically, so long as the result of
:py:func:`get_url_patterns` from top-level resources are added to the Django
``url_patterns`` variables commonly found in :file:`urls.py`.

Child objects should set the :py:attr:`WebAPIResource.model_parent_key`
variable to the field name of the object's parent in the resource hierarchy.
This allows :py:class:`WebAPIResource` to build a URL with the right values
filled in in order to make a URL to this object.

If the parent is dynamic based on certain conditions, then the
:py:meth:`WebAPIResource.get_parent_object` function can be overridden
instead.


Object Serialization
--------------------

Objects are serialized through the :py:meth:`WebAPIResource.serialize_object`
function. This rarely needs to be overridden, but can be called from
WebAPIEncoders in order to serialize the object. By default, this will loop
through the :py:attr:`WebAPIResource.fields` variable and add each value to
the resulting dictionary.

Values can be specially serialized by creating functions in the form of
:samp:`serialize_<fieldname>_field()`. These functions take the object being
serialized and must return a value that can be fed to the encoder.

By default, resources will not necessarily serialize the objects in their own
payloads. Instead, they will look up the registered resource instance for the
model using :py:meth:`WebAPIResourec.get_resource_for_object`, and serialize
with that. A resource can override that logic for its own payloads by
providing a custom :py:meth:`WebAPIResource.get_serializer_for_object` method.


Handling Requests
-----------------

WebAPIResource calls the following functions based on the type of
HTTP request:

* :py:meth:`~WebAPIResource.get` -
  HTTP GET for individual objects.

* :py:meth:`~WebAPIResource.get_list` -
  HTTP GET for resources representing lists of objects.

* :py:meth:`~WebAPIResource.create` -
  HTTP POST on resources representing lists of objects. This is expected to
  return the object and :http:`201` on success.

* :py:meth:`~WebAPIResource.update` -
  HTTP PUT on individual objects to modify their state based on full or
  partial data.

* :py:meth:`~WebAPIResource.delete` -
  HTTP DELETE on an individual object. This is expected to return :http:`204`
  on success. The default implementation just deletes the object.

Any function that is not implemented will return an :http:`405`. Functions
that have handlers provided should
set :py:attr:`WebAPIResource.allowed_methods` to a tuple of the HTTP methods
allowed. For example:

.. code-block:: python

   allowed_methods = ('GET', 'POST', 'DELETE')

These functions are passed an :py:class:`~django.http.HTTPRequest` and a list
of arguments captured in the URL and are expected to return standard HTTP
response codes, along with a payload in most cases. The functions can return
any of:

* :py:class:`~django.http.HttpResponse`
* :py:class:`~djblets.webapi.responses.WebAPIResponse`
* :py:class:`~djblets.webapi.errors.WebAPIError`
* Tuple of (:py:class:`~djblets.webapi.errors.WebAPIError`, payload)
* Tuple of (:py:class:`~djblets.webapi.errors.WebAPIError`,
  payload dictionary, headers dictionary)
* Tuple of (HTTP status, payload)
* Tuple of (HTTP status, payload dictionary, headers dictionary)

In general, it's best to return one of the tuples containing an HTTP
status, and not any object, but there are cases where an object is
necessary.

Commonly, a handler will need to fetch parent objects in order to make
some request. The values for all captured object IDs in the URL are passed
to the handler, but it's best to not use these directly. Instead, the
handler should accept a ``**kwargs`` parameter, and then call the parent
resource's :py:meth:`WebAPIResource.get_object` function and pass in that
``**kwargs``. For example:

.. code-block:: python

   def create(self, request, *args, **kwargs):
       try:
           my_parent = myParentResource.get_object(request, *args, **kwargs)
       except ObjectDoesNotExist:
           return DOES_NOT_EXIST


Pagination
----------

List resources automatically handle pagination of data, when using
models and querysets. Each request will return a fixed number of
results, and clients can fetch the previous or next batches through
the generated ``prev`` and ``next`` links.

By default, pagination is handled by
:py:class:`~djblets.webapi.responses.WebAPIResponsePaginated`. This is
responsible for fetching data from the resource's queryset. It's also
responsible for interpreting the ``start`` and ``max-results`` query
parameters, which are assumed to be 0-based indexes into the queryset.

Resources can override how pagination works by setting
:py:attr:`WebAPIResource.paginated_cls` to a subclass of
:py:class:`~djblets.webapi.responses.WebAPIResponsePaginated`.  Through that,
they can customize all aspects of pagination for the resource.


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

* :py:meth:`~WebAPIResource.has_access_permissions` -
  Used for HTTP GET calls. Returns ``True`` by default.

* :py:meth:`~WebAPIResource.has_modify_permissions` -
  Used for HTTP POST or PUT calls, if called by the subclass.
  Returns ``False`` by default.

* :py:meth:`~WebAPIResource.has_delete_permissions` -
  Used for HTTP DELETE permissions. Returns ``False`` by default.


Browser Caching
---------------

To improve performance, resources can make use of browser-side caching.
If a resource is accessed more than once, and it hasn't changed,
the resource will return an :http:`304`.

There are two methods for caching: Last Modified headers, and ETags.


Last Modified
~~~~~~~~~~~~~

A resource can set :py:meth:`WebAPIResource.last_modified_field` to the name
of a :py:class:`~django.db.models.DateTimeField` in the model. This will be
used to determine if the resource has changed since the last request.

If a bit more work is needed, the :py:meth:`WebAPIResource.get_last_modified`
function can instead be overridden. This takes the request and object and is
expected to return a timestamp.


ETags
~~~~~

ETags are arbitrary, unique strings that represent the state of a resource.
There should only ever be one possible ETag per state of the resource.

A resource can set the :py:attr:`WebAPIResourec.etag_field` to the name of a
field in the model.

If no field really works, :py:attr:`WebAPIResource.autogenerate_etags` can be
set. This will generate a suitable ETag based on all fields in the resource.
For this to work correctly, no custom data can be added to the payload, and
links cannot be dynamic.

If more work is needed, the :py:meth:`WebAPIResource.get_etag` function can
instead be overridden. It will take a request and object and is expected to
return a string.


Mimetypes
---------

Resources should list the possible mimetypes they'll accept and return in
:py:attr:`WebAPIResource.allowed_mimetypes`. Each entry in the list is a
dictionary with ``list`` containing a mimetype for resource lists, and
``item`` containing the equivalent mimetype for a resource item. In the case
of a singleton, ``item`` will contain the mimetype. If the mimetype is not
applicable to one of the resource forms, the corresponding entry should
contain ``None``.

Entries in these lists are checked against the mimetypes requested in the
HTTP ``Accept`` header, and, by default, the returned data will be sent in
that mimetype. If the requested data is a resource list, the corresponding
resource item mimetype will also be sent in the ``Item-Content-Type``
header.

By default, this lists will have entries with both ``list`` and ``item``
containing :mimetype:`application/json` and :mimetype:`application/xml`,
along with any resource-specific mimetypes, if used.


Resource-specific Mimetypes
~~~~~~~~~~~~~~~~~~~~~~~~~~~

In order to better identify resources, resources can provide their
own custom mimetypes. These are known as vendor-specific mimetypes, and
are subsets of :mimetype:`application/json` and
:mimetype:`application/xml`. An example would be
:mimetype:`application/vnd.example.com.myresource+json`.

To enable this on a resource, set :py:attr:`WebAPIResource.mimetype_vendor` to
the vendor name. This is often a domain name. For example:

.. code-block:: python

   mimetype_vendor = 'djblets.org'

The resource names will then be generated based on the name of the resource
(:py:attr:`WebAPIResource.name_plural` for resource lists,
:py:attr:`WebAPIResource.name` for resource items and singletons). These can
be customized as well:

.. code-block:: python

   mimetype_list_resource_name = 'myresource-list'
   mimetype_item_resource_name = 'myresource'

When these are used, any client requesting either the resource-specific
mimetype or the more generic mimetype will by default receive a payload
with the resource-specific mimetype. This makes it easier to identify
the schema of resource data without hard-coding any knowledge of the
URI.


Limiting Payload Contents
-------------------------

.. versionadded:: 0.9

Often times, the client won't actually need the full contents of an
API payload. Returning a full payload would not only increase the amount
of data that needs to be transferred, but would also incur extra
processing time on both the server and client, possibly also additional
database queries.

Clients can specify a list of fields and/or links that should be returned
in the payload by including ``?only-fields=`` or ``?only-links=`` in the URL
in any GET requst. These should contain a comma-separated list of fields or
link names to include. To prevent any fields/links from being returned,
simply leave the list blank.

To limit fields/links in PUT or POST requests, you should instead send
a field in the request called ``only_fields`` or ``only_links``. The
behavior is exactly the same as for GET requests.
