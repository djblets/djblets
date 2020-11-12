"""Unit tests for djblets.util.templatetags.djblets_utils."""

from __future__ import unicode_literals

import warnings
from collections import OrderedDict
from datetime import datetime, timedelta

from django.http import HttpRequest, QueryDict
from django.template import Context, Template
from django.utils import six

from djblets.deprecation import RemovedInDjblets30Warning
from djblets.testing.testcases import TagTest, TestCase
from djblets.util.templatetags.djblets_utils import (ageid, escapespaces,
                                                     humanize_list, indent)


class AgeIdTagTests(TagTest):
    """Unit tests for the {% ageid %} template tag."""

    def setUp(self):
        super(AgeIdTagTests, self).setUp()

        self.now = datetime.utcnow()

        self.context = {
            'now': self.now,
            'minus1': self.now - timedelta(1),
            'minus2': self.now - timedelta(2),
            'minus3': self.now - timedelta(3),
            'minus4': self.now - timedelta(4),
        }

    def test_with_now(self):
        """Testing {% ageid %} with now"""
        self.assertEqual(ageid(self.now), 'age1')

    def test_with_now_minus_1_day(self):
        """Testing {% ageid %} with yesterday"""
        self.assertEqual(ageid(self.now - timedelta(1)), 'age2')

    def test_with_now_minus_2_days(self):
        """Testing {% ageid %} with two days ago"""
        self.assertEqual(ageid(self.now - timedelta(2)), 'age3')

    def test_with_now_minus_3_days(self):
        """Testing {% ageid %} with three days ago"""
        self.assertEqual(ageid(self.now - timedelta(3)), 'age4')

    def test_with_now_minus_4_days(self):
        """Testing {% ageid %} with four days ago"""
        self.assertEqual(ageid(self.now - timedelta(4)), 'age5')

    def test_with_non_datetime(self):
        """Testing {% ageid %} with non-datetime object"""
        class Foo:
            def __init__(self, now):
                self.day = now.day
                self.month = now.month
                self.year = now.year

        self.assertEqual(ageid(Foo(self.now)), 'age1')


class AttrTagTests(TestCase):
    """Unit tests for the {% attr %} template tag."""

    def test_with_value(self):
        """Testing {% attr %} with value"""
        t = Template('{% load djblets_utils %}'
                     '<span{% attr "class" %}\n'
                     '{%  if some_bool %}truthy{% endif %}\n'
                     '{% endattr %}>')

        self.assertEqual(
            t.render(Context({
                'some_bool': True,
            })),
            '<span class="truthy">')

    def test_without_value(self):
        """Testing {% attr %} with no value"""
        t = Template('{% load djblets_utils %}'
                     '<span{% attr "class" %}\n'
                     '{%  if some_bool %}falsy{% endif %}\n'
                     '{% endattr %}>')

        self.assertEqual(
            t.render(Context({
                'some_bool': False,
            })),
            '<span>')

    def test_escapes_value(self):
        """Testing {% attr %} escapes value"""
        t = Template('{% load djblets_utils %}'
                     '<span{% attr "data-foo" %}<hello>{% endattr %}>')

        self.assertEqual(
            t.render(Context()),
            '<span data-foo="&lt;hello&gt;">')

    def test_condenses_whitespace(self):
        """Testing {% attr %} condenses/strips extra whitespace by default"""
        t = Template('{% load djblets_utils %}'
                     '<span{% attr "data-foo" %}\n'
                     'some    \n\n'
                     'value\n'
                     '{% endattr %}>')

        self.assertEqual(
            t.render(Context()),
            '<span data-foo="some value">')

    def test_with_nocondense_preserves_whitespace(self):
        """Testing {% attr %} with "nocondense" option preserves whitespace"""
        t = Template('{% load djblets_utils %}'
                     '<span{% attr "data-foo" nocondense %}\n'
                     'some    \n\n'
                     'value\n'
                     '{% endattr %}>')

        self.assertEqual(
            t.render(Context()),
            '<span data-foo="\nsome    \n\nvalue\n">')


