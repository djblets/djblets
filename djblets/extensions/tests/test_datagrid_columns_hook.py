"""Unit tests for djblets.extensions.hooks.DataGridColumnsHook."""

from kgb import SpyAgency

from djblets.datagrid.grids import Column, DataGrid
from djblets.extensions.extension import Extension
from djblets.extensions.hooks import DataGridColumnsHook
from djblets.extensions.testing import ExtensionTestCaseMixin
from djblets.testing.testcases import TestCase


class MyTestExtension(Extension):
    pass


class DataGridColumnsHookTest(SpyAgency, ExtensionTestCaseMixin, TestCase):
    """Unit tests for djblets.extensions.hooks.DataGridColumnsHook."""

    extension_class = MyTestExtension

    def test_add_column(self):
        """Testing DataGridColumnsHook registers column"""
        self.spy_on(DataGrid.add_column)

        DataGridColumnsHook(extension=self.extension,
                            datagrid_cls=DataGrid,
                            columns=[Column(id='sandbox')])

        self.assertTrue(DataGrid.add_column.called)

    def test_remove_column(self):
        """Testing DataGridColumnsHook unregisters column"""
        self.spy_on(DataGrid.remove_column)

        hook = DataGridColumnsHook(extension=self.extension,
                                   datagrid_cls=DataGrid,
                                   columns=[Column(id='sandbox2')])

        hook.disable_hook()

        self.assertTrue(DataGrid.remove_column.called)
