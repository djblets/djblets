"""Unit tests for djblets.datagrid."""

from datetime import datetime, timedelta

import kgb
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.db.models import Count, Q
from django.http import HttpRequest
from django.test.client import RequestFactory
from django.utils.encoding import force_str
from django.utils.safestring import SafeText

from djblets.datagrid.grids import (CheckboxColumn, Column, DataGrid,
                                    DateTimeSinceColumn, StatefulColumn,
                                    logger)
from djblets.testing.testcases import TestCase
from djblets.util.dates import get_tz_aware_utcnow


class GroupDataGrid(DataGrid):
    objid = Column('ID', link=True, sortable=True, field_name='id')
    name = Column('Group Name', link=True, sortable=True, expand=True)

    def __init__(self, request):
        super(GroupDataGrid, self).__init__(
            request=request,
            queryset=Group.objects.order_by('pk'),
            title='All Groups')
        self.default_sort = []
        self.default_columns = ['objid', 'name']


class CheckboxColumnTests(TestCase):
    """Unit tests for djblets.datagrid.grids.CheckboxColumn."""

    def test_initial_state(self):
        """Testing CheckboxColumn initial state"""
        column = CheckboxColumn(checkbox_name='my_checkbox&',
                                detailed_label='<Select Rows>')

        self.assertHTMLEqual(
            column.label,
            '<input class="datagrid-header-checkbox" '
            ' type="checkbox" data-checkbox-name="my_checkbox&amp;">')
        self.assertHTMLEqual(
            column.detailed_label_html,
            '<input type="checkbox"> &lt;Select Rows&gt;')
        self.assertEqual(column.detailed_label, '<Select Rows>')
        self.assertEqual(column.checkbox_name, 'my_checkbox&')

    def test_render_data_with_selected(self):
        """Testing CheckboxColumn.render_data with selected object"""
        group = Group.objects.create(name='test')

        column = CheckboxColumn(checkbox_name='my_checkbox&',
                                detailed_label='<Select Rows>')
        column.is_selected = lambda *args, **kwargs: True

        self.assertHTMLEqual(
            column.render_data(state=None, obj=group),
            '<input type="checkbox" data-object-id="1"'
            ' data-checkbox-name="my_checkbox&amp;" checked="true">')

    def test_render_data_with_unselected(self):
        """Testing CheckboxColumn.render_data with unselected object"""
        group = Group.objects.create(name='test')

        column = CheckboxColumn(checkbox_name='my_checkbox&',
                                detailed_label='<Select Rows>')

        self.assertHTMLEqual(
            column.render_data(state=None, obj=group),
            '<input type="checkbox" data-object-id="1"'
            ' data-checkbox-name="my_checkbox&amp;">')


class DateTimeSinceColumnTests(TestCase):
    """Unit tests for djblets.datagrid.grids.DateTimeSinceColumn."""

    def test_render_data(self):
        """Testing DateTimeSinceColumn.render_data"""
        class DummyObj:
            time = None

        column = DateTimeSinceColumn('Test', field_name='time')
        state = StatefulColumn(None, column)

        if settings.USE_TZ:
            now = get_tz_aware_utcnow()
        else:
            now = datetime.now()

        obj = DummyObj()
        obj.time = now
        self.assertEqual(column.render_data(state, obj), '0\xa0minutes ago')

        obj.time = now - timedelta(days=5)
        self.assertEqual(column.render_data(state, obj), '5\xa0days ago')

        obj.time = now - timedelta(days=7)
        self.assertEqual(column.render_data(state, obj), '1\xa0week ago')


