from __future__ import print_function, unicode_literals

import json
import warnings

from django.contrib.auth.models import User
from django.db.models import Model
from django.http import HttpResponseNotModified
from django.test.client import RequestFactory
from django.utils import six

from djblets.testing.testcases import TestCase
from djblets.util.http import encode_etag
from djblets.webapi.fields import (ResourceFieldType,
                                   ResourceListFieldType,
                                   StringFieldType)
from djblets.webapi.resources.base import WebAPIResource
from djblets.webapi.resources.registry import (register_resource_for_model,
                                               unregister_resource_for_model,
                                               unregister_resource)
from djblets.webapi.responses import WebAPIResponse


class BaseTestWebAPIResource(WebAPIResource):
    mimetype_vendor = 'djblets-test'


class TestUserResource(BaseTestWebAPIResource):
    name = 'user'
    model = User

    fields = {
        'username': {
            'type': StringFieldType,
        },
        'first_name': {
            'type': StringFieldType,
        },
        'last_name': {
            'type': StringFieldType,
        },
    }

    def get_href(self, obj, *args, **kwargs):
        return 'http://testserver/api/test/users/%s/' % obj.pk


class BaseTestRefUserResource(BaseTestWebAPIResource):
    name = 'test'
    uri_object_key = 'pk'

    def build_resource_url(self, name, request, **kwargs):
        return request.build_absolute_uri()

    def get_serializer_for_object(self, o):
        if isinstance(o, User):
            return TestUserResource()
        else:
            return self


