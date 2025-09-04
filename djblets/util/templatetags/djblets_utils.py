"""Miscellaneous utility template tags."""

from __future__ import annotations

import datetime
import os
import re
from typing import TYPE_CHECKING

from django import template
from django.http import QueryDict
from django.template import TemplateSyntaxError, Variable
from django.template.defaultfilters import stringfilter
from django.template.loader import render_to_string
from django.utils.html import escape, format_html, strip_spaces_between_tags
from django.utils.safestring import mark_safe
from django.utils.timezone import is_aware

from djblets.util.decorators import blocktag
from djblets.util.dates import get_tz_aware_utcnow
from djblets.util.http import get_url_params_except
from djblets.util.humanize import humanize_list

if TYPE_CHECKING:
    from django.template import Context


register = template.Library()


WS_RE = re.compile(r'\s+')


@register.tag
@blocktag(resolve_vars=False)
def definevar(context, nodelist, varname, *options):
    """Define a variable for later use in the template.

    The variable defined can be used within the same context (such as the
    same block or for loop). This is useful for caching a portion of a
    template that would otherwise be expensive to repeatedly compute.

    Version Added:
        2.0:
        Added the new ``global`` option.

    Version Added:
        1.0:
        Added new ``strip``, ``spaceless``, and ``unsafe`` options.

    Args:
        varname (unicode):
            The variable name.

        *options (list of unicode, optional):
            A list of options passed. This supports the following:

            ``global``:
                Register the variable in the top-level context, for other
                blocks to see.

                Note that the ordering of registration and usage is important,
                so consumers are advised to have a dedicated template block
                for this purpose. Also note that if a later block defines a
                variable with the same name, that will take precedence.

            ``strip``:
                Strip whitespace at the beginning/end of the value.

            ``spaceless``:
                Strip whitespace at the beginning/end and remove all spaces
                between tags. This implies ``strip``.

            ``unsafe``:
                Mark the text as unsafe. The contents will be HTML-escaped when
                inserted into the page.

        block_content (unicode):
            The block content to set in the variable.

    Example:
        .. code-block:: html+django

           {% definevar "myvar1" %}
           {%  expensive_tag %}
           {% enddefinevar %}

           {% definevar "myvar2" spaceless %}
           <div>
            <a href="#">Click me!</a>
           </div>
           {% enddefinevar %}

           {{myvar1}}
           {{myvar2}}
    """
    varname = Variable(varname).resolve(context)
    result = nodelist.render(context)

    if 'spaceless' in options:
        result = strip_spaces_between_tags(result.strip())
    elif 'strip' in options:
        result = result.strip()

    if 'unsafe' in options:
        result = escape(result)
    else:
        result = mark_safe(result)

    if 'global' in options:
        # Note that we're setting at index 1. That's the first mutable
        # context dictionary. Index 0 is reserved for primitives (True,
        # False, None).
        context.dicts[1][varname] = result
    else:
        context[varname] = result

    return ''


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


@register.simple_tag(takes_context=True)
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
    s = render_to_string(template_name, context.flatten())
    s = s.replace("'", "\\'")
    s = s.replace("\n", "\\\n")

    # Since this works like {% include %}, we have to trust the resulting
    # content here. It's still possible that a nefarious template could cause
    # problems, but this is the responsibility of the caller.
    #
    # In prior versions of Django (< 1.9), this was implicitly marked safe.
    return mark_safe("'%s'" % s)


@register.tag
@blocktag(resolve_vars=False)
def attr(context, nodelist, attrname, *options):
    """Set an HTML attribute to a value if the value is not an empty string.

    This is a handy way of adding attributes with non-empty values to an
    HTML element without requiring several `{% if %}` tags.

    The contents will be stripped and all whitespace within condensed before
    being considered or rendered. This can be turned off (restoring pre-1.0
    behavior) by passing ``nocondense`` as an option.

    .. versionchanged:: 1.0

       Prior to this release, all whitespace before/after/within the
       attribute value was preserved. Now ``nocondense`` is required for this
       behavior.

       The value is now escaped as well. Previously the value was assumed to
       be safe, requiring the consumer to escape the contents.

    Args:
        attrname (unicode):
            The name for the HTML attribute.

        *options (list unicode, optional):
            A list of options passed. This supports the following:

            ``nocondense``:
                Preserves all whitespace in the value.

        block_content (unicode):
            The block content to render for the attribute value.

    Returns:
        An attribute in the form of ``key="value"``, if the value (the
        block content) is not empty.

    Example:
        .. code-block:: html+django

           <div{% attr "class" %}{{obj.name}}{% endattr %}>
           <div{% attr "data-description" nocondense %}
               Space-sensitive

               whitespace
           {% endattr %}>
    """
    attrname = Variable(attrname).resolve(context)
    content = nodelist.render(context)

    if 'nocondense' not in options:
        content = WS_RE.sub(' ', content.strip())

    if not content:
        return ''

    return format_html(' {0}="{1}"', attrname, str(content))


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


