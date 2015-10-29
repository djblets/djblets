#
# djblets_utils.py -- Various utility template tags
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

import datetime
import os

from django import template
from django.template import TemplateSyntaxError
from django.template.defaultfilters import stringfilter
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.six.moves.urllib.parse import urlencode
from django.utils.timezone import is_aware

from djblets.util.decorators import basictag, blocktag
from djblets.util.dates import get_tz_aware_utcnow
from djblets.util.http import get_url_params_except
from djblets.util.humanize import humanize_list


register = template.Library()


@register.tag
@blocktag
def definevar(context, nodelist, varname):
    """Define a variable for later use in the template.

    The variable defined can be used within the same context (such as the
    same block or for loop). This is useful for caching a portion of a
    template that would otherwise be expensive to repeatedly compute.

    Args:
        varname (unicode):
            The variable name.

        block_content (unicode):
            The block content to set in the variable.

    Example:
        .. code-block:: html+django

           {% definevar "myvar" %}{% expensive_tag %}{% enddefinevar %}

           {{myvar}}
           {{myvar}}
    """
    context[varname] = nodelist.render(context)
    return ""


@register.tag
@blocktag
def ifuserorperm(context, nodelist, user, perm):
    """Render content only for a given user or a user with a given permission.

    The content will only be rendered if the logged in user matches the
    specified user, or the logged in user has the specified permission.

    This is useful when you want to restrict some content to the owner of an
    object or to a privileged user that has the abilities of the owner.

    Args:
        user (django.contrib.auth.models.User):
            The user to limit access to, unless the logged in user has the
            specified permission.

        perm (unicode):
            The permission to require, if the logged in user does not match
            the specified user.

        block_content (unicode):
            The block content to render.

    Returns:
        The content, if the user or permission matches. Otherwise, no content
        will be returned.

    Example:
        .. code-block:: html+django

           {% ifuserorperm myobject.user "myobject.can_change_status" %}
           Owner-specific content here...
           {% endifuserorperm %}
    """
    if _check_userorperm(context, user, perm):
        return nodelist.render(context)

    return ''


@register.tag
@blocktag
def ifnotuserandperm(context, nodelist, user, perm):
    """Render content if a user and permission don't match the logged in user.

    This is the opposite of :py:func:`{% ifuserorperm %} <ifuserorperm>`. It
    will only render content if the logged in user is not the specified user
    and doesn't have the specified permission.

    Args:
        user (django.contrib.auth.models.User):
            The user who cannot see the provided content.

        perm (unicode):
            Any user with this permission will not see the provided content.

        block_content (unicode):
            The block content to render.

    Returns:
        The content, if neither the user nor permission matches. Otherwise, no
        content will be returned.

    Example:
        .. code-block:: html+django

           {% ifuserorperm myobject.user "myobject.can_change_status" %}
           Owner-specific content here...
           {% endifuserorperm %}

           {% ifnotuserandperm myobject.user "myobject.can_change_status" %}
           Another owner-specific content here...
           {% endifnotuserandperm %}
    """
    if not _check_userorperm(context, user, perm):
        return nodelist.render(context)

    return ''


def _check_userorperm(context, user, perm):
    from django.contrib.auth.models import AnonymousUser, User

    req_user = context.get('user', None)

    if isinstance(req_user, AnonymousUser):
        return False

    if req_user.has_perm(perm):
        return True

    return ((isinstance(user, User) and user == req_user) or
            user == req_user.pk)


@register.tag
@basictag(takes_context=True)
def include_as_string(context, template_name):
    """Include the contents of a template as an escaped string.

    This is primarily for use with JavaScript. It allows another template
    to be rendered (with the current context) and returned as an escaped
    string.

    Args:
        template_name (unicode):
            The name of the template to render.

    Returns:
        The escaped content from the template.

    Example:
        .. code-block:: html+django

           <script>
           var s = {% include_as_string "message.txt" %};
           </script>
    """
    s = render_to_string(template_name, context)
    s = s.replace("'", "\\'")
    s = s.replace("\n", "\\\n")
    return "'%s'" % s


@register.tag
@blocktag
def attr(context, nodelist, attrname):
    """Set an HTML attribute to a value if the value is not an empty string.

    This is a handy way of adding attributes with non-empty values to an
    HTML element without requiring several `{% if %}` tags.

    Args:
        attrname (unicode):
            The name for the HTML attribute.

        block_content (unicode):
            The block content to render for the attribute value.

    Returns:
        An attribute in the form of ``key="value"``, if the value (the
        block content) is not empty.

    Example:
        .. code-block:: html+django

           <div{% attr "data-description" %}{{obj.description}}{% endattr %}>
    """
    content = nodelist.render(context)

    if content.strip() == "":
        return ""

    return ' %s="%s"' % (attrname, content)