class WebAPIResourceTests(TestCase):
    """Unit tests for djblets.webapi.resources.base."""

    def setUp(self):
        super(WebAPIResourceTests, self).setUp()

        self.maxDiff = 10000000

        self.factory = RequestFactory()
        self.test_resource = None

    def tearDown(self):
        super(WebAPIResourceTests, self).tearDown()

        if self.test_resource:
            unregister_resource(self.test_resource)

    def test_vendor_mimetypes(self):
        """Testing WebAPIResource with vendor-specific mimetypes"""
        class TestResource(WebAPIResource):
            mimetype_vendor = 'djblets'

        self.test_resource = TestResource()

        item_mimetypes = [
            mimetype['item']
            for mimetype in self.test_resource.allowed_mimetypes
            if 'item' in mimetype
        ]

        list_mimetypes = [
            mimetype['list']
            for mimetype in self.test_resource.allowed_mimetypes
            if 'list' in mimetype
        ]

        self.assertEqual(len(list_mimetypes), 4)
        self.assertEqual(len(item_mimetypes), 4)

        self.assertTrue('application/json' in
                        list_mimetypes)
        self.assertTrue('application/xml' in
                        list_mimetypes)
        self.assertTrue('application/vnd.djblets.testresources+json' in
                        list_mimetypes)
        self.assertTrue('application/vnd.djblets.testresources+xml' in
                        list_mimetypes)

        self.assertTrue('application/json' in
                        item_mimetypes)
        self.assertTrue('application/xml' in
                        item_mimetypes)
        self.assertTrue('application/vnd.djblets.testresource+json' in
                        item_mimetypes)
        self.assertTrue('application/vnd.djblets.testresource+xml' in
                        item_mimetypes)

    def test_vendor_mimetypes_with_custom(self):
        """Testing WebAPIResource with vendor-specific and custom mimetypes"""
        class TestResource(WebAPIResource):
            mimetype_vendor = 'djblets'
            allowed_mimetypes = WebAPIResource.allowed_mimetypes + [
                {'item': 'text/html'},
            ]

        self.test_resource = TestResource()

        item_mimetypes = [
            mimetype['item']
            for mimetype in self.test_resource.allowed_mimetypes
            if 'item' in mimetype
        ]

        list_mimetypes = [
            mimetype['list']
            for mimetype in self.test_resource.allowed_mimetypes
            if 'list' in mimetype
        ]

        self.assertEqual(len(list_mimetypes), 4)
        self.assertEqual(len(item_mimetypes), 5)

        self.assertTrue('application/json' in
                        list_mimetypes)
        self.assertTrue('application/xml' in
                        list_mimetypes)
        self.assertTrue('application/vnd.djblets.testresources+json' in
                        list_mimetypes)
        self.assertTrue('application/vnd.djblets.testresources+xml' in
                        list_mimetypes)

        self.assertTrue('application/json' in
                        item_mimetypes)
        self.assertTrue('application/xml' in
                        item_mimetypes)
        self.assertTrue('application/vnd.djblets.testresource+json' in
                        item_mimetypes)
        self.assertTrue('application/vnd.djblets.testresource+xml' in
                        item_mimetypes)
        self.assertTrue('application/vnd.djblets.testresource+xml' in
                        item_mimetypes)
        self.assertTrue('text/html' in
                        item_mimetypes)

    def test_get_with_vendor_mimetype(self):
        """Testing WebAPIResource with GET and vendor-specific mimetypes"""
        class TestResource(WebAPIResource):
            allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
            mimetype_vendor = 'djblets'
            uri_object_key = 'id'

            def get(self, *args, **kwargs):
                return 200, {}

            create = get
            update = get
            delete = get

        self.test_resource = TestResource()
        self._test_mimetype_responses(
            self.test_resource,
            '/api/tests/',
            'application/vnd.djblets.testresources+json',
            'application/vnd.djblets.testresources+xml')
        self._test_mimetype_responses(
            self.test_resource,
            '/api/tests/',
            'application/vnd.djblets.testresource+json',
            'application/vnd.djblets.testresource+xml',
            method='post')

        self._test_mimetype_responses(
            self.test_resource,
            '/api/tests/1/',
            'application/vnd.djblets.testresource+json',
            'application/vnd.djblets.testresource+xml',
            view_kwargs={'id': 1},
            method='put')
        self._test_mimetype_responses(
            self.test_resource,
            '/api/tests/1/',
            'application/vnd.djblets.testresource+json',
            'application/vnd.djblets.testresource+xml',
            view_kwargs={'id': 1},
            method='delete')

    def test_get_with_item_mimetype(self):
        """Testing WebAPIResource with GET and Item-Content-Type header"""
        class TestResource(WebAPIResource):
            allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
            mimetype_vendor = 'djblets'
            uri_object_key = 'id'

            def get(self, *args, **kwargs):
                return 200, {}

            create = get
            update = get
            delete = get

        self.test_resource = TestResource()
        self._test_item_mimetype_responses(
            self.test_resource,
            '/api/tests/',
            'application/vnd.djblets.testresources+json',
            'application/vnd.djblets.testresources+xml',
            'application/vnd.djblets.testresource+json',
            'application/vnd.djblets.testresource+xml')
        self._test_item_mimetype_responses(
            self.test_resource,
            '/api/tests/',
            'application/vnd.djblets.testresource+json',
            'application/vnd.djblets.testresource+xml',
            None,
            None,
            method='post')

        self._test_item_mimetype_responses(
            self.test_resource,
            '/api/tests/1/',
            'application/vnd.djblets.testresource+json',
            'application/vnd.djblets.testresource+xml',
            None,
            None,
            view_kwargs={'id': 1},
            method='put')
        self._test_item_mimetype_responses(
            self.test_resource,
            '/api/tests/',
            'application/vnd.djblets.testresources+json',
            'application/vnd.djblets.testresources+xml',
            'application/vnd.djblets.testresource+json',
            'application/vnd.djblets.testresource+xml')
        self._test_item_mimetype_responses(
            self.test_resource,
            '/api/tests/1/',
            'application/vnd.djblets.testresource+json',
            'application/vnd.djblets.testresource+xml',
            None,
            None,
            view_kwargs={'id': 1},
            method='delete')

    def test_get_with_autogenerate_etags_and_not_modified(self):
        """Testing WebAPIResource with GET and autogenerate_etags and requested
        ETag is a match
        """
        class TestResource(WebAPIResource):
            allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
            mimetype_vendor = 'djblets'
            uri_object_key = 'id'
            autogenerate_etags = True

            def get(self, *args, **kwargs):
                return 200, {
                    'abc': True,
                }

        resource = TestResource()
        etag = '790fc95c3f89afe28403c272553e790274ea1d3e'

        request = self.factory.get('/api/tests/',
                                   HTTP_ACCEPT='application/json',
                                   HTTP_IF_NONE_MATCH=etag)
        response = resource(request)

        self.assertIsInstance(response, HttpResponseNotModified)
        self.assertEqual(response.status_code, 304)
        self.assertEqual(response['ETag'], etag)

    def test_get_with_autogenerate_etags_and_modified(self):
        """Testing WebAPIResource with GET and autogenerate_etags and
        requested ETag is not a match
        """
        class TestResource(WebAPIResource):
            allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
            mimetype_vendor = 'djblets'
            uri_object_key = 'id'
            autogenerate_etags = True

            def get(self, *args, **kwargs):
                return 200, {
                    'abc': True,
                }

        resource = TestResource()
        request = self.factory.get('/api/tests/',
                                   HTTP_ACCEPT='application/json',
                                   HTTP_IF_NONE_MATCH='adfjhslfa')
        response = resource(request)

        self.assertIsInstance(response, WebAPIResponse)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['ETag'],
                         '790fc95c3f89afe28403c272553e790274ea1d3e')

    def test_generate_etag_with_encode_etag_true(self):
        """Testing WebAPIResource.generate_etag with encode_etag=True"""
        class TestObject(object):
            my_field = 'abc'

        request = RequestFactory().request()
        request.user = User()

        resource = WebAPIResource()
        obj = TestObject()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            etag = resource.generate_etag(obj, ['my_field'], request,
                                          encode_etag=True)

        self.assertEqual(len(w), 1)
        self.assertIn('generate_etag is deprecated',
                      six.text_type(w[0].message))

        self.assertEqual(
            etag,
            encode_etag(
                ':%s' % repr(resource.serialize_object(obj, request=request))))

    def test_generate_etag_with_encode_etag_false(self):
        """Testing WebAPIResource.generate_etag with encode_etag=False"""
        class TestObject(object):
            my_field = 'abc'

        request = RequestFactory().request()
        request.user = User()

        resource = WebAPIResource()
        obj = TestObject()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            etag = resource.generate_etag(obj, None, request,
                                          encode_etag=False)

        self.assertEqual(len(w), 1)
        self.assertIn('generate_etag is deprecated',
                      six.text_type(w[0].message))

        self.assertEqual(
            etag,
            repr(resource.serialize_object(obj, request=request)))

    def test_are_cache_headers_current_with_old_last_modified(self):
        """Testing WebAPIResource.are_cache_headers_current with old last
        modified timestamp
        """
        request = RequestFactory().request()
        request.META['HTTP_IF_MODIFIED_SINCE'] = \
            'Wed, 14 Jan 2015 13:49:10 GMT'

        resource = WebAPIResource()
        self.assertFalse(resource.are_cache_headers_current(
            request, last_modified='Wed, 14 Jan 2015 12:10:13 GMT'))

    def test_are_cache_headers_current_with_current_last_modified(self):
        """Testing WebAPIResource.are_cache_headers_current with current last
        modified timestamp
        """
        timestamp = 'Wed, 14 Jan 2015 13:49:10 GMT'
        request = RequestFactory().request()
        request.META['HTTP_IF_MODIFIED_SINCE'] = timestamp

        resource = WebAPIResource()
        self.assertTrue(resource.are_cache_headers_current(
            request, last_modified=timestamp))

    def test_are_cache_headers_current_with_old_etag(self):
        """Testing WebAPIResource.are_cache_headers_current with old ETag"""
        request = RequestFactory().request()
        request.META['HTTP_IF_NONE_MATCH'] = 'abc123'

        resource = WebAPIResource()
        self.assertFalse(resource.are_cache_headers_current(request,
                                                            etag='def456'))

    def test_are_cache_headers_current_with_current_etag(self):
        """Testing WebAPIResource.are_cache_headers_current with current
        ETag
        """
        etag = 'abc123'
        request = RequestFactory().request()
        request.META['HTTP_IF_NONE_MATCH'] = etag

        resource = WebAPIResource()
        self.assertTrue(resource.are_cache_headers_current(request, etag=etag))

    def test_serialize_object_with_only_fields(self):
        """Testing WebAPIResource.serialize_object with
        ?only-fields=<fields>
        """
        class TestObject(object):
            field1 = 'abc'
            field2 = 'def'
            field3 = 'ghi'

        class TestResource(WebAPIResource):
            fields = {
                'field1': {
                    'type': StringFieldType,
                },
                'field2': {
                    'type': StringFieldType,
                },
                'field3': {
                    'type': StringFieldType,
                },
            }

        request = RequestFactory().get('/api/test/?only-fields=field1,field3')
        resource = TestResource()
        data = resource.serialize_object(TestObject(), request=request)

        self.assertEqual(data, {
            'field1': 'abc',
            'field3': 'ghi',
            'links': {
                'self': {
                    'href': 'http://testserver/api/test/'
                            '?only-fields=field1,field3',
                    'method': 'GET',
                },
            }
        })

    def test_serialize_object_with_only_fields_blank(self):
        """Testing WebAPIResource.serialize_object with ?only-fields="""
        class TestObject(object):
            field1 = 'abc'
            field2 = 'def'
            field3 = 'ghi'

        class TestResource(WebAPIResource):
            fields = {
                'field1': {
                    'type': StringFieldType,
                },
                'field2': {
                    'type': StringFieldType,
                },
                'field3': {
                    'type': StringFieldType,
                },
            }

        request = RequestFactory().get('/api/test/?only-fields=')
        resource = TestResource()
        data = resource.serialize_object(TestObject(), request=request)

        self.assertEqual(data, {
            'links': {
                'self': {
                    'href': 'http://testserver/api/test/?only-fields=',
                    'method': 'GET',
                },
            }
        })

    def test_serialize_object_with_expand_model(self):
        """Testing WebAPIResource.serialize_object with
        ?expand=<model_field>
        """
        class TestObject(object):
            pk = '1'
            user = User.objects.create(username='user1',
                                       first_name='Test1',
                                       last_name='User1')

        class TestResource(BaseTestRefUserResource):
            fields = {
                'user': {
                    'type': ResourceFieldType,
                    'resource': TestUserResource,
                },
            }

        request = RequestFactory().get('/api/test/?expand=user')
        resource = TestResource()
        data = resource.serialize_object(TestObject(), request=request)

        self.assertEqual(data, {
            '_expanded': {
                'user': {
                    'item_mimetype': 'application/vnd.djblets-test.user+json',
                },
            },
            'user': {
                'username': 'user1',
                'first_name': 'Test1',
                'last_name': 'User1',
                'links': {
                    'self': {
                        'href': 'http://testserver/api/test/users/1/',
                        'method': 'GET',
                    },
                },
            },
            'links': {
                'self': {
                    'href': 'http://testserver/api/test/?expand=user',
                    'method': 'GET',
                },
            }
        })

    def test_serialize_object_with_expand_queryset(self):
        """Testing WebAPIResource.serialize_object with
        ?expand=<queryset_field>
        """
        class TestObject(object):
            pk = '1'
            users = User.objects.all()

        class TestResource(BaseTestRefUserResource):
            fields = {
                'users': {
                    'type': ResourceListFieldType,
                    'resource': TestUserResource,
                },
            }

        User.objects.create(username='user1',
                            first_name='Test1',
                            last_name='User1')
        User.objects.create(username='user2',
                            first_name='Test2',
                            last_name='User2')

        request = RequestFactory().get('/api/test/?expand=users')
        resource = TestResource()
        data = resource.serialize_object(TestObject(), request=request)

        self.assertEqual(data, {
            '_expanded': {
                'users': {
                    'item_mimetype': 'application/vnd.djblets-test.user+json',
                },
            },
            'users': [
                {
                    'username': 'user1',
                    'first_name': 'Test1',
                    'last_name': 'User1',
                    'links': {
                        'self': {
                            'href': 'http://testserver/api/test/users/1/',
                            'method': 'GET',
                        },
                    },
                },
                {
                    'username': 'user2',
                    'first_name': 'Test2',
                    'last_name': 'User2',
                    'links': {
                        'self': {
                            'href': 'http://testserver/api/test/users/2/',
                            'method': 'GET',
                        },
                    },
                },
            ],
            'links': {
                'self': {
                    'href': 'http://testserver/api/test/?expand=users',
                    'method': 'GET',
                },
            }
        })

    def test_serialize_object_with_expand_child_resource(self):
        """Testing WebAPIResource.serialize_object with
        ?expand=<child_resource_field>
        """
        class TestObject(object):
            pk = '1'
            field = 'test'
            users = User.objects.all()

        class TestResource(BaseTestRefUserResource):
            item_child_resources = [TestUserResource()]

            fields = {
                'field': {
                    'type': StringFieldType,
                },
            }

        User.objects.create(username='user1',
                            first_name='Test1',
                            last_name='User1')
        User.objects.create(username='user2',
                            first_name='Test2',
                            last_name='User2')

        request = RequestFactory().get('/api/test/?expand=users')
        resource = TestResource()
        data = resource.serialize_object(TestObject(), request=request)

        self.assertEqual(data, {
            '_expanded': {
                'users': {
                    'item_mimetype': 'application/vnd.djblets-test.user+json',
                    'list_mimetype': 'application/vnd.djblets-test.users+json',
                    'list_url': 'http://testserver/api/test/users/',
                },
            },
            'field': 'test',
            'users': [
                {
                    'username': 'user1',
                    'first_name': 'Test1',
                    'last_name': 'User1',
                    'links': {
                        'self': {
                            'href': 'http://testserver/api/test/users/1/',
                            'method': 'GET',
                        },
                    },
                },
                {
                    'username': 'user2',
                    'first_name': 'Test2',
                    'last_name': 'User2',
                    'links': {
                        'self': {
                            'href': 'http://testserver/api/test/users/2/',
                            'method': 'GET',
                        },
                    },
                },
            ],
            'links': {
                'self': {
                    'href': 'http://testserver/api/test/?expand=users',
                    'method': 'GET',
                },
            }
        })

    def test_serialize_object_with_only_fields_and_expand(self):
        """Testing WebAPIResource.serialize_object with
        ?only-fields=<field>&expand=<field>
        """
        class TestObject(object):
            pk = 1

            field1 = 'abc'
            field2 = User.objects.create(username='user1',
                                         first_name='Test1',
                                         last_name='Test1')
            field3 = User.objects.create(username='user2',
                                         first_name='Test2',
                                         last_name='Test2')

        class TestResource(BaseTestRefUserResource):
            fields = {
                'field1': {
                    'type': StringFieldType,
                },
                'field2': {
                    'type': ResourceFieldType,
                    'resource': TestUserResource,
                },
                'field3': {
                    'type': ResourceFieldType,
                    'resource': TestUserResource,
                },
            }

        request = RequestFactory().get(
            '/api/test/?only-fields=field2&expand=field2')
        resource = TestResource()
        obj = TestObject()
        data = resource.serialize_object(obj, request=request)

        self.assertEqual(data, {
            '_expanded': {
                'field2': {
                    'item_mimetype': 'application/vnd.djblets-test.user+json',
                },
            },
            'field2': {
                'links': {
                    'self': {
                        'href': 'http://testserver/api/test/users/1/',
                        'method': 'GET',
                    },
                },
            },
            'links': {
                'self': {
                    'href': 'http://testserver/api/test/?only-fields=field2'
                            '&expand=field2',
                    'method': 'GET',
                },
                'field3': {
                    'href': 'http://testserver/api/test/users/2/',
                    'method': 'GET',
                    'title': 'user2',
                },
            }
        })

    def test_serialize_object_with_only_links(self):
        """Testing WebAPIResource.serialize_object with ?only-links=<links>"""
        class TestObject(object):
            field1 = 'abc'
            field2 = 'def'
            field3 = 'ghi'

        class TestResource(WebAPIResource):
            allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
            fields = {
                'field1': {
                    'type': StringFieldType,
                },
                'field2': {
                    'type': StringFieldType,
                },
                'field3': {
                    'type': StringFieldType,
                },
            }

        request = RequestFactory().get('/api/test/?only-links=delete,update')
        resource = TestResource()
        data = resource.serialize_object(TestObject(), request=request)

        self.assertEqual(data, {
            'field1': 'abc',
            'field2': 'def',
            'field3': 'ghi',
            'links': {
                'delete': {
                    'href': 'http://testserver/api/test/',
                    'method': 'DELETE',
                },
                'update': {
                    'href': 'http://testserver/api/test/',
                    'method': 'PUT',
                },
            }
        })

    def test_serialize_object_with_only_links_blank(self):
        """Testing WebAPIResource.serialize_object with ?only-links="""
        class TestObject(object):
            field1 = 'abc'
            field2 = 'def'
            field3 = 'ghi'

        class TestResource(WebAPIResource):
            allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
            fields = {
                'field1': {
                    'type': StringFieldType,
                },
                'field2': {
                    'type': StringFieldType,
                },
                'field3': {
                    'type': StringFieldType,
                },
            }

        request = RequestFactory().get('/api/test/?only-links=')
        resource = TestResource()
        data = resource.serialize_object(TestObject(), request=request)

        self.assertEqual(data, {
            'field1': 'abc',
            'field2': 'def',
            'field3': 'ghi',
        })

    def test_serialize_object_with_cache_copy(self):
        """Testing WebAPIResource.serialize_object always returns a copy of
        the cached data
        """
        class TestObject(object):
            my_field = 'abc'

        request = RequestFactory().request()
        request.user = User()

        resource = WebAPIResource()
        resource.fields = {
            'my_field': {
                'type': StringFieldType,
            }
        }

        obj = TestObject()

        # We check this three times, since prior to Djblets 2.0.20, we would
        # first return a copy of the newly-generated data, then the cached
        # copy of the original data, and then the cached copy again (which
        # would no longer be untouched).
        data = resource.serialize_object(obj, request=request)
        self.assertIn('my_field', data)
        del data['my_field']

        data = resource.serialize_object(obj, request=request)
        self.assertIn('my_field', data)
        del data['my_field']

        data = resource.serialize_object(obj, request=request)
        self.assertIn('my_field', data)

    def _test_mimetype_responses(self, resource, url, json_mimetype,
                                 xml_mimetype, **kwargs):
        self._test_mimetype_response(resource, url, '*/*', json_mimetype,
                                     **kwargs)
        self._test_mimetype_response(resource, url, 'application/json',
                                     json_mimetype, **kwargs)
        self._test_mimetype_response(resource, url, json_mimetype,
                                     json_mimetype, **kwargs)
        self._test_mimetype_response(resource, url, 'application/xml',
                                     xml_mimetype, **kwargs)
        self._test_mimetype_response(resource, url, xml_mimetype, xml_mimetype,
                                     **kwargs)

    def _test_mimetype_response(self, resource, url, accept_mimetype,
                                response_mimetype, method='get',
                                view_kwargs={}):
        func = getattr(self.factory, method)

        if accept_mimetype:
            request = func(url, HTTP_ACCEPT=accept_mimetype)
        else:
            request = func(url)

        response = resource(request, **view_kwargs)
        print(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], response_mimetype)

    def test_serialize_object_with_circular_references(self):
        """Testing WebAPIResource.serialize_object with circular references and
        ?expand=
        """
        class TestObject(Model):
            def __init__(self, name, pk):
                super(TestObject, self).__init__()

                self.name = name
                self.pk = pk  # Django 1.8+ requires a pk field

        class TestResource(BaseTestWebAPIResource):
            fields = {
                'dependency': {
                    'type': [TestObject],
                },
                'name': {
                    'type': StringFieldType,
                }
            }

        try:
            obj1 = TestObject('obj1', 1)
            obj2 = TestObject('obj2', 2)

            obj1.dependency = obj2
            obj2.dependency = obj1

            request = RequestFactory().get('/api/test/?expand=dependency')
            resource = TestResource()
            register_resource_for_model(TestObject, resource)
            data = resource.serialize_object(obj1, request=request)

            self.maxDiff = 100000
            self.assertEqual(data, {
                '_expanded': {
                    'dependency': {
                        'item_mimetype':
                            'application/vnd.djblets-test.testresource+json',
                    },
                },
                'dependency': {
                    'links': {
                        'dependency': {
                            'href': None,
                            'method': 'GET',
                            'title': 'TestObject object',
                        },
                        'self': {
                            'href': 'http://testserver/api/test/?expand=dependency',
                            'method': 'GET',
                        },
                    },
                    'name': 'obj2',
                },
                'links': {
                    'self': {
                        'href': 'http://testserver/api/test/?expand=dependency',
                        'method': 'GET',
                    },
                },
                'name': 'obj1',
            })
        finally:
            unregister_resource_for_model(TestObject)

    def _test_item_mimetype_responses(self, resource, url, json_mimetype,
                                      xml_mimetype, json_item_mimetype,
                                      xml_item_mimetype, **kwargs):
        self._test_item_mimetype_response(resource, url, '*/*',
                                          json_item_mimetype, **kwargs)
        self._test_item_mimetype_response(resource, url, 'application/json',
                                          json_item_mimetype, **kwargs)
        self._test_item_mimetype_response(resource, url, json_mimetype,
                                          json_item_mimetype, **kwargs)
        self._test_item_mimetype_response(resource, url, 'application/xml',
                                          xml_item_mimetype, **kwargs)
        self._test_item_mimetype_response(resource, url, xml_mimetype,
                                          xml_item_mimetype, **kwargs)

    def _test_item_mimetype_response(self, resource, url, accept_mimetype,
                                     response_item_mimetype=None,
                                     method='get', view_kwargs={}):
        func = getattr(self.factory, method)

        if accept_mimetype:
            request = func(url, HTTP_ACCEPT=accept_mimetype)
        else:
            request = func(url)

        response = resource(request, **view_kwargs)
        print(response)
        self.assertEqual(response.status_code, 200)

        if response_item_mimetype:
            self.assertEqual(response['Item-Content-Type'],
                             response_item_mimetype)
        else:
            self.assertTrue('Item-Content-Type' not in response)
