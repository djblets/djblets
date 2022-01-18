"""JavaScript-related template tags."""

import json

from django import template
from django.core.serializers import serialize
from django.db.models.query import QuerySet
from django.template.defaultfilters import escapejs
from django.utils.encoding import force_str
from django.utils.safestring import mark_safe

from djblets.util.serializers import DjbletsJSONEncoder


register = template.Library()

_safe_js_escapes = {
    ord('&'): '\\u0026',
    ord('<'): '\\u003C',
    ord('>'): '\\u003E',
}


@register.simple_tag
def form_dialog_fields(form):
    """
    Translates a Django Form object into a JavaScript list of fields.
    The resulting list of fields can be used to represent the form
    dynamically.
    """
    s = ''

    for field in form:
        s += "{ name: '%s', " % escapejs(field.name)

        if field.is_hidden:
            s += "hidden: true, "
        else:
            s += "label: '%s', " % escapejs(field.label_tag(field.label + ":"))

            if field.field.required:
                s += "required: true, "

            if field.field.help_text:
                s += "help_text: '%s', " % escapejs(field.field.help_text)

        s += "widget: '%s' }," % escapejs(str(field))

    # Chop off the last ','
    return "[ %s ]" % s[:-1]


@register.filter
def json_dumps(value, indent=None):
    if isinstance(value, QuerySet):
        result = serialize('json', value, indent=indent)
    else:
        result = json.dumps(value,
                            indent=indent,
                            cls=DjbletsJSONEncoder,
                            sort_keys=True)

    return mark_safe(force_str(result).translate(_safe_js_escapes))


@register.filter
def json_dumps_items(d, append=''):
    """Dumps a list of keys/values from a dictionary, without braces.

    This works very much like ``json_dumps``, but doesn't output the
    surrounding braces. This allows it to be used within a JavaScript
    object definition alongside other custom keys.

    If the dictionary is not empty, and ``append`` is passed, it will be
    appended onto the results. This is most useful when you want to append
    a comma after all the dictionary items, in order to provide further
    keys in the template.
    """
    if not d:
        return ''

    return mark_safe(json_dumps(d)[1:-1] + append)