class DefineVarTagTests(TestCase):
    """Unit tests for the {% definevar %} template tag."""

    def test_basic_usage(self):
        """Testing {% definevar %}"""
        t = Template('{% load djblets_utils %}'
                     '{% definevar "myvar" %}\n'
                     'test{{num}}\n'
                     '{% enddefinevar %}'
                     '{{myvar}}')

        self.assertEqual(
            t.render(Context({
                'num': 123,
            })),
            '\ntest123\n')

    def test_with_global(self):
        """Testing {% definevar %} with global option"""
        t = Template(
            '{% load djblets_utils %}'
            '{% block main %}'
            '{%  block inner %}'
            '{%   definevar "myvar" global %}{{num}}{% enddefinevar %}'
            '{%  endblock %}'
            '{% endblock %}'
            '[{{myvar}}]')

        self.assertEqual(
            t.render(Context({
                'num': 123,
            })),
            '[123]')

    def test_with_strip(self):
        """Testing {% definevar %} with strip option"""
        t = Template('{% load djblets_utils %}'
                     '{% definevar "myvar" strip %}\n'
                     '<span>\n'
                     ' <strong>\n'
                     '  test{{num}}\n'
                     ' </strong>\n'
                     '</span>\n'
                     '{% enddefinevar %}'
                     '[{{myvar}}]')

        self.assertEqual(
            t.render(Context({
                'num': 123,
            })),
            '[<span>\n <strong>\n  test123\n </strong>\n</span>]')

    def test_with_spaceless(self):
        """Testing {% definevar %} with spaceless option"""
        t = Template('{% load djblets_utils %}'
                     '{% definevar "myvar" spaceless %}\n'
                     '<span>\n'
                     ' <strong>\n'
                     '  test{{num}}\n'
                     ' </strong>\n'
                     '</span>\n'
                     '{% enddefinevar %}'
                     '[{{myvar}}]')

        self.assertEqual(
            t.render(Context({
                'num': 123,
            })),
            '[<span><strong>\n  test123\n </strong></span>]')

    def test_with_unsafe(self):
        """Testing {% definevar %} with unsafe option"""
        t = Template('{% load djblets_utils %}'
                     '{% definevar "myvar" unsafe %}<hello>{% enddefinevar %}'
                     '{{myvar}}')

        self.assertEqual(t.render(Context()), '&lt;hello&gt;')


class EscapeSpacesFilterTests(TestCase):
    """Unit tests for the {{...|escapespaces}} template filter."""

    def test_with_single_space(self):
        """Testing {{...|escapespaces}} with single space"""
        self.assertEqual(escapespaces('Hi there'),
                         'Hi there')

    def test_with_multiple_spaces(self):
        """Testing {{...|escapespaces}} with multiple consecutive spaces"""
        self.assertEqual(escapespaces('Hi  there'),
                         'Hi&nbsp; there')

    def test_with_newline(self):
        """Testing {{...|escapespaces}} with newline"""
        self.assertEqual(escapespaces('Hi  there\n'),
                         'Hi&nbsp; there<br />')


class GetAttrFilterTests(TestCase):
    """Unit tests for the {{...|getattr:...}} template filter."""

    def test_with_attr_found(self):
        """Testing {{...|getattr:...}} with attribute found"""
        class MyObject(object):
            key = 'value'

        t = Template('{% load djblets_utils %}'
                     '{{obj|getattr:"key"}}')

        self.assertEqual(
            t.render(Context({
                'obj': MyObject(),
            })),
            'value')

    def test_with_attr_not_found(self):
        """Testing {{...|getattr:...}} with attribute not found"""
        class MyObject(object):
            key = 'value'

        t = Template('{% load djblets_utils %}'
                     '{{obj|getattr:"bad_key"}}')

        self.assertEqual(
            t.render(Context({
                'obj': MyObject(),
            })),
            'None')

    def test_with_attr_not_found_and_default_if_none(self):
        """Testing {{...|getattr:...}} with attribute not found and
        default_if_none fallback filter
        """
        class MyObject(object):
            key = 'value'

        t = Template('{% load djblets_utils %}'
                     '{{obj|getattr:"bad_key"|default_if_none:"doh"}}')

        self.assertEqual(
            t.render(Context({
                'obj': MyObject(),
            })),
            'doh')


class HumanizeListFilterTests(TestCase):
    """Unit tests for the {{...|humanize_list}} template filter."""

    def test_with_empty_list(self):
        """Testing {{...|humanize_list}} with empty list"""
        self.assertEqual(humanize_list([]),
                         '')

    def test_with_1_item(self):
        """Testing {{...|humanize_list}} with 1 item"""
        self.assertEqual(humanize_list(['a']),
                         'a')

    def test_with_2_items(self):
        """Testing {{...|humanize_list}} with 2 items"""
        self.assertEqual(humanize_list(['a', 'b']),
                         'a and b')

    def test_with_3_items(self):
        """Testing {{...|humanize_list}} with 3 items"""
        self.assertEqual(humanize_list(['a', 'b', 'c']),
                         'a, b and c')

    def test_with_4_items(self):
        """Testing {{...|humanize_list}} with 4 items"""
        self.assertEqual(humanize_list(['a', 'b', 'c', 'd']),
                         'a, b, c, and d')


