#
# djblets_js.py -- JavaScript-related template tags
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

from __future__ import unicode_literals

import json

from django import template
from django.core.serializers import serialize
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.query import QuerySet
from django.utils import six
from django.utils.encoding import force_text
from django.utils.functional import Promise
from django.utils.safestring import mark_safe


register = template.Library()


class LazyEncoder(DjangoJSONEncoder):
    """
    Encoder to take care of initializing lazily created ugettext messages.

    In the case of lazy translation objects, they need to be converted to
    strings before passed as a JSON object. If the passed object is a
    Promise, do a force_text on it to resolve the Promise.
    """
    def default(self, obj):
        if isinstance(obj, Promise):
            return force_text(obj)

        return super(LazyEncoder, self).default(obj)


@register.simple_tag
def form_dialog_fields(form):
    """
    Translates a Django Form object into a JavaScript list of fields.
    The resulting list of fields can be used to represent the form
    dynamically.
    """
    s = ''

    for field in form:
        s += "{ name: '%s', " % field.name

        if field.is_hidden:
            s += "hidden: true, "
        else:
            s += "label: '%s', " % field.label_tag(field.label + ":")

            if field.field.required:
                s += "required: true, "

            if field.field.help_text:
                s += "help_text: '%s', " % field.field.help_text

        s += "widget: '%s' }," % six.text_type(field)

    # Chop off the last ','
    return "[ %s ]" % s[:-1]


@register.filter
def json_dumps(value, indent=None):
    if isinstance(value, QuerySet):
        result = serialize('json', value, indent=indent)
    else:
        result = json.dumps(value, indent=indent, cls=LazyEncoder)

    return mark_safe(result)
