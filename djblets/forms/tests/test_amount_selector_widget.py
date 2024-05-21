"""Unit tests for djblets.forms.widgets.AmountSelectorWidget.

Version Added:
    3.3
"""

from djblets.forms.widgets import AmountSelectorWidget
from djblets.testing.testcases import TestCase


class AmountSelectorWidgetTests(TestCase):
    """Unit tests for djblets.forms.widgets.AmountSelectorWidget."""

    def test_value_from_datadict_base(self) -> None:
        """Testing AmountSelectorWidget.value_from_datadict with a value
        in the base unit
        """
        widget = AmountSelectorWidget(unit_choices=[
            (1, 'bytes'),
            (1024, 'kilobytes'),
            (1048576, 'megabytes'),
            (1073741824, 'gigabytes'),
        ])

        # 8 bytes.
        data = {
            'my_field_0': '8',
            'my_field_1': '1',
        }

        self.assertEqual(
            widget.value_from_datadict(data=data, files={}, name='my_field'),
            8)

    def test_value_from_datadict_non_base(self) -> None:
        """Testing AmountSelectorWidget.value_from_datadict with a value
        in one of the non base units
        """
        widget = AmountSelectorWidget(unit_choices=[
            (1, 'bytes'),
            (1024, 'kilobytes'),
            (1048576, 'megabytes'),
            (1073741824, 'gigabytes'),
        ])

        # 2 megabytes.
        data = {
            'my_field_0': '2',
            'my_field_1': '1048576',
        }

        self.assertEqual(
            widget.value_from_datadict(data=data, files={}, name='my_field'),
            2097152)

    def test_value_from_datadict_zero(self) -> None:
        """Testing AmountSelectorWidget.value_from_datadict with a value
        of 0
        """
        widget = AmountSelectorWidget(unit_choices=[
            (1, 'bytes'),
            (1024, 'kilobytes'),
            (1048576, 'megabytes'),
            (1073741824, 'gigabytes'),
        ])

        # 2 megabytes.
        data = {
            'my_field_0': '0',
            'my_field_1': '1024',
        }

        self.assertEqual(
            widget.value_from_datadict(data=data, files={}, name='my_field'),
            0)

    def test_value_from_datadict_with_empty_string(self) -> None:
        """Testing AmountSelectorWidget.value_from_datadict with an empty
        string value
        """
        widget = AmountSelectorWidget(unit_choices=[
            (1, 'bytes'),
            (1024, 'kilobytes'),
            (1048576, 'megabytes'),
            (1073741824, 'gigabytes'),
        ])

        # No unit selected. The amount should be disregarded.
        data = {
            'my_field_0': '5',
            'my_field_1': '',
        }

        self.assertEqual(
            widget.value_from_datadict(data=data, files={}, name='my_field'),
            None)

    def test_value_from_datadict_with_none(self) -> None:
        """Testing AmountSelectorWidget.value_from_datadict with a None value
        """
        widget = AmountSelectorWidget(unit_choices=[
            (1, 'bytes'),
            (1024, 'kilobytes'),
            (1048576, 'megabytes'),
            (1073741824, 'gigabytes'),
        ])

        # No unit selected. The amount should be disregarded.
        data = {
            'my_field_0': '5',
            'my_field_1': None,
        }

        self.assertEqual(
            widget.value_from_datadict(data=data, files={}, name='my_field'),
            None)

    def test_decompress_base(self) -> None:
        """Testing AmountSelectorWidget.decompress with a value in the
        base unit
        """
        widget = AmountSelectorWidget(unit_choices=[
            (1, 'bytes'),
            (1024, 'kilobytes'),
            (1048576, 'megabytes'),
            (1073741824, 'gigabytes'),
        ])

        # 1500 bytes.
        self.assertEqual(widget.decompress(1500), (1500, 1))

    def test_decompress_non_base(self) -> None:
        """Testing AmountSelectorWidget.decompress represents a value in the
        most appropriate unit
        """
        widget = AmountSelectorWidget(unit_choices=[
            (1, 'bytes'),
            (1024, 'kilobytes'),
            (1048576, 'megabytes'),
            (1073741824, 'gigabytes'),
        ])

        # 2 kilobytes.
        self.assertEqual(widget.decompress(2048), (2, 1024))

    def test_decompress_zeroe(self) -> None:
        """Testing AmountSelectorWidget.decompress with a value of 0"""
        widget = AmountSelectorWidget(unit_choices=[
            (1, 'bytes'),
            (1024, 'kilobytes'),
            (1048576, 'megabytes'),
            (1073741824, 'gigabytes'),
        ])

        # 0 gigabytes.
        self.assertEqual(widget.decompress(0), (0, 1073741824))

    def test_decompress_none(self) -> None:
        """Testing AmountSelectorWidget.decompress with a null value"""
        widget = AmountSelectorWidget(unit_choices=[
            (1, 'bytes'),
            (1024, 'kilobytes'),
            (1048576, 'megabytes'),
            (1073741824, 'gigabytes'),
        ])

        self.assertEqual(widget.decompress(None), (None, None))
