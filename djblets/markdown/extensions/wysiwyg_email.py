from __future__ import absolute_import, unicode_literals

from django import template
from django.utils import six
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor


register = template.Library()


class InlineStyleProcessor(Treeprocessor):
    """Injects CSS styles directly into the tags, for use in e-mails.

    This will process each element and, depending on the element type,
    create inline styles. These styles are meant to match the stylesheets
    in the :file:`markdown-wysiwyg.less` file.
    """

    def process_element(self, context, el):
        """Process an element in the tree.

        This adds a handful of inline styles to the resulting document which
        mimic the .rich-text rules in markdown-wysiwyg.less.

        This does not do quite everything that the markdown-wysiwyg.less rules
        do, due to the complexity in implementing CSS selectors in Python,
        and the CSS compatibility logic in most e-mail clients.

        The end result is that the e-mail will look similar but not identical
        to the page.
        """
        style = {
            'margin': 0,
            'padding': 0,
            'line-height': 'inherit',
            'text-rendering': 'inherit',
            'white-space': 'normal',
        }
        tag = el.tag

        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            style['font-size'] = '100%'
        elif tag == 'ul':
            style['margin'] = '0 0 0 1em'
        elif tag == 'ol':
            style['margin'] = '0 0 0 2em'
        elif tag == 'code':
            style['color'] = '#4444cc'
        elif tag == 'p':
            style['white-space'] = 'inherit'
        elif tag == 'blockquote':
            style.update({
                'border-left': '1px solid #bbb',
                'padding': '0 0 0 1em',
                'margin': '0 0 0 0.5em',
            })
        elif tag == 'hr':
            style['border'] = '1px solid #ddd'
        elif tag in ('th', 'td'):
            style.update({
                'border-bottom': '1px solid #bbb',
                'padding': '0.2em 1em',
            })

        # Create a valid CSS string and set it as the style attribute
        el.set('style', ''.join(
            '%s: %s;' % (k, v)
            for k, v in six.iteritems(style)
        ))

        # Recurse into children
        context.append(tag)

        for child in el:
            self.process_element(context, child)

        context.pop()

    def run(self, root):
        # We don't just process the root element, because if we add any style
        # characteristics to it, markdown can't strip off the top-level <div>
        # tag. Why it doesn't use the element tree to do the stripping is
        # beyond me.
        for child in root:
            self.process_element([], child)


class WysiwygEMailExtension(Extension):
    """A Markdown extension to inject CSS into elements for HTML output.

    This is meant as a counterpart to the Wysiwyg Markdown extension. It
    aims to provide HTML output that looks as similar as possible to the
    input, preserving the spacing, font sizes, alignment, and other styles
    from the raw text.

    This is meant to be used with the following Markdown configuration
    and extensions:

    .. code-block:: python

        {
            'extensions': [
                'codehilite(noclasss=True)', 'tables',
                'djblets.markdown.extentions.wysiwyg',
            ],
        }
    """

    def extendMarkdown(self, md, md_globals):
        """Extend the list of Markdown processors."""
        md.treeprocessors.add('inlinestyle', InlineStyleProcessor(), '_end')


def makeExtension(configs={}):
    """Create a Markdown extension instance for this file."""
    return WysiwygEMailExtension(configs=configs)