class DataGridTests(kgb.SpyAgency, TestCase):
    """Unit tests for djblets.datagrid.grids.DataGrid."""

    def setUp(self):
        super(DataGridTests, self).setUp()

        Group.objects.bulk_create(
            Group(name='Group %02d' % i)
            for i in range(1, 100)
        )

        self.user = User(username='testuser')
        self.request = HttpRequest()
        self.request.user = self.user
        self.datagrid = GroupDataGrid(self.request)

    def test_render_listview(self):
        """Testing DataGrid.render_listview"""
        result = self.datagrid.render_listview()

        self.assertIsInstance(result, SafeText)
        self.assertIn('<div class="datagrid-wrapper" id="datagrid-0">', result)
        self.assertIn('<div class="datagrid-main">', result)
        self.assertInHTML('<td colspan="2">Group 01</td>', result)
        self.assertInHTML('<td colspan="2">Group 50</td>', result)
        self.assertIn('<div class="paginator">', result)
        self.assertIn('<div class="datagrid-menu', result)

    def test_render_listview_to_response(self):
        """Testing DataGrid.render_listview_to_response"""
        response = self.datagrid.render_listview_to_response()
        self.assertEqual(response.status_code, 200)

        content = force_str(response.content)

        self.assertIn('<div class="datagrid-wrapper" id="datagrid-0">',
                      content)
        self.assertIn('<div class="datagrid-main">', content)
        self.assertInHTML('<td colspan="2">Group 01</td>', content)
        self.assertInHTML('<td colspan="2">Group 50</td>', content)
        self.assertIn('<div class="paginator">', content)
        self.assertIn('<div class="datagrid-menu', content)

    def test_render_paginator(self):
        """Testing DataGrid.render_paginator"""
        self.datagrid.load_state()
        content = self.datagrid.render_paginator()

        self.assertHTMLEqual(
            content,
            '<div class="paginator">'
            ' <span class="current-page">1</span>'
            ' <a href="?page=2" title="Page 2">2</a>'
            ' <a href="?page=2" title="Next Page">&gt;</a>'
            ' <span class="page-count">2 pages&nbsp;</span>'
            '</div>')

    def test_load_state_with_sort_ascending(self):
        """Testing DataGrid.load_state with ascending sort"""
        self.request.GET['sort'] = 'name,objid'
        self.datagrid.load_state()

        self.assertEqual(self.datagrid.sort_list, ['name', 'objid'])
        self.assertEqual(len(self.datagrid.rows), self.datagrid.paginate_by)
        self.assertEqual(self.datagrid.rows[0]['object'].name, 'Group 01')
        self.assertEqual(self.datagrid.rows[1]['object'].name, 'Group 02')
        self.assertEqual(self.datagrid.rows[2]['object'].name, 'Group 03')

        # Exercise the code paths when rendering.
        result = self.datagrid.render_listview()
        self.assertIsInstance(result, SafeText)
        self.assertIn('<div class="datagrid-wrapper" id="datagrid-0">', result)

    def test_load_state_with_sort_descending(self):
        """Testing DataGrid.load_state with descending sort"""
        self.request.GET['sort'] = '-name'
        self.datagrid.load_state()

        self.assertEqual(self.datagrid.sort_list, ['-name'])
        self.assertEqual(len(self.datagrid.rows), self.datagrid.paginate_by)
        self.assertEqual(self.datagrid.rows[0]['object'].name, 'Group 99')
        self.assertEqual(self.datagrid.rows[1]['object'].name, 'Group 98')
        self.assertEqual(self.datagrid.rows[2]['object'].name, 'Group 97')

        # Exercise the code paths when rendering.
        result = self.datagrid.render_listview()
        self.assertIsInstance(result, SafeText)
        self.assertIn('<div class="datagrid-wrapper" id="datagrid-0">', result)

    def test_load_state_with_custom_column_orders(self):
        """Testing DataGrid.load_state with custom column orders"""
        self.request.GET['columns'] = 'objid'
        self.datagrid.load_state()

        self.assertEqual(len(self.datagrid.rows), self.datagrid.paginate_by)
        self.assertEqual(len(self.datagrid.rows[0]['cells']), 1)

        # Exercise the code paths when rendering.
        result = self.datagrid.render_listview()
        self.assertIsInstance(result, SafeText)
        self.assertIn('<div class="datagrid-wrapper" id="datagrid-0">', result)

    def test_load_state_with_load_extra_state_fields(self):
        """Testing DataGrid.load_state with load_extra_state returning fields
        """
        class MyProfile(object):
            def save(self, **kwargs):
                pass

        class TestDataGrid(GroupDataGrid):
            def get_user_profile(self):
                return my_profile

            def load_extra_state(self, profile):
                return ['field1', 'field2']

        my_profile = MyProfile()
        self.spy_on(my_profile.save)

        datagrid = TestDataGrid(request=self.request)
        datagrid.load_state()

        self.assertSpyCalledWith(
            my_profile.save,
            update_fields=['field1', 'field2'])

    def test_load_state_with_load_extra_state_no_fields(self):
        """Testing DataGrid.load_state with load_extra_state returning no
        fields
        """
        class MyProfile(object):
            def save(self, **kwargs):
                pass

        class TestDataGrid(GroupDataGrid):
            def get_user_profile(self):
                return my_profile

            def load_extra_state(self, profile):
                return []

        my_profile = MyProfile()
        self.spy_on(my_profile.save)

        datagrid = TestDataGrid(request=self.request)
        datagrid.load_state()

        self.assertSpyNotCalled(my_profile.save)

    def test_load_state_with_stored_settings_no_changes(self) -> None:
        """Testing DataGrid.load_state with stored columns and sort field
        unchanged on load
        """
        class MyProfile(object):
            my_columns = 'name'
            my_sort = 'name'

            def save(self, **kwargs):
                pass

        class TestDataGrid(GroupDataGrid):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

                self.profile_columns_field = 'my_columns'
                self.profile_sort_field = 'my_sort'

            def get_user_profile(self):
                return my_profile

        my_profile = MyProfile()
        self.spy_on(my_profile.save)

        datagrid = TestDataGrid(request=self.request)
        datagrid.load_state()

        self.assertSpyNotCalled(my_profile.save)
        self.assertEqual(my_profile.my_columns, 'name')
        self.assertEqual(my_profile.my_sort, 'name')

    def test_load_state_with_stored_settings_columns_changed(self) -> None:
        """Testing DataGrid.load_state with stored columns changed on load"""
        class MyProfile(object):
            my_columns = 'name'
            my_sort = 'name'

            def save(self, **kwargs):
                pass

        class TestDataGrid(GroupDataGrid):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

                self.profile_columns_field = 'my_columns'
                self.profile_sort_field = 'my_sort'

            def get_user_profile(self):
                return my_profile

        my_profile = MyProfile()
        self.spy_on(my_profile.save)

        request = self.request
        request.GET['columns'] = 'objid,name'

        datagrid = TestDataGrid(request=request)
        datagrid.load_state()

        self.assertSpyCalledWith(my_profile.save,
                                 update_fields=['my_columns'])
        self.assertEqual(my_profile.my_columns, 'objid,name')
        self.assertEqual(my_profile.my_sort, 'name')

    def test_load_state_with_stored_settings_columns_bad(self) -> None:
        """Testing DataGrid.load_state with stored columns in bad format"""
        class MyProfile(object):
            my_columns = '[name--'
            my_sort = 'name'

            def save(self, **kwargs):
                pass

        class TestDataGrid(GroupDataGrid):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

                self.profile_columns_field = 'my_columns'
                self.profile_sort_field = 'my_sort'

            def get_user_profile(self):
                return my_profile

        my_profile = MyProfile()
        self.spy_on(my_profile.save)

        datagrid = TestDataGrid(request=self.request)
        datagrid.load_state()

        self.assertSpyCalledWith(my_profile.save,
                                 update_fields=['my_columns'])
        self.assertEqual(my_profile.my_columns, 'objid,name')
        self.assertEqual(my_profile.my_sort, 'name')

    def test_load_state_with_stored_settings_sort_changed(self) -> None:
        """Testing DataGrid.load_state with stored sort changed on load"""
        class MyProfile(object):
            my_columns = 'objid,name'
            my_sort = 'name'

            def save(self, **kwargs):
                pass

        class TestDataGrid(GroupDataGrid):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

                self.profile_columns_field = 'my_columns'
                self.profile_sort_field = 'my_sort'

            def get_user_profile(self):
                return my_profile

        my_profile = MyProfile()
        self.spy_on(my_profile.save)

        request = self.request
        request.GET['sort'] = 'objid'

        datagrid = TestDataGrid(request=request)
        datagrid.load_state()

        self.assertSpyCalledWith(my_profile.save,
                                 update_fields=['my_sort'])
        self.assertEqual(my_profile.my_columns, 'objid,name')
        self.assertEqual(my_profile.my_sort, 'objid')

    def test_load_state_with_stored_settings_sort_bad(self) -> None:
        """Testing DataGrid.load_state with stored sort in bad format"""
        class MyProfile(object):
            my_columns = 'name'
            my_sort = '[name--'

            def save(self, **kwargs):
                pass

        class TestDataGrid(GroupDataGrid):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

                self.profile_columns_field = 'my_columns'
                self.profile_sort_field = 'my_sort'
                self.default_sort = ['name']

            def get_user_profile(self):
                return my_profile

        my_profile = MyProfile()
        self.spy_on(my_profile.save)

        datagrid = TestDataGrid(request=self.request)
        datagrid.load_state()

        self.assertSpyCalledWith(my_profile.save,
                                 update_fields=['my_sort'])
        self.assertEqual(my_profile.my_columns, 'name')
        self.assertEqual(my_profile.my_sort, 'name')

    def test_precompute_objects_with_unsortable_column_ascending(self):
        """Testing DataGrid.precompute_objects with improper sort key
        in ascending order
        """
        self.request.GET['sort'] = 'garbagetrash'
        self.datagrid.load_state()
        self.datagrid.precompute_objects()

        self.assertEqual(self.datagrid.sort_list, [])

    def test_precompute_objects_with_unsortable_column_descending(self):
        """Testing DataGrid.load_state with improper sort key in
        descending order
        """
        self.request.GET['sort'] = '-garbagetrash'
        self.datagrid.load_state()
        self.datagrid.precompute_objects()

        self.assertEqual(self.datagrid.sort_list, [])

    def test_precompute_objects_with_mixed_column_ascending(self):
        """Testing DataGrid.load_state with one proper and one improper sort
        key in ascending order
        """
        self.request.GET['sort'] = 'garbagetrash,name'
        self.datagrid.load_state()
        self.datagrid.precompute_objects()

        self.assertEqual(self.datagrid.sort_list, ['name'])

    def test_precompute_objects_with_mixed_column_descending(self):
        """Testing DataGrid.load_state with one proper and one improper sort
        key in descending order
        """
        self.request.GET['sort'] = '-garbagetrash,-name'
        self.datagrid.load_state()
        self.datagrid.precompute_objects()

        self.assertEqual(self.datagrid.sort_list, ['-name'])

    def test_precompute_objects_with_filtering_and_data(self):
        """Testing DataGrid.precompute_objects with filtering and data
        queryset augmentation applied
        """
        class Column1(Column):
            def augment_queryset_for_filter(self, state, queryset, **kwargs):
                return queryset.filter(is_active=True)

        class Column2(Column):
            def augment_queryset_for_data(self, state, queryset, **kwargs):
                return queryset.annotate(Count('groups'))

        class TestDataGrid(DataGrid):
            username = Column1()
            date_joined = Column2()

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

                self.default_columns = ['username', 'date_joined']
                self.default_sort = []

            def post_process_queryset_for_filter(self, queryset, **kwargs):
                return super().post_process_queryset_for_filter(
                    queryset.filter(email__endswith='@example.com'))

            def post_process_queryset_for_data(self, queryset, **kwargs):
                return super().post_process_queryset_for_data(
                    queryset.only('pk', 'username', 'date_joined'))

        group1 = Group.objects.create(name='group1')
        group2 = Group.objects.create(name='group2')
        group3 = Group.objects.create(name='group3')

        user1 = User.objects.create(
            username='user1',
            email='user1@example.com')
        user1.groups.add(group1)

        user2 = User.objects.create(
            username='user2',
            email='user2@example.com')
        user2.groups.add(group1, group2)

        user3 = User.objects.create(
            username='user3',
            email='user3@example.com')
        user3.groups.add(group1, group2, group3)

        datagrid = TestDataGrid(
            request=self.request,
            queryset=User.objects.order_by('pk'))
        datagrid.load_state()

        queries = [
            {
                'annotations': {'__count': Count('*')},
                'model': User,
                'where': (Q(email__endswith='@example.com') &
                          Q(is_active=True)),
            },
            {
                'annotations': {
                    'groups__count': Count('groups'),
                },
                'distinct': True,
                'group_by': True,
                'join_types': {
                    'auth_user_groups': 'LEFT OUTER JOIN',
                },
                'limit': 3,
                'model': User,
                'num_joins': 1,
                'only_fields': {
                    'date_joined',
                    'id',
                    'username',
                },
                'order_by': ('pk',),
                'tables': {
                    'auth_user',
                    'auth_user_groups',
                },
                'where': (Q(email__endswith='@example.com') &
                          Q(is_active=True)),
            },
        ]

        with self.assertQueries(queries):
            datagrid.precompute_objects()

        rows = datagrid.rows

        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]['object'], user1)
        self.assertEqual(rows[1]['object'], user2)
        self.assertEqual(rows[2]['object'], user3)

    def test_post_process_queryset_with_select_related(self):
        """Testing DataGrid.post_process_queryset with chained select_related
        calls
        """
        class Column1(Column):
            def augment_queryset(self, state, queryset):
                return queryset.select_related('foo')

        class Column2(Column):
            def augment_queryset(self, state, queryset):
                return queryset.select_related('foo__bar')

        class Column3(Column):
            def augment_queryset(self, state, queryset):
                return queryset.select_related('foo', 'foo__abc')

        class TestDataGrid(DataGrid):
            col1 = Column1()
            col2 = Column2()
            col3 = Column3()

            def __init__(self, *args, **kwargs):
                super(TestDataGrid, self).__init__(*args, **kwargs)

                self.default_columns = ['col1', 'col2', 'col3']
                self.default_sort = []

            def post_process_queryset(self, queryset):
                return super(TestDataGrid, self).post_process_queryset(
                    queryset.select_related('baz'))

        grid = TestDataGrid(self.request, queryset=Group.objects.all())
        grid.columns = [
            grid.get_stateful_column(grid.get_column(name))
            for name in grid.default_columns
        ]

        queryset = grid.post_process_queryset(grid.queryset)

        self.assertEqual(
            queryset.query.select_related,
            {
                'foo': {
                    'bar': {},
                    'abc': {},
                },
                'baz': {},
            })

    def test_post_process_queryset_sandboxes_errors(self):
        """Testing DataGrid.post_process_queryset with column.augment_queryset
        raises exception
        """
        class BadColumn(Column):
            def augment_queryset(self, state, queryset):
                raise Exception

        column = BadColumn(id='test')
        self.datagrid.add_column(column)

        self.spy_on(column.augment_queryset)
        self.spy_on(logger.exception)

        try:
            self.datagrid.columns = [
                self.datagrid.get_stateful_column(column),
            ]
            self.datagrid.post_process_queryset(queryset=Group.objects.all())
        finally:
            self.datagrid.remove_column(column)

        self.assertTrue(column.augment_queryset.called)
        self.assertIn('Error when calling augment_queryset for DataGrid '
                      'Column',
                      logger.exception.last_call.args[0])

    def test_get_stateful_column_sandboxes_errors(self):
        """Testing DataGrid.get_stateful_column when column.setup_state
        raises exception
        """
        class BadColumn(Column):
            def setup_state(self, state):
                raise Exception

        column = BadColumn(id='test')
        self.datagrid.add_column(column)

        self.spy_on(column.setup_state)
        self.spy_on(logger.exception)

        try:
            self.datagrid.get_stateful_column(column=column)
        finally:
            self.datagrid.remove_column(column)

        self.assertTrue(column.setup_state.called)
        self.assertIn('Error when calling setup_state for DataGrid Column',
                      logger.exception.last_call.args[0])

    def test_get_sort_field_columns_sandboxes_errors(self):
        """Testing DataGrid.get_sort_field_columns when column.get_sort_field
        raises exception
        """
        class BadColumn(Column):
            def get_sort_field(self, state):
                raise Exception

        column = BadColumn(id='test', sortable=True)
        self.datagrid.add_column(column)

        self.datagrid.sort_list = ['test']
        self.datagrid.default_columns = ['objid', 'test']

        self.spy_on(column.get_sort_field)
        self.spy_on(logger.exception)

        try:
            self.datagrid.precompute_objects()
        finally:
            self.datagrid.remove_column(column)

        self.assertTrue(column.get_sort_field.called)
        self.assertIn('Error when calling get_sort_field for DataGrid Column',
                      logger.exception.last_call.args[0])


class ColumnTests(kgb.SpyAgency, TestCase):
    """Unit tests for djblets.datagrid.grids.Column."""

    def test_render_cell_sandboxes_errors(self):
        """Testing Column.render_cell when column.render_data raises exception
        """
        class BadColumn(Column):
            def render_data(self, state, obj):
                raise Exception

        request = RequestFactory().request()
        datagrid = DataGrid(request=request,
                            queryset=Group.objects.all())

        column = BadColumn(id='test')
        self.spy_on(column.render_data)
        self.spy_on(logger.exception)

        rendered = column.render_cell(state=StatefulColumn(datagrid=datagrid,
                                                           column=column),
                                      obj=None,
                                      render_context=None)
        self.assertHTMLEqual(rendered, '<td></td>')

        self.assertTrue(column.render_data.called)
        self.assertIn('Error when calling render_data for DataGrid Column',
                      logger.exception.last_call.args[0])
