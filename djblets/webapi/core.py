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
from django.http import HttpResponse
from django.utils import simplejson
from django.utils.encoding import force_unicode

from djblets.util.http import get_http_requested_mimetype
from djblets.webapi.errors import INVALID_FORM_DATA


SPECIAL_PARAMS = ('api_format', 'callback', '_method', 'expand')


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
                attrs = {}

                if isinstance(key, (int, long)):
                    attrs['value'] = str(key)
                    key = 'int'

                self.startElement(key, attrs)
                self.__encode(value, *args, **kwargs)
                self.endElement(key)
        elif isinstance(o, (tuple, list)):
            self.startElement("array")

            for i in o:
                self.startElement("item")
                self.__encode(i, *args, **kwargs)
                self.endElement("item")

            self.endElement("array")
        elif isinstance(o, basestring):
            self.text(o)
        elif isinstance(o, (int, long)):
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
    supported_mimetypes = [
        'application/json',
        'application/xml',
    ]

    def __init__(self, request, obj={}, stat='ok', api_format=None,
                 status=200, headers={}, encoders=[]):
        if not api_format:
            if request.method == 'GET':
                api_format = request.GET.get('api_format', None)
            else:
                api_format = request.POST.get('api_format', None)

        if not api_format:
            mimetype = get_http_requested_mimetype(request, self.supported_mimetypes)
        elif api_format == "json":
            mimetype = 'application/json'
        elif api_format == "xml":
            mimetype = 'application/xml'
        else:
            mimetype = None

        if not mimetype:
            self.status_code = 400
            self.content_set = True
            return

        if mimetype == 'application/json' and request.FILES:
            # When uploading a file using AJAX to a webapi view,
            # we must set the mimetype to text/plain. If we use
            # application/json instead, the browser will ask the user
            # to save the file. It's not great, but it's what we must do.
            mimetype = 'text/plain'

        super(WebAPIResponse, self).__init__(mimetype=mimetype,
                                             status=status)
        self.request = request
        self.callback = request.GET.get('callback', None)
        self.api_data = {'stat': stat}
        self.api_data.update(obj)
        self.content_set = False
        self.mimetype = mimetype
        self.encoders = encoders or get_registered_encoders()

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
            def __init__(self, encoders):
                self.encoders = encoders

            def encode(self, *args, **kwargs):
                for encoder in self.encoders:
                    result = encoder.encode(*args, **kwargs)

                    if result is not None:
                        return result

                return None

        if not self.content_set:
            adapter = None
            encoder = MultiEncoder(self.encoders)

            # See the note above about the check for text/plain.
            if self.mimetype in ['application/json', 'text/plain']:
                adapter = JSONEncoderAdapter(encoder)
            elif self.mimetype == "application/xml":
                adapter = XMLEncoderAdapter(encoder)
            else:
                assert False

            content = adapter.encode(self.api_data, request=self.request)

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
                 prev_key="prev", next_key="next",
                 total_results_key="total_results",
                 default_max_results=25, max_results_cap=200,
                 serialize_object_func=None,
                 extra_data={}, *args, **kwargs):
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

        results = queryset[start:start + max_results]

        if serialize_object_func:
            results = [serialize_object_func(obj)
                       for obj in results]
        else:
            results = list(results)

        total_results = queryset.count()

        data = {
            results_key: results,
            total_results_key: total_results,
        }
        data.update(extra_data)

        full_path = request.build_absolute_uri(request.path)

        if start > 0:
            data['links'][prev_key] = {
                'method': 'GET',
                'href': '%s?start=%s&max-results=%s' %
                        (full_path, max(start - max_results, 0), max_results),
            }

        if start + len(results) < total_results:
            data['links'][next_key] = {
                'method': 'GET',
                'href': '%s?start=%s&max-results=%s' %
                        (full_path, start + max_results, max_results),
            }

        WebAPIResponse.__init__(self, request, obj=data, *args, **kwargs)


class WebAPIResponseError(WebAPIResponse):
    """
    A general error response, containing an error code and a human-readable
    message.
    """
    def __init__(self, request, err, extra_params={}, headers={},
                 *args, **kwargs):
        errdata = {
            'err': {
                'code': err.code,
                'msg': err.msg
            }
        }
        errdata.update(extra_params)

        headers = headers.copy()
        headers.update(err.headers)

        WebAPIResponse.__init__(self, request, obj=errdata, stat="fail",
                                status=err.http_status, headers=headers,
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
            encoders = ('BasicAPIEncoder',)

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


# Backwards-compatibility
#
# This must be done after the classes in order to avoid a
# circular import problem.
from djblets.webapi.encoders import BasicAPIEncoder
