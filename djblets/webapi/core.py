#
# core.py -- Core classes for webapi
#
# Copyright (c) 2007-2009  Christian Hammond
# Copyright (c) 2007-2009  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#


from cStringIO import StringIO
from xml.sax.saxutils import XMLGenerator

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.db.models.query import QuerySet
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse, Http404
from django.utils import simplejson
from django.utils.encoding import force_unicode

from djblets.webapi.errors import INVALID_FORM_DATA, INVALID_ATTRIBUTE


class WebAPIEncoder(object):
    """
    Encodes an object into a dictionary of fields and values.

    This object is used for both JSON and XML API formats.

    Projects can subclass this to provide representations of their objects.
    To make use of a encoder, add the path to the encoder class to
    the project's settings.WEB_API_ENCODERS list.

    For example:

    WEB_API_ENCODERS = (
        'myproject.webapi.MyEncoder',
    )
    """

    def encode(self, o, *args, **kwargs):
        """
        Encodes an object.

        This is expected to return either a dictionary or a list. If the
        object being encoded is not supported, return None, or call
        the superclass's encode method.
        """
        return None


class BasicAPIEncoder(WebAPIEncoder):
    """
    A basic encoder that encodes dates, times, QuerySets, Users, and Groups.
    """
    def encode(self, o, *args, **kwargs):
        if isinstance(o, QuerySet):
            return list(o)
        elif isinstance(o, User):
            return {
                'id': o.id,
                'username': o.username,
                'first_name': o.first_name,
                'last_name': o.last_name,
                'fullname': o.get_full_name(),
                'email': o.email,
                'url': o.get_absolute_url(),
            }
        elif isinstance(o, Group):
            return {
                'id': o.id,
                'name': o.name,
            }
        else:
            try:
                return DjangoJSONEncoder().default(o)
            except TypeError:
                return None


class JSONEncoderAdapter(simplejson.JSONEncoder):
    """
    Adapts a WebAPIEncoder to be used with simplejson.

    This takes an existing encoder and makes it available to use as a
    simplejson.JSONEncoder. This is used internally when generating JSON
    from a WebAPIEncoder, but can be used in other projects for more specific
    purposes as well.
    """

    def __init__(self, encoder, *args, **kwargs):
        simplejson.JSONEncoder.__init__(self, *args, **kwargs)
        self.encoder = encoder

    def encode(self, o, *args, **kwargs):
        self.encode_args = args
        self.encode_kwargs = kwargs
        return super(JSONEncoderAdapter, self).encode(o)

    def default(self, o):
        """
        Encodes an object using the supplied WebAPIEncoder.

        If the encoder is unable to encode this object, a TypeError is raised.
        """
        result = self.encoder.encode(o, *self.encode_args, **self.encode_kwargs)

        if result is None:
            raise TypeError("%r is not JSON serializable" % (o,))

        return result


class XMLEncoderAdapter(object):
    """
    Adapts a WebAPIEncoder to output XML.

    This takes an existing encoder and adapts it to output a simple XML format.
    """

    def __init__(self, encoder, *args, **kwargs):
        self.encoder = encoder

    def encode(self, o, *args, **kwargs):
        self.level = 0
        self.doIndent = False

        stream = StringIO()
        self.xml = XMLGenerator(stream, settings.DEFAULT_CHARSET)
        self.xml.startDocument()
        self.startElement("rsp")
        self.__encode(o, *args, **kwargs)
        self.endElement("rsp")
        self.xml.endDocument()
        self.xml = None

        return stream.getvalue()

    def __encode(self, o, *args, **kwargs):
        if isinstance(o, dict):
            for key, value in o.iteritems():
                self.startElement(key)
                self.__encode(value, *args, **kwargs)
                self.endElement(key)
        elif isinstance(o, list):
            self.startElement("array")

            for i in o:
                self.startElement("item")
                self.__encode(i, *args, **kwargs)
                self.endElement("item")

            self.endElement("array")
        elif isinstance(o, basestring):
            self.text(o)
        elif isinstance(o, int):
            self.text("%d" % o)
        elif isinstance(o, bool):
            if o:
                self.text("True")
            else:
                self.text("False")
        elif o is None:
            pass
        else:
            result = self.encoder.encode(o, *args, **kwargs)

            if result is None:
                raise TypeError("%r is not XML serializable" % (o,))

            return self.__encode(result, *args, **kwargs)

    def startElement(self, name, attrs={}):
        self.addIndent()
        self.xml.startElement(name, attrs)
        self.level += 1
        self.doIndent = True

    def endElement(self, name):
        self.level -= 1
        self.addIndent()
        self.xml.endElement(name)
        self.doIndent = True

    def text(self, value):
        self.xml.characters(value)
        self.doIndent = False

    def addIndent(self):
        if self.doIndent:
            self.xml.ignorableWhitespace('\n' + ' ' * self.level)


