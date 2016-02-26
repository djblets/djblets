from __future__ import print_function, unicode_literals

from markdown import markdown

from djblets.testing.testcases import TestCase
from djblets.markdown import (get_markdown_element_tree,
                              iter_markdown_lines,
                              markdown_escape,
                              markdown_unescape)


class MarkdownTestCase(TestCase):
    """Base class for Markdown-related test cases."""

    def render_markdown(self, text):
        return markdown(
            text,
            safe_mode='escape',
            output_format='xhtml1',
            lazy_ol=False,
            extensions=[
                'fenced_code', 'codehilite', 'sane_lists', 'smart_strong',
                'nl2br', 'djblets.markdown.extensions.wysiwyg',
            ],
        )


class MarkdownUtilsTests(MarkdownTestCase):
    """Unit tests for the Markdown utility functions."""

    UNESCAPED_TEXT = r'\`*_{}[]()#+-.!'
    ESCAPED_TEXT = r'\\\`\*\_\{\}\[\]\(\)#+-.\!'

    def test_get_markdown_element_tree(self):
        """Testing get_markdown_element_tree"""
        node = get_markdown_element_tree(
            self.render_markdown('**Test**\nHi.'))

        self.assertEqual(node[0].toxml(),
                         '<p><strong>Test</strong><br/>\n'
                         'Hi.</p>')

    def test_get_markdown_element_tree_with_illegal_chars(self):
        """Testing get_markdown_element_tree with illegal characters"""
        node = get_markdown_element_tree(
            self.render_markdown('(**Test**\x0C)'))

        self.assertEqual(node[0].toxml(), '<p>(<strong>Test</strong>)</p>')

    def test_markdown_escape(self):
        """Testing markdown_escape"""
        self.assertEqual(markdown_escape(self.UNESCAPED_TEXT),
                         self.ESCAPED_TEXT)

    def test_markdown_escape_periods(self):
        """Testing markdown_escape with '.' placement"""
        self.assertEqual(
            markdown_escape('Line. 1.\n'
                            '1. Line. 2.\n'
                            '1.2. Line. 3.\n'
                            '  1. Line. 4.'),
            ('Line. 1.\n'
             '1\\. Line. 2.\n'
             '1.2. Line. 3.\n'
             '  1\\. Line. 4.'))

    def test_markdown_escape_atx_headers(self):
        """Testing markdown_escape with '#' placement"""
        self.assertEqual(
            markdown_escape('### Header\n'
                            '  ## Header ##\n'
                            'Not # a header'),
            ('\\#\\#\\# Header\n'
             '  \\#\\# Header ##\n'
             'Not # a header'))

    def test_markdown_escape_hyphens(self):
        """Testing markdown_escape with '-' placement"""
        self.assertEqual(
            markdown_escape('Header\n'
                            '------\n'
                            '\n'
                            '- List item\n'
                            '  - List item\n'
                            'Just hyp-henated'),
            ('Header\n'
             '\\-\\-\\-\\-\\-\\-\n'
             '\n'
             '\\- List item\n'
             '  \\- List item\n'
             'Just hyp-henated'))

    def test_markdown_escape_plusses(self):
        """Testing markdown_escape with '+' placement"""
        self.assertEqual(
            markdown_escape('+ List item\n'
                            'a + b'),
            ('\\+ List item\n'
             'a + b'))

    def test_markdown_escape_underscores(self):
        """Testing markdown_escape with '_' placement"""
        self.assertEqual(markdown_escape('_foo_'), r'\_foo\_')
        self.assertEqual(markdown_escape('__foo__'), r'\_\_foo\_\_')
        self.assertEqual(markdown_escape(' _foo_ '), r' \_foo\_ ')
        self.assertEqual(markdown_escape('f_o_o'), r'f_o_o')
        self.assertEqual(markdown_escape('_f_o_o'), r'\_f_o_o')
        self.assertEqual(markdown_escape('f_o_o_'), r'f_o_o\_')
        self.assertEqual(markdown_escape('foo_ _bar'), r'foo\_ \_bar')
        self.assertEqual(markdown_escape('foo__bar'), r'foo__bar')
        self.assertEqual(markdown_escape('foo\n_bar'), 'foo\n\\_bar')
        self.assertEqual(markdown_escape('(_foo_)'), r'(\_foo\_)')

    def test_markdown_escape_asterisks(self):
        """Testing markdown_escape with '*' placement"""
        self.assertEqual(markdown_escape('*foo*'), r'\*foo\*')
        self.assertEqual(markdown_escape('**foo**'), r'\*\*foo\*\*')
        self.assertEqual(markdown_escape(' *foo* '), r' \*foo\* ')
        self.assertEqual(markdown_escape('f*o*o'), r'f*o*o')
        self.assertEqual(markdown_escape('f*o*o*'), r'f*o*o\*')
        self.assertEqual(markdown_escape('foo* *bar'), r'foo\* \*bar')
        self.assertEqual(markdown_escape('foo**bar'), r'foo**bar')
        self.assertEqual(markdown_escape('foo\n*bar'), 'foo\n\\*bar')

    def test_markdown_escape_parens(self):
        """Testing markdown_escape with '(' and ')' placement"""
        self.assertEqual(markdown_escape('[name](link)'), r'\[name\]\(link\)')
        self.assertEqual(markdown_escape('(link)'), r'(link)')
        self.assertEqual(markdown_escape('](link)'), r'\](link)')
        self.assertEqual(markdown_escape('[foo] ](link)'),
                         r'\[foo\] \](link)')

    def test_markdown_escape_gt_text(self):
        """Testing markdown_escape with '>' for standard text"""
        self.assertEqual(markdown_escape('<foo>'), r'<foo>')

    def test_markdown_escape_gt_blockquotes(self):
        """Testing markdown_escape with '>' for blockquotes"""
        self.assertEqual(markdown_escape('>'), r'\>')
        self.assertEqual(markdown_escape('> foo'), r'\> foo')
        self.assertEqual(markdown_escape('  > foo'), r'  \> foo')
        self.assertEqual(markdown_escape('> > foo'), r'\> \> foo')
        self.assertEqual(markdown_escape('  > > foo'), r'  \> \> foo')

    def test_markdown_escape_gt_autolinks(self):
        """Testing markdown_escape with '>' for autolinks"""
        self.assertEqual(markdown_escape('<http://www.example.com>'),
                         r'<http://www.example.com\>')

    def test_markdown_escape_gt_autoemail(self):
        """Testing markdown_escape with '>' for autoemails"""
        self.assertEqual(markdown_escape('<user@example.com>'),
                         r'<user@example.com\>')

    def test_markdown_unescape(self):
        """Testing markdown_unescape"""
        self.assertEqual(markdown_unescape(self.ESCAPED_TEXT),
                         self.UNESCAPED_TEXT)

        self.assertEqual(
            markdown_unescape('&nbsp;   code\n'
                              '&nbsp;   code'),
            ('    code\n'
             '    code'))
        self.assertEqual(
            markdown_unescape('&nbsp;\tcode\n'
                              '&nbsp;\tcode'),
            ('\tcode\n'
             '\tcode'))

    def test_markdown_list_start(self):
        """Testing iteration of Markdown lists with a 'start' parameter"""
        # In bug 3715, we were treating the 'start' parameter incorrectly. This
        # checks that said bug is fixed.
        rendered = '<ul start="2"><li>x</li><li>y</li></ul>'
        lines = list(iter_markdown_lines(rendered))

        self.assertEqual(lines, [
            '<ul start="2"><li>x</li></ul>',
            '<ul start="3"><li>y</li></ul>',
        ])

    def test_sanitize_illegal_chars(self):
        """Testing sanitize_illegal_chars_for_xml"""
        s = '<a>\u2018\u2019\u201c\u201d\u201c\u201d</a>'

        # This used to cause a UnicodeDecodeError
        nodes = get_markdown_element_tree(s)

        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].toxml(),
                         '<a>\u2018\u2019\u201c\u201d\u201c\u201d</a>')