class IncludeAsStringTagTests(TestCase):
    """Unit tests for the {% include_as_string %} template tag."""

    def test_basic_usage(self):
        """Testing {% include_as_string %}"""
        t = Template('{% load djblets_utils %}'
                     '{% include_as_string template_name %}')

        self.assertEqual(
            t.render(Context({
                'template_name': 'testing/foo.html',
                'foo': 1,
                'bar': 2,
            })),
            "'1 2\\\n'")


class IndentFilterTests(TestCase):
    """Unit tests for the {{...|indent}} template filter."""

    def test_with_default_indent(self):
        """Testing {{...|indent}} with default indentation level"""
        self.assertEqual(indent('foo'), '    foo')

    def test_with_custom_indent(self):
        """Testing {{...|indent}} with custom indentation level"""
        self.assertEqual(indent('foo', 3), '   foo')

    def test_with_multiple_lines(self):
        """Testing {{...|indent}} with multiple lines"""
        self.assertEqual(indent('foo\nbar'),
                         '    foo\n    bar')


class QuerystringWithTagTests(TestCase):
    """Unit tests for the {% querystring_with %} template tag."""

    def setUp(self):
        super(QuerystringWithTagTests, self).setUp()
        self.request = HttpRequest()
        warnings.simplefilter('always')

    def test_basic_usage(self):
        """Testing {% querystring_with %}"""
        t = Template('{% load djblets_utils %}'
                     '{% querystring_with "foo" "bar" %}')

        with warnings.catch_warnings(record=True) as w:
            t.render(Context({
                'request': self.request,
            }))

        self.assertEqual(len(w), 1)
        deprecation_message = w[0].message

        self.assertIsInstance(deprecation_message, RemovedInDjblets30Warning)
        self.assertEqual(
            six.text_type(deprecation_message),
            '{% querystring_with "foo" "bar" %} is deprecated and will be '
            'removed in a future version of Djblets. Please use '
            '{% querystring "mode" "foo=bar" %} instead.')

        self.assertEqual(
            t.render(Context({
                'request': HttpRequest(),
            })),
            '?foo=bar')

    def test_with_tag_existing_query(self):
        """Testing {% querystring_with %} with an existing query"""
        t = Template('{% load djblets_utils %}'
                     '{% querystring_with "foo" "bar" %}')

        self.request.GET = OrderedDict([
            ('a', '1'),
            ('b', '2'),
        ])

        self.assertEqual(
            t.render(Context({
                'request': self.request,
            })),
            '?a=1&amp;b=2&amp;foo=bar')

    def test_with_existing_query_override(self):
        """Testing {% querystring_with %} with an existing query that gets
        overriden
        """
        t = Template('{% load djblets_utils %}'
                     '{% querystring_with "foo" "bar" %}')

        self.request.GET = {
            'foo': 'foo',
            'bar': 'baz',
        }

        self.assertEqual(
            t.render(Context({
                'request': self.request,
            })), '?bar=baz&amp;foo=bar')