@register.filter
def escapespaces(value):
    """HTML-escape all spaces with ``&nbsp;`` and newlines with ``<br />``.

    Args:
        value (unicode):
            The value to escape.

    Returns:
        unicode:
        The same text, but escaped.

    Example:
        .. code-block:: html+django

           <div class="text">
            {{obj.description|escapespaces}}
           </div>
    """
    return value.replace('  ', '&nbsp; ').replace('\n', '<br />')


@register.simple_tag
def ageid(timestamp):
    """Return an ID based on the difference between now and a timestamp.

    This can be used to help show the age of an item in days. It will
    generate an ID in the form of :samp:`age{num}` ranging from
    ``age1`` (today) through ``age5`` (4+ days old).

    This is a specialty function, and is not expected to be useful in many
    cases.

    Args:
        timestamp (datetime.datetime):
            The timestamp to compare to.

    Returns:
        unicode:
        The ID. One of ``age1``, ``age2``, ``age3``, ``age4``, or ``age5``.

    Example:
        .. code-block:: html+django

           <div class="{% ageid obj.timestamp %}">
            {{obj.timestamp}}
           </div>
    """
    if timestamp is None:
        return ""

    # Convert datetime.date into datetime.datetime
    if timestamp.__class__ is not datetime.datetime:
        timestamp = datetime.datetime(timestamp.year, timestamp.month,
                                      timestamp.day)

    now = datetime.datetime.utcnow()

    if is_aware(timestamp):
        now = get_tz_aware_utcnow()

    delta = now - (timestamp -
                   datetime.timedelta(0, 0, timestamp.microsecond))

    if delta.days == 0:
        return "age1"
    elif delta.days == 1:
        return "age2"
    elif delta.days == 2:
        return "age3"
    elif delta.days == 3:
        return "age4"
    else:
        return "age5"


@register.filter
def user_displayname(user):
    """Return the display name of a user.

    If the user has a full name set, it will be returned. Otherwise, the
    username will be returned.

    Args:
        user (django.contrib.auth.models.User):
            The user whose full name or username will be returned.

    Returns:
        unicode:
        The full name of the user, if set, or the username as a fallback.

    Example:
        .. code-block:: html+django

           Welcome, {{user|user_displayname}}!
    """
    return user.get_full_name() or user.username


register.filter('humanize_list', humanize_list)


@register.filter
def contains(container, value):
    """Return whether the specified value is in the specified container.

    This is equivalent to a ``if value in container`` statement in Python.

    Args:
        container (object):
            The list, dictionary, or other object that may or may not
            contain the value.

        value (object):
            The value being checked.

    Returns:
        bool:
        ``True`` if the value is in the container. Otherwise, ``False``.

    Example:
        .. code-block:: html+django

           {% if usernames|contains:"bob" %}
             Hi, Bob!
           {% endif %}
    """
    return value in container


@register.filter
def getitem(container, key):
    """Return the attribute of a specified name from a container.

    This is equivalent to a ``container[key]`` statement in Python. The
    container must support this operator.

    Args:
        container (object):
            The list, dictionary, or other object that can contain items.

        key (object):
            The key to look up in the container.

    Returns:
        object: The content within the container.

    Example:
        .. code-block:: html+django

           {% for key in keys %}
             {{key}}: {{obj|getitem:key}}
           {% endfor %}
    """
    return container[key]


@register.filter
def exclude_item(container, item):
    """Return a list with the given item excluded.

    Args:
        container (list):
            The list the item will be excluded from.

        item (object):
            The item to exclude from the list.

    Returns:
        list: The list with the item excluded.

    Example:
        .. code-block:: html+django

           {% for item in mylist|exclude_item:"special" %}
             ...
           {% endfor %}
    """
    if not isinstance(container, list):
        raise TemplateSyntaxError("remove_item expects a list")

    container = list(container)

    try:
        container.remove(item)
    except ValueError:
        pass

    return container


@register.filter
def indent(value, numspaces=4):
    """Indent a string by the specified number of spaces.

    This is especially useful for preformatted content.

    Args:
        value (unicode):
            The value containing text to indent.

        numspaces (int, optional):
            The number of spaces to indent the text. Defaults to 4 spaces.

    Returns:
        unicode: The indented text.

    Example:
        .. code-block:: html+django

           <pre>
           The traceback was:

           {{traceback|indent:2}}
           </pre>
    """
    indent_str = ' ' * numspaces
    return indent_str + value.replace('\n', '\n' + indent_str)


