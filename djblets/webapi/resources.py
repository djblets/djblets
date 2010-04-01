from django.conf.urls.defaults import include, patterns, url
from django.contrib.auth.models import User, Group
from django.core.urlresolvers import reverse, NoReverseMatch
from django.db import models
from django.http import HttpResponseNotAllowed, HttpResponse

from djblets.util.misc import never_cache_patterns
from djblets.webapi.core import WebAPIResponse, WebAPIResponseError
from djblets.webapi.decorators import webapi_login_required
from djblets.webapi.errors import WebAPIError, DOES_NOT_EXIST, \
                                  PERMISSION_DENIED


class WebAPIResource(object):
    model = None
    fields = ()
    uri_object_key_regex = '[0-9]+'
    uri_object_key = None
    model_object_key = 'pk'
    list_child_resources = []
    item_child_resources = []
    actions = {}

    allowed_methods = ('GET',)

    method_mapping = {
        'GET': 'get',
        'POST': 'post',
        'PUT': 'put',
        'DELETE': 'delete',
    }

    def __call__(self, request, api_format="json", *args, **kwargs):
        method = request.method

        if method == 'POST':
            # Not all clients can do anything other than GET or POST.
            # So, in the case of POST, we allow overriding the method
            # used.
            method = request.POST.get('method', kwargs.get('method', method))
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
                self.uri_object_key is not None and
                self.uri_object_key not in kwargs):
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
        if self.model:
            return self.model.__name__.lower()
        else:
            return self.__name__.lower()

    @property
    def name_plural(self):
        return self.name + 's'

    def get_object(self, request, *args, **kwargs):
        assert self.model
        assert self.uri_object_key

        queryset = self.get_queryset(request, *args, **kwargs)

        return queryset.get(**{
            self.model_object_key: kwargs[self.uri_object_key]
        })

    def post(self, *args, **kwargs):
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
        action = request.PUT.get('action', kwargs.get('action', None))

        if action and action != 'set':
            action_func = getattr(self, 'action_%s' % action)

            if callable(action_func):
                return action_func(request, *args, **kwargs)
            else:
                return INVALID_ACTION, {
                    'action': action,
                }
        else:
            return self.update(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not self.model or self.uri_object_key is None:
            return HttpResponseNotAllowed(self.allowed_methods)

        try:
            obj = self.get_object(request, *args, **kwargs)
        except self.model.DoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_access_permissions(request, obj, *args, **kwargs):
            return PERMISSION_DENIED

        key = self.name.replace('-', '_')

        return 200, {
            key: self.serialize_object(obj, *args, **kwargs),
        }

    def get_list(self, request, *args, **kwargs):
        if not self.model:
            return HttpResponseNotAllowed(self.allowed_methods)

        key = self.name_plural.replace('-', '_')

        # TODO: Paginate this.
        data = {
            key: self.get_queryset(request, is_list=True, *args, **kwargs),
        }

        if self.list_child_resources:
            data['related_hrefs'] = {}

            for resource in self.list_child_resources:
                data['related_hrefs'][resource.name_plural] = \
                    resource.name_plural + '/'

        return 200, data

    @webapi_login_required
    def create(self, request, api_format, *args, **kwargs):
        return HttpResponseNotAllowed(self.allowed_methods)

    @webapi_login_required
    def update(self, request, api_format, *args, **kwargs):
        return HttpResponseNotAllowed(self.allowed_methods)

    @webapi_login_required
    def delete(self, request, api_format, *args, **kwargs):
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

    def get_queryset(self, request, *args, **kwargs):
        return self.model.objects.all()

    def get_url_patterns(self):
        urlpatterns = never_cache_patterns('',
            url(r'^$', self, name='%s-resource' % self.name_plural),
        )

        for resource in self.list_child_resources:
            child_regex = r'^' + resource.name_plural + '/'
            urlpatterns += patterns('',
                url(child_regex, include(resource.get_url_patterns())),
            )

        if self.uri_object_key:
            # If the resource has particular items in it...
            base_regex = r'^(?P<%s>%s)/' % (self.uri_object_key,
                                            self.uri_object_key_regex)

            urlpatterns += never_cache_patterns('',
                url(base_regex + '$', self, name='%s-resource' % self.name),
            )

            for resource in self.item_child_resources:
                child_regex = base_regex + resource.name_plural + '/'
                urlpatterns += patterns('',
                    url(child_regex, include(resource.get_url_patterns())),
                )

        return urlpatterns

    def has_access_permissions(self, request, obj, *args, **kwargs):
        return True

    def has_delete_permissions(self, request, obj, *args, **kwargs):
        return True

    def serialize_object(self, obj, api_format='json', *args, **kwargs):
        data = {}

        if self.uri_object_key:
            href = self.get_href(obj, api_format=api_format)

            if href:
                data['href'] = href

        for field in self.fields:
            serialize_func = getattr(self, "serialize_%s_field" % field, None)

            if serialize_func and callable(serialize_func):
                value = serialize_func(obj)
            else:
                value = getattr(obj, field)

                if callable(getattr(value, 'all', None)):
                    value = value.all()
                elif isinstance(value, models.ForeignKey):
                    value = value.get()

            data[field] = value

        if self.item_child_resources:
            data['related_hrefs'] = {}

            base_href = self.get_href(obj, api_format=api_format)

            for resource in self.item_child_resources:
                if resource.uri_object_key:
                    data['related_hrefs'][resource.name_plural] = \
                        '%s%s/' % (base_href, resource.name_plural)

        return data

    def get_href(self, obj, *args, **kwargs):
        object_key = getattr(obj, self.model_object_key)
        resource_name = '%s-resource' % self.name
        parent_ids = self.get_href_parent_ids(obj, *args, **kwargs)

        href_kwargs = {
            self.uri_object_key: object_key,
        }
        href_kwargs.update(parent_ids)

        try:
            return reverse(resource_name, kwargs=href_kwargs)
        except NoReverseMatch:
            href_kwargs['api_format'] = kwargs.get('api_format', None)

            return reverse(resource_name, kwargs=href_kwargs)

    def get_href_parent_ids(self, obj, *args, **kwargs):
        return {}


class UserResource(WebAPIResource):
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


class GroupResource(WebAPIResource):
    model = Group
    fields = ('id', 'name')

    uri_object_key = 'group_name'
    uri_object_key_regex = '[A-Za-z0-9_-]+'
    model_object_key = 'name'

    allowed_methods = ('GET',)


userResource = UserResource()
groupResource = GroupResource()
