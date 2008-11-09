from cStringIO import StringIO
from xml.sax.saxutils import XMLGenerator

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.db.models.query import QuerySet
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse, Http404
from django.utils import simplejson
from django.utils.encoding import force_unicode

from djblets.webapi.errors import INVALID_FORM_DATA


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

    def encode(self, o):
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
    def encode(self, o):
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

    def default(self, o):
        """
        Encodes an object using the supplied WebAPIEncoder.

        If the encoder is unable to encode this object, a TypeError is raised.
        """
        result = self.encoder.encode(o)

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

    def encode(self, o):
        self.level = 0
        self.doIndent = False

        stream = StringIO()
        self.xml = XMLGenerator(stream, settings.DEFAULT_CHARSET)
        self.xml.startDocument()
        self.startElement("rsp")
        self.__encode(o)
        self.endElement("rsp")
        self.xml.endDocument()
        self.xml = None

        return stream.getvalue()

    def __encode(self, o):
        if isinstance(o, dict):
            for key, value in o.iteritems():
                self.startElement(key)
                self.__encode(value)
                self.endElement(key)
        elif isinstance(o, list):
            self.startElement("array")

            for i in o:
                self.startElement("item")
                self.__encode(i)
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
            result = self.encoder.encode(o)

            if result is None:
                raise TypeError("%r is not XML serializable" % (o,))

            return self.__encode(result)

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
    def __init__(self, request, obj={}, stat='ok', api_format="json"):
        super(WebAPIResponse, self).__init__()
        self.callback = request.GET.get('callback', None)
        self.api_data = {'stat': stat}
        self.api_data.update(obj)
        self.api_format = api_format

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
            def encode(self, o):
                for encoder in get_registered_encoders():
                    result = encoder.encode(o)

                    if result is not None:
                        return result

                return None


        if self.api_format == "json":
            content = JSONEncoderAdapter(MultiEncoder()).encode(self.api_data)
            self.mimetype = "application/json"
        elif self.api_format == "xml":
            content = XMLEncoderAdapter(MultiEncoder()).encode(self.api_data)
            self.mimetype = "application/xml"
        else:
            raise Http404

        if self.callback != None:
            content = "%s(%s);" % (self.callback, content)

        self.content = content

        return super(WebAPIResponse, self)._get_content()

    def _set_content(self, value):
        super(WebAPIResponse, self)._set_content(value)

    content = property(_get_content, _set_content)


class WebAPIResponseError(WebAPIResponse):
    """
    A general error response, containing an error code and a human-readable
    message.
    """
    def __init__(self, request, err, extra_params={}, api_format="json"):
        errdata = {
            'err': {
                'code': err.code,
                'msg': err.msg
            }
        }
        errdata.update(extra_params)

        WebAPIResponse.__init__(self, request, obj=errdata,
                                api_format=api_format, stat="fail")


class WebAPIResponseFormError(WebAPIResponseError):
    """
    An error response class designed to return all errors from a form class.
    """
    def __init__(self, request, form, api_format="json"):
        fields = {}

        for field in form.errors:
            fields[field] = [force_unicode(e) for e in form.errors[field]]

        WebAPIResponseError.__init__(self, request, INVALID_FORM_DATA, {
            'fields': fields
        }, api_format=api_format)


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