@register.filter
def basename(path):
    """Return the base name of a path.

    This will be computed based on the path rules from the system the
    server is running on.

    Args:
        path (unicode):
            The path for which to retrieve the base name.

    Returns:
        unicode:
        The base name of the path.

    Example:
        .. code-block:: html+django

           The file is contained within <tt>{{path|basename}}</tt>.
    """
    return os.path.basename(path)


@register.filter(name="range")
def range_filter(value):
    """Turn an integer into a range of numbers.

    This is useful for iterating with the "for" tag.

    Args:
        value (int):
            The number of values in the range.

    Returns:
        list:
        The list of numbers in the range.

    Example:
        .. code-block:: html+django

            {% for i in 10|range %}
             {{i}}
            {% endfor %}
    """
    return range(value)


@register.filter
def realname(user):
    """Return the real name of a user, if available, or the username.

    If the user has a full name set, this will return the full name.
    Otherwise, this returns the username.

    .. deprecated:: 0.9

       This is deprecated in favor of :py:func:`user_displayname`.

    Args:
        user (django.contrib.auth.models.User):
            The user whose full name or username will be returned.

    Returns:
        unicode:
        The full name of the user, if set, or the username as a fallback.

    Example:
        .. code-block:: html+django

           Welcome, {{user|realname}}!
    """
    full_name = user.get_full_name()
    if full_name == '':
        return user.username
    else:
        return full_name


@register.filter
@stringfilter
def startswith(s, prefix):
    """Return whether a value starts with another value.

    Args:
        s (unicode):
            The string to check.

        prefix (unicode):
            The prefix to check for.

    Returns:
        bool:
        ``True`` if the string starts with the given prefix.

    Example:
        .. code-block:: html+django

           {% if key|startswith:"__" %}
             ..
           {% endif %}
    """
    return s.startswith(prefix)


@register.filter
@stringfilter
def endswith(s, suffix):
    """Return whether a value ends with another value.

    Args:
        s (unicode):
            The string to check.

        suffix (unicode):
            The suffix to check for.

    Returns:
        bool:
        ``True`` if the string ends with the given suffix.

    Example:
        .. code-block:: html+django

           {% if filename|endswith:".json" %}
             ..
           {% endif %}
    """
    return s.endswith(suffix)


@register.filter
@stringfilter
def paragraphs(text):
    """Return an HTML paragraph for each line of text.

    This iterates through the lines of text given and wraps each in a
    ``<p>`` tag.

    This expects that each paragraph in the string will be on its own line.
    Blank lines are filtered out.

    The text is expected to be HTML-safe already.

    Args:
        text (unicode):
            The text containing at least one line of content.

    Returns:
        unicode:
        The resulting HTML output.

    Example:
        .. code-block:: html+django

           <article>
            {{description|paragraphs}}
           </article>
    """
    s = ""

    for line in text.splitlines():
        if line:
            s += "<p>%s</p>\n" % line

    return mark_safe(s)
paragraphs.is_safe = True


@register.filter
@stringfilter
def split(s, delim=','):
    """Split a string into a list.

    The string can be split by any specified delimiter, and defaults to a
    comma.

    Args:
        s (unicode):
            The string to split.

        delim (unicode, optional):
            The delimiter to split by. Defaults to ``,``.

    Returns:
        list:
        The resulting list of tokens from the string.

    Example:
        .. code-block:: html+django

           {% for token in str|split:'\\t' %}
             ..
           {% endfor %}
    """
    return s.split(delim)


@register.tag
@basictag(takes_context=True)
def querystring_with(context, attr, value):
    """Return the current page URL with a new query string argument added.

    This makes it easy to add to or replace part of a query string for the
    current page's URL, which may already contain a query string.

    If the page URL already has a query string, a new item is added in the form
    of ``&attr=value``. If it doesn't have a query string, this will start a
    new one in the form of ``?attr=value``.

    If the attribute already exists in the query string, its value will be
    replaced.

    Args:
        attr (unicode):
            The name of the attribute for the new query string argument.

        value (unicode):
            The value of the attribute for the new query string argument.

    Returns:
        unicode:
        The new URL with the modified query string.

    Example:
        .. code-block:: html+django

           <a href="{% querystring_with "sorted" "1" %}">Sort</a>
    """
    existing_query = get_url_params_except(context['request'].GET, attr)
    new_query = urlencode({attr.encode('utf-8'): value.encode('utf-8')})

    if existing_query:
        return '?%s&%s' % (existing_query, new_query)
    else:
        return '?%s' % new_query