class QuerystringTagTests(TestCase):
    """Unit tests for the {% querystring %} template tag."""

    def test_update_basic_usage(self):
        """Testing {% querystring "update" %} basic usage"""
        self.assertEqual(
            self._render_tag(tag='{% querystring "update" "foo=bar" %}',
                             query_str='foo=bar'),
            '?foo=bar')

    def test_update_with_tag_existing_query(self):
        """Testing {% querystring "update" %} with an existing query"""
        rendered_result = self._render_tag(
            tag='{% querystring "update" "foo=bar" %}',
            query_str='a=1&b=2')

        self.assertTrue(rendered_result.startswith('?'))
        self.assertEqual(QueryDict(rendered_result[1:]),
                         QueryDict('a=1&;b=2&;foo=bar'))

    def test_update_with_existing_query_override(self):
        """Testing {% querystring "update" %} with an existing query that gets
        overridden
        """
        rendered_result = self._render_tag(
            tag='{% querystring "update" "foo=bar" %}',
            query_str='foo=foo&bar=baz')

        self.assertTrue(rendered_result.startswith('?'))
        self.assertEqual(QueryDict(rendered_result[1:]),
                         QueryDict('foo=bar&bar=baz'))

    def test_update_with_existing_query_with_two_args_override(self):
        """Testing {% querystring "update" %} with two args that get
        overridden
        """
        rendered_result = self._render_tag(
            tag='{% querystring "update" "foo=bar" "qux=baz" %}',
            query_str='foo=foo&bar=bar&baz=baz&qux=qux')

        self.assertTrue(rendered_result.startswith('?'))
        self.assertEqual(QueryDict(rendered_result[1:]),
                         QueryDict('foo=bar&bar=bar&baz=baz&qux=baz'))

    def test_update_with_no_value(self):
        """Testing {% querystring "update" %} with no value"""
        rendered_result = self._render_tag(
            tag='{% querystring "update" "foo" %}',
            query_str='')

        self.assertTrue(rendered_result.startswith('?'))
        self.assertEqual(QueryDict(rendered_result[1:]), QueryDict('foo='))

    def test_update_with_multiple_values(self):
        """Testing {% querystring "update" %} with multiple values"""
        rendered_result = self._render_tag(
            tag='{% querystring "update" "foo=bar=baz" %}',
            query_str='foo=foo')

        self.assertTrue(rendered_result.startswith('?'))
        self.assertEqual(QueryDict(rendered_result[1:]),
                         QueryDict('foo=bar=baz'))

    def test_update_with_empty_value(self):
        """Testing {% querystring "update" %} with empty value"""
        rendered_result = self._render_tag(
            tag='{% querystring "update" "foo=" %}',
            query_str='')

        self.assertTrue(rendered_result.startswith('?'))
        self.assertEqual(QueryDict(rendered_result[1:]), QueryDict('foo='))

    def test_update_with_no_key(self):
        """Testing {% querystring "update" %} with no key"""
        rendered_result = self._render_tag(
            tag='{% querystring "update" "=foo" %}',
            query_str='')

        self.assertTrue(rendered_result.startswith('?'))
        self.assertEqual(QueryDict(rendered_result[1:]), QueryDict('=foo'))

    def test_update_with_querystring_key_overide(self):
        """Testing {% querystring "update" %} by updating multiple values of a
        key value gets overriden
        """
        rendered_result = self._render_tag(
            tag='{% querystring "update" "a=1" "a=2" %}',
            query_str='foo=foo')

        self.assertTrue(rendered_result.startswith('?'))
        self.assertEqual(QueryDict(rendered_result[1:]),
                         QueryDict('foo=foo&a=2'))

    def test_with_updating_multiple_values_of_a_key(self):
        """Testing {% querystring "update" %} by updating multiple values of a
        key value
        """
        rendered_result = self._render_tag(
            tag='{% querystring "update" "a=1&a=2" %}',
            query_str='foo=foo')

        self.assertTrue(rendered_result.startswith('?'))
        self.assertEqual(QueryDict(rendered_result[1:]),
                         QueryDict('foo=foo&a=1&a=2'))

    def test_append_with_basic_usage(self):
        """Testing {% querystring "append" %} with appending on to an existing
        key
        """
        rendered_result = self._render_tag(
            tag='{% querystring "append" "foo=baz" %}',
            query_str='foo=foo&bar=bar')

        self.assertTrue(rendered_result.startswith('?'))
        self.assertEqual(QueryDict(rendered_result[1:]),
                         QueryDict('foo=foo&foo=baz&bar=bar'))

    def test_append_with_multiple_values_and_same_key(self):
        """Testing {% querystring "append" %} with appending multiple values of
        a key
        """
        rendered_result = self._render_tag(
            tag='{% querystring "append" "a=1&a=2&a=3" %}',
            query_str='a=0&&b=2&c=3')

        self.assertTrue(rendered_result.startswith('?'))
        self.assertEqual(QueryDict(rendered_result[1:]),
                         QueryDict('a=0&a=1&a=2&a=3&b=2&c=3'))

    def test_append_with_multiple_values_and_same_key_seperated(self):
        """Testing {% querystring "append" %} with appending multiple values of
        a key fragment
        """
        rendered_result = self._render_tag(
            tag='{% querystring "append" "a=1" "a=2" "a=3" %}',
            query_str='a=0&&b=2&c=3')

        self.assertTrue(rendered_result.startswith('?'))
        self.assertEqual(QueryDict(rendered_result[1:]),
                         QueryDict('a=0&a=1&a=2&a=3&b=2&c=3'))

    def test_append_with_new_key(self):
        """Testing {% querystring "append" %} with appending new key-value
        pair
        """
        rendered_result = self._render_tag(
            tag='{% querystring "append" "d=4" %}',
            query_str='a=1&b=2&c=3')

        self.assertTrue(rendered_result.startswith('?'))
        self.assertEqual(QueryDict(rendered_result[1:]),
                         QueryDict('a=1&b=2&c=3&d=4'))

    def test_remove_with_basic_usage(self):
        """Testing {% querystring "remove" %} by removing a single instance of
        key
        """
        rendered_result = self._render_tag(
            tag='{% querystring "remove" "foo" %}',
            query_str='foo=foo&bar=bar')

        self.assertTrue(rendered_result.startswith('?'))
        self.assertEqual(QueryDict(rendered_result[1:]), QueryDict('bar=bar'))

    def test_remove_with_key_not_in_querystring(self):
        """Testing {% querystring "remove" %} by attempting to remove a
        non-existing key
        """
        rendered_result = self._render_tag(
            tag='{% querystring "remove" "baz" %}',
            query_str='foo=foo&bar=bar')

        self.assertTrue(rendered_result.startswith('?'))
        self.assertEqual(QueryDict(rendered_result[1:]),
                         QueryDict('foo=foo&bar=bar'))

    def test_remove_with_key_appearing_multiple_times(self):
        """Testing {% querystring "remove" %} by removing all instances of a
        key
        """
        rendered_result = self._render_tag(
            tag='{% querystring "remove" "foo" %}',
            query_str='foo=foo&foo=bar&bar=bar')

        self.assertTrue(rendered_result.startswith('?'))
        self.assertEqual(QueryDict(rendered_result[1:]), QueryDict('bar=bar'))

    def test_remove_for_specific_key_value_pairs(self):
        """Testing {% querystring "remove" %} by removing a specific key-value
        pair
        """
        rendered_result = self._render_tag(
            tag='{% querystring "remove" "a=4" %}',
            query_str='a=1&a=2&a=3&a=4')

        self.assertTrue(rendered_result.startswith('?'))
        self.assertEqual(QueryDict(rendered_result[1:]),
                         QueryDict('a=1&a=2&a=3&'))

    def test_remove_with_no_key(self):
        """Testing {% querystring "remove" %} by removing a value with
        no key
        """
        rendered_result = self._render_tag(
            tag='{% querystring "remove" "=foo" %}',
            query_str='foo=foo&foo=bar&baz=baz&=foo')

        self.assertTrue(rendered_result.startswith('?'))
        self.assertEqual(QueryDict(rendered_result[1:]),
                         QueryDict('foo=foo&foo=bar&baz=baz'))

    def test_remove_with_no_value(self):
        """Testing {% querystring "remove" %} by removing a key with no
        value
        """
        rendered_result = self._render_tag(
            tag='{% querystring "remove" "foo=" %}',
            query_str='foo=foo&foo=bar&foo=&baz=baz')

        self.assertTrue(rendered_result.startswith('?'))
        self.assertEqual(QueryDict(rendered_result[1:]), QueryDict('baz=baz'))

    def test_remove_with_multiple_removes(self):
        """Testing {% querystring "remove" %} by removing multiple keys and
        values
        """
        rendered_result = self._render_tag(
            tag='{% querystring "remove" "foo" "bar" "baz=1" %}',
            query_str='foo=foo&bar=bar&foo=&baz=1&qux=qux')

        self.assertTrue(rendered_result.startswith('?'))
        self.assertEqual(QueryDict(rendered_result[1:]), QueryDict('qux=qux'))

    def test_remove_with_multiple_specific_values(self):
        """Testing {% querystring "remove" %} by removing multiple specific
        key-value pairs
        """
        rendered_result = self._render_tag(
            tag='{% querystring "remove" "foo=1" "foo=2" %}',
            query_str='foo=1&foo=2&foo=3')

        self.assertTrue(rendered_result.startswith('?'))
        self.assertEqual(QueryDict(rendered_result[1:]), QueryDict('foo=3'))

    def _render_tag(self, tag, query_str):
        """Returned a rendered template tag using a query string.

        This will render a ``querystring`` template using the provided template
        tag, with auto-escaping turned off, and with the given query string as
        would be provided in a URL.

        Args:
            tag (unicode):
                The template tag line (``{% querystring ... %}``).

            query_str (unicode):
                The query string to simulate being in the URL.

        Returns:
            unicode:
            The rendered content, without escaping.
        """
        t = Template('{%% load djblets_utils %%}'
                     '{%% autoescape off %%}%s{%% endautoescape %%}'
                     % tag)

        request = HttpRequest()

        if query_str:
            request.GET = QueryDict(query_str)

        return t.render(Context({
            'request': request,
        })).replace('&amp;', '&')
