"""Unit tests for djblets.util.templatetags.djblets_utils."""

from __future__ import unicode_literals

from datetime import datetime, timedelta

from django.http import HttpRequest
from django.template import Context, Template

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

    def test_basic_usage(self):
        """Testing {% querystring_with %}"""
        t = Template('{% load djblets_utils %}'
                     '{% querystring_with "foo" "bar" %}')

        self.assertEqual(
            t.render(Context({
                'request': HttpRequest()
            })),
            '?foo=bar')

    def test_with_tag_existing_query(self):
        """Testing {% querystring_with %} with an existing query"""
        t = Template('{% load djblets_utils %}'
                     '{% querystring_with "foo" "bar" %}')

        request = HttpRequest()
        request.GET = {
            'a': '1',
            'b': '2',
        }

        self.assertEqual(
            t.render(Context({
                'request': request
            })),
            '?a=1&amp;b=2&amp;foo=bar')

    def test_with_existing_query_override(self):
        """Testing {% querystring_with %} with an existing query that gets
        overriden
        """
        t = Template('{% load djblets_utils %}'
                     '{% querystring_with "foo" "bar" %}')

        request = HttpRequest()
        request.GET = {
            'foo': 'foo',
            'bar': 'baz',
        }

        self.assertEqual(
            t.render(Context({
                'request': request
            })),
            '?bar=baz&amp;foo=bar')
