#
# tests.py -- Unit tests for classes in djblets.datagrid
#
# Copyright (c) 2007-2008  Christian Hammond
# Copyright (c) 2007-2008  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.http import HttpRequest

from djblets.datagrid.grids import Column, DataGrid, DateTimeSinceColumn
from djblets.util.testing import TestCase


def populate_groups():
    for i in range(1, 100):
        group = Group(name="Group %02d" % i)
        group.save()


class GroupDataGrid(DataGrid):
    objid = Column("ID", link=True, sortable=True, field_name="id")
    name = Column("Group Name", link=True, sortable=True, expand=True)

    def __init__(self, request):
        DataGrid.__init__(self, request, Group.objects.all(), "All Groups")
        self.default_sort = []
        self.default_columns = [
            "objid", "name"
        ]


class ColumnsTest(TestCase):
    def testDateTimeSinceColumn(self):
        """Testing DateTimeSinceColumn"""
        class DummyObj:
            time = None

        column = DateTimeSinceColumn("Test", field_name='time')
        now = datetime.now()

        obj = DummyObj()
        obj.time = now
        self.assertEqual(column.render_data(obj), "0 minutes ago")

        obj.time = now - timedelta(days=5)
        self.assertEqual(column.render_data(obj), "5 days ago")

        obj.time = now - timedelta(days=7)
        self.assertEqual(column.render_data(obj), "1 week ago")


class DataGridTest(TestCase):
    def setUp(self):
        self.old_auth_profile_module = getattr(settings, "AUTH_PROFILE_MODULE",
                                               None)
        settings.AUTH_PROFILE_MODULE = None
        populate_groups()
        self.user = User(username="testuser")
        self.request = HttpRequest()
        self.request.user = self.user
        self.datagrid = GroupDataGrid(self.request)

    def tearDown(self):
        settings.AUTH_PROFILE_MODULE = self.old_auth_profile_module

    def testRender(self):
        """Testing basic datagrid rendering"""
        self.datagrid.render_listview()

    def testRenderToResponse(self):
        """Testing rendering datagrid to HTTPResponse"""
        self.datagrid.render_listview_to_response()

    def testSortAscending(self):
        """Testing datagrids with ascending sort"""
        self.request.GET['sort'] = "name,objid"
        self.datagrid.load_state()

        self.assertEqual(self.datagrid.sort_list, ["name", "objid"])
        self.assertEqual(len(self.datagrid.rows), self.datagrid.paginate_by)
        self.assertEqual(self.datagrid.rows[0]['object'].name, "Group 01")
        self.assertEqual(self.datagrid.rows[1]['object'].name, "Group 02")
        self.assertEqual(self.datagrid.rows[2]['object'].name, "Group 03")

        # Exercise the code paths when rendering
        self.datagrid.render_listview()

    def testSortDescending(self):
        """Testing datagrids with descending sort"""
        self.request.GET['sort'] = "-name"
        self.datagrid.load_state()

        self.assertEqual(self.datagrid.sort_list, ["-name"])
        self.assertEqual(len(self.datagrid.rows), self.datagrid.paginate_by)
        self.assertEqual(self.datagrid.rows[0]['object'].name, "Group 99")
        self.assertEqual(self.datagrid.rows[1]['object'].name, "Group 98")
        self.assertEqual(self.datagrid.rows[2]['object'].name, "Group 97")

        # Exercise the code paths when rendering
        self.datagrid.render_listview()


    def testCustomColumns(self):
        """Testing datagrids with custom column orders"""
        self.request.GET['columns'] = "objid"
        self.datagrid.load_state()

        self.assertEqual(len(self.datagrid.rows), self.datagrid.paginate_by)
        self.assertEqual(len(self.datagrid.rows[0]['cells']), 1)

        # Exercise the code paths when rendering
        self.datagrid.render_listview()
