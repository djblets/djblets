from __future__ import absolute_import, unicode_literals

import re
import sys
from xml.dom.minidom import parseString

from django.utils import six
from django.utils.six.moves import cStringIO as StringIO
from markdown import Markdown, markdownFromFile


default_app_config = 'djblets.markdown.apps.MarkdownAppConfig'


MARKDOWN_SPECIAL_CHARS = re.escape(r''.join(Markdown.ESCAPED_CHARS))
MARKDOWN_SPECIAL_CHARS_RE = re.compile(r'([%s])' % MARKDOWN_SPECIAL_CHARS)

# Markdown.ESCAPED_CHARS lists several characters to escape, but it's not
# that simple. We only want to escape certain things if they'll actually affect
# the Markdown rendering, because otherwise it's annoying to look at the
# source.
MARKDOWN_ESCAPED_CHARS = set(Markdown.ESCAPED_CHARS)
MARKDOWN_ESCAPED_CHARS -= set(['.', '#', '-', '+', '_', '(', ')', '*', '>'])

ESCAPE_CHARS_RE = re.compile(r"""
    (
    # Numeric lists start with leading whitespace, one or more digits,
    # and then a period
      ^\s*(\d+\.)\s

    # ATX-style headers start with a hash at the beginning of the line.
    | ^\s*(\#+)

    # + and - have special meaning (lists, headers, and rules), but only if
    # they're at the start of the line.
    | ^\s*([-\+]+)

    # _ indicates italic, and __ indicates bold, but not when in the middle
    # of a word.
    #
    | (?<!\w|_)(__?)
    | (__?)(?!\w|_)

    # This is an alternate format for italic and bold, using * instead of _.
    | (?<!\w|\*)(\*\*?)
    | (\*\*?)(?!\w|\*)

    # Named links are in the form of [name](url).
    | (\[) [^\]]* (\]) (\() [^\)]* (\))

    # '>' need only be escaped for blockquotes ('> ...') or automatic links
    # ('<http://...> or <user@example.com>).
    | ^((?:\s*>)+)
    | (?:<(?:(?:[Ff]|[Hh][Tt])[Tt][Pp][Ss]?://[^>]*))(>)
    | (?:<[^> \!]*@[^> ]*)(>)

    # All other special characters
    | ([%s])
    )
    """ % re.escape(''.join(MARKDOWN_ESCAPED_CHARS)),
    re.M | re.VERBOSE)
UNESCAPE_CHARS_RE = re.compile(r'\\([%s])' % MARKDOWN_SPECIAL_CHARS)

ILLEGAL_XML_CHARS_RE = None


def markdown_escape(text):
    """Escape text for use in Markdown.

    This will escape the provided text so that none of the characters will
    be rendered specially by Markdown.
    """
    def _escape_matches(m):
        prev_end = m.start(0)
        new_s = []

        for i, group in enumerate(m.groups()[1:], start=2):
            if group:
                new_s.append(m.string[prev_end:m.start(i)])
                new_s.append(MARKDOWN_SPECIAL_CHARS_RE.sub(r'\\\1', group))
                prev_end = m.end(i)

        new_s.append(m.string[prev_end:m.end(0)])

        return ''.join(new_s)

    return ESCAPE_CHARS_RE.sub(_escape_matches, text)


def markdown_unescape(escaped_text):
    """Unescape Markdown-escaped text.

    This will unescape the provided Markdown-formatted text so that any
    escaped characters will be unescaped.
    """
    text = UNESCAPE_CHARS_RE.sub(r'\1', escaped_text)

    split = text.split('\n')
    for i, line in enumerate(split):
        if line.startswith('&nbsp;   '):
            split[i] = ' ' + line[6:]
        elif line.startswith('&nbsp;\t'):
            split[i] = line[6:]

    return '\n'.join(split)


