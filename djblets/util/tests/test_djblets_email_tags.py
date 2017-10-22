"""Unit tests for djblets.util.templatetags.djblets_email."""

from __future__ import unicode_literals

from django.template import Context, Template, TemplateSyntaxError

from djblets.testing.testcases import TagTest, TestCase
from djblets.util.templatetags.djblets_email import quote_text


class CondenseTagTests(TagTest):
    """Unit tests for the {% condense %} template tag."""

    tag_content = 'foo\nbar\n\n\n\n\n\n\nfoobar!'

    def test_with_defaults(self):
        """Testing {% condense %}"""
        t = Template('{% load djblets_email %}'
                     '{% condense %}' +
                     self.tag_content +
                     '{% endcondense %}')

        self.assertHTMLEqual(t.render(Context({})),
                             'foo\nbar\n\n\nfoobar!')

    def test_with_max_indents(self):
        """Testing {% condense %} with custom max_indents"""
        t = Template('{% load djblets_email %}'
                     '{% condense 1 %}' +
                     self.tag_content +
                     '{% endcondense %}')
        self.assertHTMLEqual(t.render(Context({})),
                             'foo\nbar\nfoobar!')


class QuotedEmailTagTests(TagTest):
    """Unit tests for the {% quoted_email %} template tag."""

    def test_basic_usage(self):
        """Testing {% quoted_email %}"""
        t = Template('{% load djblets_email %}'
                     '{% quoted_email template_name %}')

        self.assertEqual(
            t.render(Context({
                'template_name': 'testing/foo.html',
                'foo': 'baz',
                'bar': 'qux',
            })),
            '> baz qux\n'
            '>')

    def test_with_invalid(self):
        """Testing {% quoted_email %} with invalid usage"""
        with self.assertRaises(TemplateSyntaxError):
            Template('{% load djblets_email %}'
                     '{% quoted_email %}content{% end_quoted_email %}')


class QuoteTextFilterTests(TestCase):
    """Unit tests for the {{...|quote_text}} template filter."""

    def test_with_default_level(self):
        """Testing {{...|quote_text}} with default quote level"""
        self.assertEqual(quote_text('foo\nbar'),
                         '> foo\n> bar')

    def testLevel2(self):
        """Testing {{...|quote_text}} with custom quote level"""
        self.assertEqual(quote_text('foo\nbar', 2),
                         '> > foo\n> > bar')