@register.simple_tag(takes_context=True)
def unique_id(
    context: Context,
    prefix: str,
) -> str:
    """Output a (potentially) unique ID for a given prefix.

    The ID will be generated as a combination of the prefix and an
    auto-incrementing number. It's considered unique for the duration of a
    template render, so long as nothing else directly outputs that same
    ID.

    This can be used for DOM elements, scripts, or other use cases.

    Version Added:
        5.3

    Args:
        context (django.template.Context):
            The current template context.

        prefix (str):
            The prefix for the ID.

    Returns:
        str:
        The generated ID.

    Example:
        .. code-block:: html+django

           {% unique_id "my_component" as my_unique_id %}

           <div aria-labelledby="{{my_unique_id}}">
            <h2 id="{{my_unique_id}}">Header</h2>
           </div>
    """
    request = context['request']
    unique_ids: dict[str, int]

    try:
        unique_ids = request._djblets_tag_unique_ids
    except AttributeError:
        unique_ids = {}
        request._djblets_tag_unique_ids = unique_ids

    new_id = unique_ids.get(prefix, 0) + 1
    unique_ids[prefix] = new_id

    return f'{prefix}{new_id}'


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


@register.filter('getattr')
def getattr_filter(obj, name):
    """Return the attribute of a specified name from an object.

    This is equivalent to a ``getattr(obj, name, None)`` statement in
    Python.

    Version Added:
        2.0

    Args:
        obj (object):
            The object that contains the attribute.

        name (unicode):
            The name of the key to look up in the container.

    Returns:
        object:
        The attribute value.

    Example:
        .. code-block:: html+django

           {% for name in attrs %}
             {{name}}: {{obj|getattr:name}}
           {% endfor %}

           {{obj|getattr:other_attr|default_if_none:"my fallback"}}
    """
    return getattr(obj, name, None)


@register.filter
def getitem(container, key):
    """Return the value of a specified key from a container.

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


@register.simple_tag(takes_context=True)
def querystring(context, mode, *args):
    """Return current page URL with new query string containing multiple
    parameters.

    Args:
        context (django.template.context.RequestContext):
            The Django template rendering context.

        mode (unicode):
            How the querystring will be modified. This should be one of the
            following values:

            ``'update'``:
                Replace the values for the specified key(s) in the query
                string.

            ``'append'``:
                Add new values for the specified key(s) to the query string.

            ``'remove'``:
                Remove the specified key(s) from the query string.

                If no value is provided, all instances of the key will be
                removed.

        *args (tuple):
            Multiple querystring fragments (e.g., ``foo=1``) that will be used
            to update the initial querystring.

    Returns:
        unicode:
        The new URL with the modified query string.

    Example:
        .. code-block:: html+django

           <a href="{% querystring "update" 'a=1' 'b=2' %}">Sort</a>

           <a href="{% querystring "append" 'a=1' 'b=2' %}">Sort</a>

           <a href="{% querystring "append" 'a=1&a=2' %}">Sort</a>

           <a href="{% querystring "remove" 'a' %}">Sort</a>
    """
    query = QueryDict('', mutable=True)
    query.update(context['request'].GET)

    if mode == 'update':
        for arg in args:
            parsed = QueryDict(arg)

            for attr in parsed:
                query.setlist(attr, parsed.getlist(attr))
    elif mode == 'remove':
        for arg in args:
            parsed = QueryDict(arg)

            for attr in parsed:
                to_remove = parsed.getlist(attr)

                if to_remove == ['']:
                    query.pop(attr, None)
                else:
                    values = query.getlist(attr)

                    for value in to_remove:
                        try:
                            values.remove(value)
                        except ValueError:
                            pass

                    query.setlist(attr, values)
    elif mode == 'append':
        for arg in args:
            query.update(QueryDict(arg))
    else:
        raise TemplateSyntaxError('Invalid mode for {%% querystring %%}: %s'
                                  % mode)

    return escape('?%s' % query.urlencode())