class WebAPIResponse(HttpResponse):
    """
    An API response, formatted for the desired file format.
    """
    def __init__(self, request, obj={}, stat='ok', api_format="json",
                 status=200, headers={}):
        if api_format == "json":
            if request.FILES:
                # When uploading a file using AJAX to a webapi view,
                # we must set the mimetype to text/plain. If we use
                # application/json instead, the browser will ask the user
                # to save the file. It's not great, but it's what we must do.
                mimetype = "text/plain"
            else:
                mimetype = "application/json"
        elif api_format == "xml":
            mimetype = "application/xml"
        else:
            self.status_code = 400
            self.content_set = True
            return

        super(WebAPIResponse, self).__init__(mimetype=mimetype,
                                             status=status)
        self.callback = request.GET.get('callback', None)
        self.api_data = {'stat': stat}
        self.api_data.update(obj)
        self.api_format = api_format
        self.content_set = False

        for header, value in headers.iteritems():
            self[header] = value

    def _get_content(self):
        """
        Returns the API response content in the appropriate format.

        This is an overridden version of HttpResponse._get_content that
        generates the resulting content when requested, rather than
        generating it up-front in the constructor. This is used so that
        the @webapi decorator can set the appropriate API format before
        the content is generated, but after the response is created.
        """
        class MultiEncoder(WebAPIEncoder):
            def encode(self, *args, **kwargs):
                for encoder in get_registered_encoders():
                    result = encoder.encode(*args, **kwargs)

                    if result is not None:
                        return result

                return None

        if not self.content_set:
            adapter = None
            encoder = MultiEncoder()

            if self.api_format == "json":
                adapter = JSONEncoderAdapter(encoder)
            elif self.api_format == "xml":
                adapter = XMLEncoderAdapter(encoder)
            else:
                assert False

            content = adapter.encode(self.api_data, api_format=self.api_format)

            if self.callback != None:
                content = "%s(%s);" % (self.callback, content)

            self.content = content
            self.content_set = True

        return super(WebAPIResponse, self)._get_content()

    def _set_content(self, value):
        super(WebAPIResponse, self)._set_content(value)

    content = property(_get_content, _set_content)


class WebAPIResponsePaginated(WebAPIResponse):
    """
    A response containing a list of results with pagination.

    This accepts the following parameters to the URL:

    * start - The index of the first item (0-based index).
    * max-results - The maximum number of results to return in the request.
    """
    def __init__(self, request, queryset, results_key="results",
                 prev_key="prev_href", next_key="next_href",
                 total_results_key="total_results",
                 default_max_results=25, max_results_cap=200,
                 *args, **kwargs):
        try:
            start = int(request.GET.get('start', 0))
        except ValueError:
            start = 0

        try:
            max_results = \
                min(int(request.GET.get('max-results', default_max_results)),
                    max_results_cap)
        except ValueError:
            max_results = default_max_results

        results = list(queryset[start:start + max_results])
        total_results = queryset.count()

        data = {
            results_key: results,
            total_results_key: total_results,
        }

        if start > 0:
            data[prev_key] = "%s?start=%s&max-results=%s" % \
                             (request.path, max(start - max_results, 0),
                              max_results)

        if start + len(results) < total_results:
            data[next_key] = "%s?start=%s&max-results=%s" % \
                             (request.path, start + max_results, max_results)

        WebAPIResponse.__init__(self, request, obj=data, *args, **kwargs)


class WebAPIResponseError(WebAPIResponse):
    """
    A general error response, containing an error code and a human-readable
    message.
    """
    def __init__(self, request, err, extra_params={}, *args, **kwargs):
        errdata = {
            'err': {
                'code': err.code,
                'msg': err.msg
            }
        }
        errdata.update(extra_params)

        WebAPIResponse.__init__(self, request, obj=errdata, stat="fail",
                                status=err.http_status, headers=err.headers,
                                *args, **kwargs)