class WysiwygRenderTests(MarkdownTestCase):
    """Unit tests for rendering with the WYSIWYG Markdown extension."""

    def test_code_1_blank_line(self):
        """Testing Markdown WYSIWYG rendering with code block and 1 surrounding
        blank line
        """
        self.assertEqual(
            self.render_markdown(
                'begin:\n'
                '\n'
                '    if (1) {}\n'
                '\n'
                'done.'),
            ('<p>begin:</p>\n'
             '<div class="codehilite"><pre><span></span>if (1) {}\n'
             '</pre></div>\n'
             '<p>done.</p>'))

    def test_code_2_blank_lines(self):
        """Testing Markdown WYSIWYG rendering with code block and 2 surrounding
        blank lines
        """
        self.assertEqual(
            self.render_markdown(
                'begin:\n'
                '\n'
                '\n'
                '    if (1) {}\n'
                '\n'
                '\n'
                'done.'),
            ('<p>begin:</p>\n'
             '<p></p>\n'
             '<div class="codehilite"><pre><span></span>if (1) {}\n'
             '</pre></div>\n'
             '<p></p>\n'
             '<p>done.</p>'))

    def test_code_3_blank_lines(self):
        """Testing Markdown WYSIWYG rendering with code block and 3 surrounding
        blank lines
        """
        self.assertEqual(
            self.render_markdown(
                'begin:\n'
                '\n'
                '\n'
                '\n'
                '    if (1) {}\n'
                '\n'
                '\n'
                '\n'
                'done.'),
            ('<p>begin:</p>\n'
             '<p></p>\n'
             '<p></p>\n'
             '<div class="codehilite"><pre><span></span>if (1) {}\n'
             '</pre></div>\n'
             '<p></p>\n'
             '<p></p>\n'
             '<p>done.</p>'))

    def test_code_4_blank_lines(self):
        """Testing Markdown WYSIWYG rendering with code block and 4 surrounding
        blank lines
        """
        self.assertEqual(
            self.render_markdown(
                'begin:\n'
                '\n'
                '\n'
                '\n'
                '\n'
                '    if (1) {}\n'
                '\n'
                '\n'
                '\n'
                '\n'
                'done.'),
            ('<p>begin:</p>\n'
             '<p></p>\n'
             '<p></p>\n'
             '<p></p>\n'
             '<div class="codehilite"><pre><span></span>if (1) {}\n'
             '</pre></div>\n'
             '<p></p>\n'
             '<p></p>\n'
             '<p></p>\n'
             '<p>done.</p>'))

    def test_lists_1_blank_line(self):
        """Testing Markdown WYSIWYG rendering with 1 blank lines between lists
        """
        # This really just results in a single list. This is Python Markdown
        # behavior.
        self.assertEqual(
            self.render_markdown(
                '1. item\n'
                '\n'
                '1. item'),
            ('<ol>\n'
             '<li>\n'
             '<p>item</p>\n'
             '</li>\n'
             '<li>\n'
             '<p>item</p>\n'
             '</li>\n'
             '</ol>'))

    def test_lists_2_blank_line(self):
        """Testing Markdown WYSIWYG rendering with 2 blank lines between lists
        """
        self.assertEqual(
            self.render_markdown(
                '1. item\n'
                '\n'
                '\n'
                '1. item'),
            ('<ol>\n'
             '<li>item</li>\n'
             '</ol>\n'
             '<p></p>\n'
             '<ol>\n'
             '<li>item</li>\n'
             '</ol>'))

    def test_lists_3_blank_line(self):
        """Testing Markdown WYSIWYG rendering with 3 blank lines between lists
        """
        self.assertEqual(
            self.render_markdown(
                '1. item\n'
                '\n'
                '\n'
                '\n'
                '1. item'),
            ('<ol>\n'
             '<li>item</li>\n'
             '</ol>\n'
             '<p></p>\n'
             '<p></p>\n'
             '<ol>\n'
             '<li>item</li>\n'
             '</ol>'))

    def test_ol(self):
        """Testing Markdown WYSIWYG rendering with ordered lists"""
        self.assertEqual(
            self.render_markdown(
                '1. Foo\n'
                '2. Bar'),
            ('<ol>\n'
             '<li>Foo</li>\n'
             '<li>Bar</li>\n'
             '</ol>'))

    def test_ol_start(self):
        """Testing Markdown WYSIWYG rendering with ordered lists using start=
        """
        self.assertEqual(
            self.render_markdown(
                '5. Foo\n'
                '6. Bar'),
            ('<ol start="5" style="counter-reset: li 4">\n'
             '<li>Foo</li>\n'
             '<li>Bar</li>\n'
             '</ol>'))

    def test_text_0_blank_lines(self):
        """Testing Markdown WYSIWYG rendering with 0 blank lines between text
        """
        self.assertEqual(
            self.render_markdown(
                'begin:\n'
                'done.'),
            ('<p>begin:<br />\n'
             'done.</p>'))

    def test_text_1_blank_line(self):
        """Testing Markdown WYSIWYG rendering with 1 blank line between text"""
        self.assertEqual(
            self.render_markdown(
                'begin:\n'
                '\n'
                'done.'),
            ('<p>begin:</p>\n'
             '<p>done.</p>'))

    def test_text_2_blank_lines(self):
        """Testing Markdown WYSIWYG rendering with 2 blank lines between text
        """
        self.assertEqual(
            self.render_markdown(
                'begin:\n'
                '\n'
                '\n'
                'done.'),
            ('<p>begin:</p>\n'
             '<p></p>\n'
             '<p>done.</p>'))

    def test_text_3_blank_lines(self):
        """Testing Markdown WYSIWYG rendering with 3 blank lines between text
        """
        self.assertEqual(
            self.render_markdown(
                'begin:\n'
                '\n'
                '\n'
                '\n'
                'done.'),
            ('<p>begin:</p>\n'
             '<p></p>\n'
             '<p></p>\n'
             '<p>done.</p>'))

    def test_trailing_p_trimmed(self):
        """Testing Markdown WYSIWYG rendering trims trailing paragraphs"""
        self.assertEqual(
            self.render_markdown(
                'begin:\n'
                '\n'
                '\n'),
            '<p>begin:</p>')
