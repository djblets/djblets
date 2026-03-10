"""Unit tests for djblets.datagrid."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import kgb
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.db.models import Count, Q
from django.http import HttpRequest
from django.test.client import RequestFactory
from django.utils.encoding import force_str
from django.utils.safestring import SafeString
from django_assert_queries import assert_queries

from djblets.datagrid.grids import (CheckboxColumn,
                                    Column,
                                    DataGrid,
                                    DateTimeColumn,
                                    DateTimeSinceColumn,
                                    StatefulColumn,
                                    logger)
from djblets.testing.testcases import TestCase
from djblets.util.dates import get_tz_aware_utcnow


class GroupDataGrid(DataGrid):
    objid = Column(
        'ID',
        link=True,
        sortable=True,
        field_name='id',
    )

    name = Column(
        'Group Name',
        link=True,
        sortable=True,
        expand=True,
    )

    other_column = Column(
        'Other Column',
    )

    def __init__(self, request, **kwargs):
        super().__init__(
            request=request,
            queryset=Group.objects.order_by('pk'),
            title='All Groups',
            **kwargs,
        )

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

    def test_to_json_with_selected(self) -> None:
        """Testing CheckboxColumn.to_json with selected object"""
        group = Group.objects.create(name='test')

        datagrid = DataGrid(request=RequestFactory().request(),
                            queryset=Group.objects.all())

        column = CheckboxColumn()
        column.is_selected = lambda *args, **kwargs: True  # type: ignore

        state = StatefulColumn(datagrid=datagrid,
                               column=column)

        self.assertIs(column.to_json(state, group), True)

    def test_to_json_with_unselected(self) -> None:
        """Testing CheckboxColumn.to_json with unselected object"""
        group = Group.objects.create(name='test')

        datagrid = DataGrid(request=RequestFactory().request(),
                            queryset=Group.objects.all())

        column = CheckboxColumn()
        state = StatefulColumn(datagrid=datagrid,
                               column=column)

        self.assertIs(column.to_json(state, group), False)

    def test_to_json_with_not_selectable(self) -> None:
        """Testing CheckboxColumn.to_json with non-selectable object"""
        group = Group.objects.create(name='test')

        datagrid = DataGrid(request=RequestFactory().request(),
                            queryset=Group.objects.all())

        column = CheckboxColumn()
        column.is_selectable = lambda *args, **kwargs: False  # type: ignore

        state = StatefulColumn(datagrid=datagrid,
                               column=column)

        self.assertIs(column.to_json(state, group), False)


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

    def test_to_json(self) -> None:
        """Testing DateTimeSinceColumn.to_json"""
        class DummyObj:
            time: (datetime | None) = None

        datagrid = DataGrid(request=RequestFactory().request(),
                            queryset=Group.objects.all())

        column = DateTimeSinceColumn('Test', field_name='time')
        state = StatefulColumn(datagrid=datagrid,
                               column=column)

        obj = DummyObj()
        obj.time = datetime(2026, 2, 15, 10, 20, 30,
                            tzinfo=UTC)

        self.assertEqual(column.to_json(state, obj),
                         '2026-02-15T10:20:30+00:00')

    def test_to_json_with_none(self) -> None:
        """Testing DateTimeSinceColumn.to_json with None value"""
        class DummyObj:
            time = None

        datagrid = DataGrid(request=RequestFactory().request(),
                            queryset=Group.objects.all())

        column = DateTimeSinceColumn('Test',
                                     field_name='time')
        state = StatefulColumn(datagrid=datagrid,
                               column=column)

        self.assertIsNone(column.to_json(state, DummyObj()))


class DateTimeColumnTests(TestCase):
    """Unit tests for djblets.datagrid.grids.DateTimeColumn."""

    def test_to_json(self) -> None:
        """Testing DateTimeColumn.to_json"""
        class DummyObj:
            time: (datetime | None) = None

        datagrid = DataGrid(request=RequestFactory().request(),
                            queryset=Group.objects.all())

        column = DateTimeColumn('Test',
                                field_name='time')
        state = StatefulColumn(datagrid=datagrid,
                               column=column)

        obj = DummyObj()
        obj.time = datetime(2026, 2, 15, 10, 20, 30,
                            tzinfo=UTC)

        self.assertEqual(column.to_json(state, obj),
                         '2026-02-15T10:20:30+00:00')

    def test_to_json_with_none(self) -> None:
        """Testing DateTimeColumn.to_json with None value"""
        class DummyObj:
            time = None

        datagrid = DataGrid(request=RequestFactory().request(),
                            queryset=Group.objects.all())

        column = DateTimeColumn('Test',
                                field_name='time')
        state = StatefulColumn(datagrid=datagrid,
                               column=column)

        self.assertIsNone(column.to_json(state, DummyObj()))


class DataGridTests(kgb.SpyAgency, TestCase):
    """Unit tests for djblets.datagrid.grids.DataGrid."""

    maxDiff = None

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

        self.assertIsInstance(result, SafeString)
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

    def test_render_paginator(self) -> None:
        """Testing DataGrid.render_paginator"""
        datagrid = self.datagrid
        datagrid.load_state()

        content = datagrid.render_paginator()

        self.assertHTMLEqual(
            content,
            '<div class="paginator">'
            ' <span class="current-page">1</span>'
            ' <a href="?page=2" title="Page 2">2</a>'
            ' <a href="?page=2" rel="next" title="Next Page">&gt;</a>'
            ' <span class="page-count">2 pages&nbsp;</span>'
            '</div>')

    def test_render_paginator_with_first(self) -> None:
        """Testing DataGrid.render_paginator with first page link"""
        self.request.GET['page'] = '10'

        datagrid = self.datagrid
        datagrid.paginate_by = 10
        datagrid.load_state()

        content = datagrid.render_paginator()

        self.assertHTMLEqual(
            content,
            '<div class="paginator">'
            ' <a href="?" rel="first" title="First Page">«</a>'
            ' <a href="?page=9" rel="prev" title="Previous Page">&lt;</a>'
            ' <a href="?page=7" title="Page 7">7</a>'
            ' <a href="?page=8" title="Page 8">8</a>'
            ' <a href="?page=9" title="Page 9">9</a>'
            ' <span class="current-page">10</span>'
            ' <span class="page-count">10 pages&nbsp;</span>'
            '</div>')

    def test_render_paginator_with_last(self) -> None:
        """Testing DataGrid.render_paginator with last page link"""
        datagrid = self.datagrid
        datagrid.paginate_by = 10
        datagrid.load_state()

        content = datagrid.render_paginator()

        self.assertHTMLEqual(
            content,
            '<div class="paginator">'
            ' <span class="current-page">1</span>'
            ' <a href="?page=2" title="Page 2">2</a>'
            ' <a href="?page=3" title="Page 3">3</a>'
            ' <a href="?page=4" title="Page 4">4</a>'
            ' <a href="?page=2" rel="next" title="Next Page">&gt;</a>'
            ' <a href="?page=10" rel="last nofollow" title="Last Page">»</a>'
            ' <span class="page-count">10 pages&nbsp;</span>'
            '</div>')

    def test_render_paginator_with_search_indexing_disabled(self) -> None:
        """Testing DataGrid.render_paginator with search indexing disabled"""
        self.request.GET['page'] = '10'

        datagrid = self.datagrid
        datagrid.allow_search_indexing = False
        datagrid.paginate_by = 2
        datagrid.load_state()

        content = datagrid.render_paginator()

        self.assertHTMLEqual(
            content,
            '<div class="paginator">'
            ' <a href="?" rel="first nofollow noindex"'
            ' title="First Page">«</a>'
            ' <a href="?page=9" rel="prev nofollow noindex"'
            ' title="Previous Page">&lt;</a>'
            ' <a href="?page=7" rel="nofollow noindex" title="Page 7">7</a>'
            ' <a href="?page=8" rel="nofollow noindex" title="Page 8">8</a>'
            ' <a href="?page=9" rel="nofollow noindex" title="Page 9">9</a>'
            ' <span class="current-page">10</span>'
            ' <a href="?page=11" rel="nofollow noindex" title="Page 11">11</a>'
            ' <a href="?page=12" rel="nofollow noindex" title="Page 12">12</a>'
            ' <a href="?page=13" rel="nofollow noindex" title="Page 13">13</a>'
            ' <a href="?page=11" rel="next nofollow noindex"'
            ' title="Next Page">&gt;</a>'
            ' <a href="?page=48" rel="last nofollow noindex"'
            ' title="Last Page">»</a>'
            ' <span class="page-count">48 pages&nbsp;</span>'
            '</div>')

    def test_load_state_with_sort_ascending_init(self) -> None:
        """Testing DataGrid.load_state with ascending sort in __init__"""
        datagrid = GroupDataGrid(request=self.request,
                                 sort=['name', 'objid'])
        datagrid.load_state()

        self.assertEqual(datagrid.sort_list, ['name', 'objid'])
        self.assertEqual(len(datagrid.rows), datagrid.paginate_by)
        self.assertEqual(datagrid.rows[0]['object'].name, 'Group 01')
        self.assertEqual(datagrid.rows[1]['object'].name, 'Group 02')
        self.assertEqual(datagrid.rows[2]['object'].name, 'Group 03')

        # Exercise the code paths when rendering.
        result = datagrid.render_listview()
        self.assertIsInstance(result, SafeString)
        self.assertIn('<div class="datagrid-wrapper" id="datagrid-1">',
                      result)

    def test_load_state_with_sort_ascending_request(self) -> None:
        """Testing DataGrid.load_state with ascending sort in request"""
        self.request.GET['sort'] = 'name,objid'

        datagrid = self.datagrid
        datagrid.load_state()

        self.assertEqual(datagrid.sort_list, ['name', 'objid'])
        self.assertEqual(len(datagrid.rows), datagrid.paginate_by)
        self.assertEqual(datagrid.rows[0]['object'].name, 'Group 01')
        self.assertEqual(datagrid.rows[1]['object'].name, 'Group 02')
        self.assertEqual(datagrid.rows[2]['object'].name, 'Group 03')

        # Exercise the code paths when rendering.
        result = datagrid.render_listview()
        self.assertIsInstance(result, SafeString)
        self.assertIn('<div class="datagrid-wrapper" id="datagrid-0">',
                      result)

    def test_load_state_with_sort_descending_init(self) -> None:
        """Testing DataGrid.load_state with descending sort in __init__"""
        datagrid = GroupDataGrid(request=self.request,
                                 sort=['-name'])
        datagrid.load_state()

        self.assertEqual(datagrid.sort_list, ['-name'])
        self.assertEqual(len(datagrid.rows), datagrid.paginate_by)
        self.assertEqual(datagrid.rows[0]['object'].name, 'Group 99')
        self.assertEqual(datagrid.rows[1]['object'].name, 'Group 98')
        self.assertEqual(datagrid.rows[2]['object'].name, 'Group 97')

        # Exercise the code paths when rendering.
        result = datagrid.render_listview()
        self.assertIsInstance(result, SafeString)
        self.assertIn('<div class="datagrid-wrapper" id="datagrid-1">',
                      result)

    def test_load_state_with_sort_descending_request(self) -> None:
        """Testing DataGrid.load_state with descending sort in request"""
        self.request.GET['sort'] = '-name'

        datagrid = self.datagrid
        datagrid.load_state()

        self.assertEqual(datagrid.sort_list, ['-name'])
        self.assertEqual(len(datagrid.rows), datagrid.paginate_by)
        self.assertEqual(datagrid.rows[0]['object'].name, 'Group 99')
        self.assertEqual(datagrid.rows[1]['object'].name, 'Group 98')
        self.assertEqual(datagrid.rows[2]['object'].name, 'Group 97')

        # Exercise the code paths when rendering.
        result = datagrid.render_listview()
        self.assertIsInstance(result, SafeString)
        self.assertIn('<div class="datagrid-wrapper" id="datagrid-0">',
                      result)

    def test_load_state_with_sort_none_init(self) -> None:
        """Testing DataGrid.load_state with sort=None in __init__"""
        class MyGroupDataGrid(GroupDataGrid):
            def __init__(self, **kwargs) -> None:
                super().__init__(**kwargs)

                self.default_sort = ['-objid']

        request = self.request
        request.GET['sort'] = '-name'

        datagrid = MyGroupDataGrid(request=request,
                                   sort=None)
        datagrid.load_state()

        self.assertEqual(datagrid.sort_list, ['-objid'])
        self.assertEqual(len(datagrid.rows), datagrid.paginate_by)
        self.assertEqual(datagrid.rows[0]['object'].name, 'Group 99')
        self.assertEqual(datagrid.rows[1]['object'].name, 'Group 98')
        self.assertEqual(datagrid.rows[2]['object'].name, 'Group 97')

        # Exercise the code paths when rendering.
        result = datagrid.render_listview()
        self.assertIsInstance(result, SafeString)
        self.assertIn('<div class="datagrid-wrapper" id="datagrid-1">',
                      result)

    def test_load_state_with_custom_columns_init(self) -> None:
        """Testing DataGrid.load_state with custom columns in __init__"""
        datagrid = GroupDataGrid(request=self.request,
                                 columns=['objid'])
        datagrid.load_state()

        objid_column = datagrid.get_column('objid')
        assert objid_column is not None

        self.assertEqual(
            datagrid.columns,
            [
                datagrid.get_stateful_column(objid_column),
            ])

        self.assertEqual(len(datagrid.rows), datagrid.paginate_by)
        self.assertEqual(len(datagrid.rows[0]['cells']), 1)

        result = datagrid.render_listview()

        self.assertIsInstance(result, SafeString)
        self.assertIn('<div class="datagrid-wrapper" id="datagrid-1">',
                      result)

    def test_load_state_with_custom_columns_request(self) -> None:
        """Testing DataGrid.load_state with custom columns in request.GET
        """
        self.request.GET['columns'] = 'objid'

        datagrid = self.datagrid
        datagrid.load_state()

        objid_column = datagrid.get_column('objid')
        assert objid_column is not None

        self.assertEqual(
            datagrid.columns,
            [
                datagrid.get_stateful_column(objid_column),
            ])

        self.assertEqual(len(datagrid.rows), datagrid.paginate_by)
        self.assertEqual(len(datagrid.rows[0]['cells']), 1)

        # Exercise the code paths when rendering.
        result = datagrid.render_listview()

        self.assertIsInstance(result, SafeString)
        self.assertIn('<div class="datagrid-wrapper" id="datagrid-0">',
                      result)

    def test_load_state_with_columns_none_init(self) -> None:
        """Testing DataGrid.load_state with columns=None in __init__"""
        request = self.request
        request.GET['columns'] = 'name'

        datagrid = GroupDataGrid(request=request,
                                 columns=None)
        datagrid.load_state()

        objid_column = datagrid.get_column('objid')
        name_column = datagrid.get_column('name')

        assert objid_column is not None
        assert name_column is not None

        self.assertEqual(
            datagrid.columns,
            [
                datagrid.get_stateful_column(objid_column),
                datagrid.get_stateful_column(name_column),
            ])

        self.assertEqual(len(datagrid.rows), datagrid.paginate_by)
        self.assertEqual(len(datagrid.rows[0]['cells']), 2)

        result = datagrid.render_listview()

        self.assertIsInstance(result, SafeString)
        self.assertIn('<div class="datagrid-wrapper" id="datagrid-1">',
                      result)

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

    def test_load_state_with_stored_settings_columns_and_init(self) -> None:
        """Testing DataGrid.load_state with stored columns changed on load
        and not saved due to being in __init__
        """
        class MyProfile:
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

        datagrid = TestDataGrid(request=self.request,
                                columns=['objid'])
        datagrid.load_state()

        # The explicitly-defined columns will not be saved.
        self.assertSpyNotCalled(my_profile.save)
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

    def test_load_state_with_stored_settings_sort_changed_and_init(
        self,
    ) -> None:
        """Testing DataGrid.load_state with stored sort changed on load
        and not saved due to being in __init__
        """
        class MyProfile:
            my_columns = 'objid,name'
            my_sort = 'objid'

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

        datagrid = TestDataGrid(request=request,
                                sort=['-name'])
        datagrid.load_state()

        # The explicitly-defined sort order will not be saved.
        self.assertSpyNotCalled(my_profile.save)
        self.assertEqual(my_profile.my_columns, 'objid,name')
        self.assertEqual(my_profile.my_sort, 'objid')

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

        with assert_queries(queries):
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

        grid = TestDataGrid(request=self.request,
                            queryset=Group.objects.all())
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

    def test_to_json(self) -> None:
        """Testing DataGrid.to_json"""
        self.assertEqual(
            self.datagrid.to_json(),
            {
                'available_columns': [
                    {
                        'expand': False,
                        'id': 'other_column',
                        'label': 'Other Column',
                        'shrink': False,
                        'sortable': False,
                        'width': 0,
                    },
                ],
                'columns': [
                    {
                        'expand': False,
                        'id': 'objid',
                        'label': 'ID',
                        'shrink': False,
                        'sortable': True,
                        'width': 33.333333333333336,
                    },
                    {
                        'expand': True,
                        'id': 'name',
                        'label': 'Group Name',
                        'shrink': False,
                        'sortable': True,
                        'width': 66.66666666666666,
                    },
                ],
                'rows': [
                    {
                        'cells': {
                            'name': {
                                'html': (
                                    f'<td colspan="2">\n'
                                    f'\n'
                                    f' Group {i:02}\n'
                                    f'\n'
                                    f'</td>\n'
                                ),
                                'value': f'Group {i:02}',
                            },
                            'objid': {
                                'html': (
                                    f'<td>\n'
                                    f'\n'
                                    f' {i}\n'
                                    f'\n'
                                    f'</td>\n'
                                ),
                                'value': i,
                            },
                        },
                        'url': None,
                    }
                    for i in range(1, 51)
                ],
                'pagination': {
                    'current_page': 1,
                    'end_index': 50,
                    'has_next': True,
                    'has_previous': False,
                    'per_page': 50,
                    'start_index': 1,
                    'total_count': 99,
                    'total_pages': 2,
                },
                'sort': [],
            })


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

    def test_to_json(self) -> None:
        """Testing Column.to_json"""
        group = Group.objects.create(name='Test Group')

        datagrid = DataGrid(request=RequestFactory().request(),
                            queryset=Group.objects.all())

        column = Column(id='name',
                        field_name='name')
        state = StatefulColumn(datagrid=datagrid,
                               column=column)

        self.assertEqual(column.to_json(state, group),
                         'Test Group')

    def test_to_json_with_no_field_name(self) -> None:
        """Testing Column.to_json with no field name"""
        group = Group.objects.create(name='Test Group')

        datagrid = DataGrid(request=RequestFactory().request(),
                            queryset=Group.objects.all())

        column = Column(id='test')
        state = StatefulColumn(datagrid=datagrid,
                               column=column)

        self.assertIsNone(column.to_json(state, group))

    def test_to_json_with_dotted_field(self) -> None:
        """Testing Column.to_json with dotted field name"""
        class DummyObj:
            def __init__(self) -> None:
                self.related = DummyRelated()

        class DummyRelated:
            def __init__(self) -> None:
                self.value = 'nested_value'

        datagrid = DataGrid(request=RequestFactory().request(),
                            queryset=Group.objects.all())

        column = Column(id='test',
                        field_name='related.value')
        state = StatefulColumn(datagrid=datagrid,
                               column=column)

        self.assertEqual(column.to_json(state, DummyObj()),
                         'nested_value')

    def test_to_json_with_callable(self) -> None:
        """Testing Column.to_json with callable field"""
        class DummyObj:
            def get_display_name(self):
                return 'Display Name'

        datagrid = DataGrid(request=RequestFactory().request(),
                            queryset=Group.objects.all())

        column = Column(id='test',
                        field_name='get_display_name')
        state = StatefulColumn(datagrid=datagrid,
                               column=column)

        self.assertEqual(column.to_json(state, DummyObj()),
                         'Display Name')
