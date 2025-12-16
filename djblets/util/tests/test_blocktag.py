"""Unit tests for djblets.util.decorators.blocktag.

Version Added:
    5.3
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.template import Context, Library, NodeList, TemplateSyntaxError
from django.template.engine import Engine

from djblets.testing.testcases import TagTest
from djblets.util.decorators import blocktag

if TYPE_CHECKING:
    from djblets.util.decorators import _TagCompiler


class BlockTagTests(TagTest):
    """Unit tests for blocktag.

    Version Added:
        5.3
    """

    def test_with_no_args(self) -> None:
        """Testing blocktag with no arguments"""
        @blocktag
        def my_blocktag(
            context: Context,
            nodelist: NodeList,
        ) -> str:
            rendered = nodelist.render(context)

            return f'[[{rendered}]]'

        self.assertEqual(self._render_tag(my_blocktag),
                         '[[123456]]')

    def test_with_optional_pos_args(self) -> None:
        """Testing blocktag with optional positional arguments"""
        @blocktag
        def my_blocktag(
            context: Context,
            nodelist: NodeList,
            x: int,
            y: int,
            z: str = 'z',
        ) -> str:
            inner = nodelist.render(context)

            return f'[[x={x},y={y},z={z};{inner}]]'

        self.assertEqual(self._render_tag(my_blocktag, '42 100'),
                         '[[x=42,y=100,z=z;123456]]')

    def test_with_missing_required_pos_args(self) -> None:
        """Testing blocktag with missing required positional arguments
        """
        @blocktag
        def my_blocktag(
            context: Context,
            nodelist: NodeList,
            x: int,
            y: int,
        ) -> str:
            inner = nodelist.render(context)

            return f'[[x={x},y={y};{inner}]]'

        message = (
            "'my_blocktag' did not receive value(s) for the argument(s): "
            "'y'"
        )

        with self.assertRaisesMessage(TemplateSyntaxError, message):
            self._render_tag(my_blocktag, '42')

    def test_with_keyword_as_pos_arg(self) -> None:
        """Testing blocktag with keyword argument for positional
        argument
        """
        @blocktag
        def my_blocktag(
            context: Context,
            nodelist: NodeList,
            x: int,
            y: int,
            z: str = 'z',
        ) -> str:
            inner = nodelist.render(context)

            return f'[[x={x},y={y},z={z};{inner}]]'

        self.assertEqual(self._render_tag(my_blocktag, 'x=42 y=100'),
                         '[[x=42,y=100,z=z;123456]]')

    def test_with_keyword_only_args(self) -> None:
        """Testing blocktag with keyword-only arguments"""
        @blocktag
        def my_blocktag(
            context: Context,
            nodelist: NodeList,
            *,
            x: int,
            y: int,
            z: str = 'z',
        ) -> str:
            inner = nodelist.render(context)

            return f'[[x={x},y={y},z={z};{inner}]]'

        self.assertEqual(self._render_tag(my_blocktag, 'x=42 y=100'),
                         '[[x=42,y=100,z=z;123456]]')

    def test_with_var_value(self) -> None:
        """Testing blocktag with variable for arguments"""
        @blocktag
        def my_blocktag(
            context: Context,
            nodelist: NodeList,
            x: int,
            y: int,
            z: str = 'z',
        ) -> str:
            inner = nodelist.render(context)

            return f'[[x={x},y={y},z={z};{inner}]]'

        self.assertEqual(self._render_tag(my_blocktag, 'my_var1 y=my_var2'),
                         '[[x=123,y=456,z=z;123456]]')

    def test_with_arg_filters(self) -> None:
        """Testing blocktag with filters on arguments"""
        @blocktag
        def my_blocktag(
            context: Context,
            nodelist: NodeList,
            x: int,
            y: int,
            z: str = 'z',
        ) -> str:
            inner = nodelist.render(context)

            return f'[[x={x},y={y},z={z};{inner}]]'

        self.assertEqual(self._render_tag(my_blocktag,
                                          'my_var1|add:100 y=my_var2'),
                         '[[x=223,y=456,z=z;123456]]')

    def _render_tag(
        self,
        tag_func: _TagCompiler,
        args: str = '',
    ) -> str:
        """Render a sample blocktag for testing.

        Args:
            tag_func (callable):
                The tag function to call.

            args (str):
                The arguments to pass to the template.

        Returns:
            django.utils.safestring.SafeString:
            The rendered HTML.
        """
        library = Library()
        library.tag(tag_func)

        engine = Engine()
        engine.template_builtins.append(library)

        return (
            engine.from_string(
                '{%% my_blocktag %s %%}'
                '{{my_var1}}{{my_var2}}'
                '{%% endmy_blocktag %%}'
                % args
            )
            .render(context=Context({
                'my_var1': 123,
                'my_var2': 456,
            }))
        )