def iter_markdown_lines(markdown_html):
    """Iterate over lines of Markdown, normalizing for individual display.

    Generated Markdown HTML cannot by itself be handled on a per-line-basis.
    Code blocks, for example, will consist of multiple lines of content
    contained within a <pre> tag. Likewise, lists will be a bunch of
    <li> tags inside a <ul> tag, and individually do not form valid lists.

    This function iterates through the Markdown tree and generates
    self-contained lines of HTML that can be rendered individually.
    """
    nodes = get_markdown_element_tree(markdown_html)

    for node in nodes:
        if node.nodeType == node.ELEMENT_NODE:
            if (node.tagName == 'div' and
                node.attributes.get('class', 'codehilite')):
                # This is a code block, which will consist of a bunch of lines
                # for the source code. We want to split that up into
                # individual lines with their own <pre> tags.
                for line in node.toxml().splitlines():
                    yield '<pre>%s</pre>' % line
            elif node.tagName in ('ul', 'ol'):
                # This is a list. We'll need to split all of its items
                # into individual lists, in order to retain bullet points
                # or the numbers.
                #
                # For the case of numbers, we can set each list to start
                # at the appropriate number so that they don't all say "1."
                start = node.attributes.get('start')
                if start is not None:
                    try:
                        i = int(start.value)
                    except ValueError:
                        i = 1
                else:
                    i = 1

                for child_node in node.childNodes:
                    if (child_node.nodeType == child_node.ELEMENT_NODE and
                        child_node.tagName == 'li'):
                        # This is a list item element. It may be multiple
                        # lines, but we'll have to treat it as one line.
                        yield '<%s start="%s">%s</%s>' % (
                            node.tagName, i, child_node.toxml(),
                            node.tagName)

                        i += 1
            elif node.tagName == 'p':
                # This is a paragraph, possibly containing multiple lines.
                for line in node.toxml().splitlines():
                    yield line
            else:
                # Whatever this is, treat it as one block.
                yield node.toxml()
        elif node.nodeType == node.TEXT_NODE:
            # This may be several blank extraneous blank lines, due to
            # Markdown's generation from invisible markup like fences.
            # We want to condense this down to one blank line.
            yield '\n'


def get_markdown_element_tree(markdown_html):
    """Return an XML element tree for Markdown-generated HTML.

    This will build the tree and return all nodes representing the rendered
    Markdown content.
    """
    markdown_html = sanitize_illegal_chars_for_xml(markdown_html)

    if isinstance(markdown_html, six.text_type):
        markdown_html = markdown_html.encode('utf-8')

    doc = parseString(b'<html>%s</html>' % markdown_html)
    return doc.childNodes[0].childNodes


def sanitize_illegal_chars_for_xml(s):
    """Sanitize a string, removing characters illegal in XML.

    This will remove a number of characters that would break the  XML parser.
    They may be in the string due to a copy/paste.

    This code is courtesy of the XmlRpcPlugin developers, as documented
    here: http://stackoverflow.com/a/22273639
    """
    global ILLEGAL_XML_CHARS_RE

    if ILLEGAL_XML_CHARS_RE is None:
        _illegal_unichrs = [
            (0x00, 0x08), (0x0B, 0x0C), (0x0E, 0x1F), (0x7F, 0x84),
            (0x86, 0x9F), (0xFDD0, 0xFDDF), (0xFFFE, 0xFFFF)
        ]

        if sys.maxunicode > 0x10000:
            _illegal_unichrs += [
                (0x1FFFE, 0x1FFFF), (0x2FFFE, 0x2FFFF), (0x3FFFE, 0x3FFFF),
                (0x4FFFE, 0x4FFFF), (0x5FFFE, 0x5FFFF), (0x6FFFE, 0x6FFFF),
                (0x7FFFE, 0x7FFFF), (0x8FFFE, 0x8FFFF), (0x9FFFE, 0x9FFFF),
                (0xAFFFE, 0xAFFFF), (0xBFFFE, 0xBFFFF), (0xCFFFE, 0xCFFFF),
                (0xDFFFE, 0xDFFFF), (0xEFFFE, 0xEFFFF), (0xFFFFE, 0xFFFFF),
                (0x10FFFE, 0x10FFFF)
            ]

        ILLEGAL_XML_CHARS_RE = re.compile('[%s]' % ''.join([
            '%s-%s' % (unichr(low), unichr(high))
            for low, high in _illegal_unichrs
        ]))

    if isinstance(s, bytes):
        s = s.decode('utf-8')

    return ILLEGAL_XML_CHARS_RE.sub('', s)


def render_markdown_from_file(f, **markdown_kwargs):
    """Render Markdown text from a file stream to HTML."""
    s = StringIO()
    markdownFromFile(input=f, output=s, **markdown_kwargs)
    html = s.getvalue()
    s.close()

    return html