class WebAPIResponseFormError(WebAPIResponseError):
    """
    An error response class designed to return all errors from a form class.
    """
    def __init__(self, request, form, *args, **kwargs):
        fields = {}

        for field in form.errors:
            fields[field] = [force_unicode(e) for e in form.errors[field]]

        WebAPIResponseError.__init__(self, request, INVALID_FORM_DATA, {
            'fields': fields
        }, *args, **kwargs)


class WebAPIResource(object):
    model = None
    uri_id_key = None
    object_result_key = None
    list_result_key = None
    fields = ()

    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    method_mapping = {
        'GET': 'get',
        'POST': 'create',
        'PUT': 'update',
        'DELETE': 'delete',
    }

    def __call__(self, request, api_format="json", *args, **kwargs):
        method = request.GET.get('method', request.method)

        if method in self.allowed_methods:
            if method == "GET" and self.uri_id_key not in kwargs:
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
                return WebAPIResponseError(self.request, err=result,
                                           api_format=api_format)
            elif isinstance(result, tuple):
                if isinstance(result[0], WebAPIError):
                    return WebAPIResponseError(self.request,
                                               err=result[0],
                                               obj=result[1],
                                               api_format=api_format)
                else:
                    return WebAPIResponse(self.request,
                                          status=result[0],
                                          obj=result[1],
                                          api_format=api_format)
        else:
            return HttpResponseNotAllowed(self.allowed_methods)

    @webapi_check_login_required
    def get(self, request, *args, **kwargs):
        if not self.model:
            return HttpResponseNotAllowed(self.allowed_methods)

        try:
            queryset = self.get_queryset(request, *args, **kwargs)
            obj = queryset.filter(pk=kwargs[self.uri_id_key])
        except self.model.DoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_access_permissions(request, obj, *args, **kwargs):
            return PERMISSION_DENIED

        return 200, {
            self.object_result_key: self.serialize_object(obj),
        }

    @webapi_check_login_required
    def get_list(self, request, *args, **kwargs):
        if not self.model:
            return HttpResponseNotAllowed(self.allowed_methods)

        list_result_key = self.list_result_key or self.object_result_key + 's'

        # TODO: Paginate this.
        return 200, {
            list_result_key: self.get_queryset(request, is_list=True,
                                               *args, **kwargs),
        }

    @webapi_login_required
    def create(self, request, api_format, *args, **kwargs):
        return HttpResponseNotAllowed(self.allowed_methods)

    @webapi_login_required
    def update(self, request, api_format, *args, **kwargs):
        return HttpResponseNotAllowed(self.allowed_methods)

    @webapi_login_required
    def delete(self, request, api_format, *args, **kwargs):
        if not self.model:
            return HttpResponseNotAllowed(self.allowed_methods)

        try:
            queryset = self.get_queryset(request, *args, **kwargs)
            obj = queryset.filter(pk=kwargs[self.uri_id_key])
        except self.model.DoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_delete_permissions(request, obj, *args, **kwargs):
            return PERMISSION_DENIED

        obj.delete()

        return 204, {}

    def get_queryset(self, request, *args, **kwargs):
        return self.model.all()

    def has_access_permissions(self, request, obj, *args, **kwargs):
        return True

    def has_delete_permissions(self, request, obj, *args, **kwargs):
        return True

    def serialize_object(self, obj):
        data = {}

        for field in self.fields:
            serialize_func = getattr(self, "serialize_%s_field" % field, None)

            if serialize_func and callable(serialize_func):
                value = serialize_func(obj)
            else:
                value = obj.getattr(field)

                if isinstance(value, models.ManyToManyField):
                    value = value.all()
                elif isinstance(value, models.ForeignKey):
                    value = value.get()

            data[field] = value

        return data


__registered_encoders = None

def get_registered_encoders():
    """
    Returns a list of registered Web API encoders.
    """
    global __registered_encoders

    if __registered_encoders is None:
        __registered_encoders = []

        try:
            encoders = settings.WEB_API_ENCODERS
        except AttributeError:
            encoders = (BasicAPIEncoder,)

        for encoder in encoders:
            encoder_path = encoder.split('.')
            if len(encoder_path) > 1:
                encoder_module_name = '.'.join(encoder_path[:-1])
            else:
                encoder_module_name = '.'

            encoder_module = __import__(encoder_module_name, {}, {},
                                        encoder_path[-1])
            encoder_class = getattr(encoder_module, encoder_path[-1])
            __registered_encoders.append(encoder_class())

    return __registered_encoders
