#
# grids.py -- Basic definitions for datagrids
#
# Copyright (c) 2008-2009  Christian Hammond
# Copyright (c) 2008-2009  David Trowbridge
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
#

import logging
import pytz
import urllib

from django.conf import settings
from django.contrib.auth.models import SiteProfileNotAvailable
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import InvalidPage, QuerySetPaginator
from django.http import Http404, HttpResponse
from django.shortcuts import render_to_response
from django.template.context import RequestContext, Context
from django.template.defaultfilters import date, timesince
from django.template.loader import render_to_string, get_template
from django.utils.cache import patch_cache_control
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _


class Column(object):
    """
    A column in a data grid.

    The column is the primary component of the data grid. It is used to
    display not only the column header but the HTML for the cell as well.

    Columns can be tied to database fields and can be used for sorting.
    Not all columns have to allow for this, though.

    Columns can have an image, text, or both in the column header. The
    contents of the cells can be instructed to link to the object on the
    row or the data in the cell.
    """
    SORT_DESCENDING = 0
    SORT_ASCENDING = 1

    def __init__(self, label=None, detailed_label=None,
                 field_name=None, db_field=None,
                 image_url=None, image_width=None, image_height=None,
                 image_alt="", shrink=False, expand=False, sortable=False,
                 default_sort_dir=SORT_DESCENDING, link=False,
                 link_func=None, cell_clickable=False, css_class=""):
        self.id = None
        self.datagrid = None
        self.field_name = field_name
        self.db_field = db_field or field_name
        self.label = label
        self.detailed_label = detailed_label or self.label
        self.image_url = image_url
        self.image_width = image_width
        self.image_height = image_height
        self.image_alt = image_alt
        self.shrink = shrink
        self.expand = expand
        self.sortable = sortable
        self.default_sort_dir = default_sort_dir
        self.cell_clickable = False
        self.link = link
        self.link_func = link_func or \
            (lambda x, y: self.datagrid.link_to_object(x, y))
        self.css_class = css_class

        self.reset()

    def reset(self):
        # State
        self.active = False
        self.last = False
        self.width = 0
        self.data_cache = {}
        self.cell_render_cache = {}

    def get_toggle_url(self):
        """
        Returns the URL of the current page with this column's visibility
        toggled.
        """
        columns = [column.id for column in self.datagrid.columns]

        if self.active:
            try:
                columns.remove(self.id)
            except ValueError:
                pass
        else:
            columns.append(self.id)

        return "?%scolumns=%s" % (self.get_url_params_except("columns"),
                                  ",".join(columns))
    toggle_url = property(get_toggle_url)

    def get_header(self):
        """
        Displays a sortable column header.

        The column header will include the current sort indicator, if it
        belongs in the sort list. It will also be made clickable in order
        to modify the sort order appropriately, if sortable.
        """
        in_sort = False
        sort_direction = self.SORT_DESCENDING
        sort_primary = False
        sort_url = ""
        unsort_url = ""

        if self.sortable:
            sort_list = list(self.datagrid.sort_list)

            if sort_list:
                rev_column_id = "-%s" % self.id
                new_column_id = self.id
                cur_column_id = ""

                if self.id in sort_list:
                    # This column is currently being sorted in
                    # ascending order.
                    sort_direction = self.SORT_ASCENDING
                    cur_column_id = self.id
                    new_column_id = rev_column_id
                elif rev_column_id in sort_list:
                    # This column is currently being sorted in
                    # descending order.
                    sort_direction = self.SORT_DESCENDING
                    cur_column_id = rev_column_id
                    new_column_id = self.id

                if cur_column_id:
                    in_sort = True
                    sort_primary = (sort_list[0] == cur_column_id)

                    if not sort_primary:
                        # If this is not the primary column, we want to keep
                        # the sort order intact.
                        new_column_id = cur_column_id

                    # Remove this column from the current location in the list
                    # so we can move it to the front of the list.
                    sort_list.remove(cur_column_id)

                # Insert the column name into the beginning of the sort list.
                sort_list.insert(0, new_column_id)
            else:
                # There's no sort list to begin with. Make this column
                # the only entry.
                sort_list = [self.id]

            # We can only support two entries in the sort list, so truncate
            # this.
            del(sort_list[2:])

            url_prefix = "?%ssort=" % self.get_url_params_except("sort",
                                                                 "datagrid-id",
                                                                 "gridonly",
                                                                 "columns")
            unsort_url = url_prefix + ','.join(sort_list[1:])
            sort_url   = url_prefix + ','.join(sort_list)

        if not self.datagrid.column_header_template_obj:
            self.datagrid.column_header_template_obj = \
                get_template(self.datagrid.column_header_template)

        ctx = Context({
            'column': self,
            'in_sort': in_sort,
            'sort_ascending': sort_direction == self.SORT_ASCENDING,
            'sort_primary': sort_primary,
            'sort_url': sort_url,
            'unsort_url': unsort_url,
        })

        return mark_safe(self.datagrid.column_header_template_obj.render(ctx))
    header = property(get_header)

    def get_url_params_except(self, *params):
        """
        Utility function to return a string containing URL parameters to
        this page with the specified parameter filtered out.
        """
        result = urllib.urlencode([
            (key, value)
            for key, value in self.datagrid.request.GET.items()
            if key not in params
        ])
        return result + '&'

    def collect_objects(self, object_list):
        """Iterates through the objects and builds a cache of data to display.

        This optimizes the fetching of data in the grid by grabbing all the
        IDs of related objects that will be queried for rendering, loading
        them all at once, and populating the cache.
        """
        id_field = '%s_id' % self.field_name
        ids = set()
        model = None

        for obj in object_list:
            if not hasattr(obj, id_field):
                # This isn't the field type you're looking for.
                return

            ids.add(getattr(obj, id_field))

            if not model:
                field = getattr(obj.__class__, self.field_name).field

                try:
                    model = field.rel.to
                except AttributeError:
                    # No idea what this is. Bail.
                    return

        if model:
            for obj in model.objects.filter(pk__in=ids):
                self.data_cache[obj.pk] = obj


    def render_cell(self, obj):
        """
        Renders the table cell containing column data.
        """
        rendered_data = self.render_data(obj)
        url = ''
        css_class = ''

        if self.link:
            try:
                url = self.link_func(obj, rendered_data)
            except AttributeError:
                pass

        if self.css_class:
            if callable(self.css_class):
                css_class = self.css_class(obj)
            else:
                css_class = self.css_class

        key = "%s:%s:%s:%s" % (self.last, rendered_data, url, css_class)

        if key not in self.cell_render_cache:
            if not self.datagrid.cell_template_obj:
                self.datagrid.cell_template_obj = \
                    get_template(self.datagrid.cell_template)

                if not self.datagrid.cell_template_obj:
                    logging.error("Unable to load template '%s' for datagrid "
                                  "cell. This may be an installation issue." %
                                  self.datagrid.cell_template)

            ctx = RequestContext(self.datagrid.request, {
                'column': self,
                'css_class': css_class,
                'url': url,
                'data': mark_safe(rendered_data)
            })

            self.cell_render_cache[key] = \
                mark_safe(self.datagrid.cell_template_obj.render(ctx))

        return self.cell_render_cache[key]

    def render_data(self, obj):
        """
        Renders the column data to a string. This may contain HTML.
        """
        id_field = '%s_id' % self.field_name

        # Look for this directly so that we don't end up fetching the
        # data for the object.
        if id_field in obj.__dict__:
            pk = obj.__dict__[id_field]

            if pk in self.data_cache:
                return self.data_cache[pk]
            else:
                value = getattr(obj, self.field_name)
                self.data_cache[pk] = value
                return value
        else:
            value = getattr(obj, self.field_name)

            if callable(value):
                return value()
            else:
                return value

    def augment_queryset(self, queryset):
        """Augments a queryset with new queries.

        Subclasses can override this to extend the queryset to provide
        additional information, usually using queryset.extra(). This must
        return a queryset based on the original queryset.

        This should not restrict the query in any way, or the datagrid may
        not operate properly. It must only add additional data to the
        queryset.
        """
        return queryset


class DateTimeColumn(Column):
    """
    A column that renders a date or time.
    """
    def __init__(self, label, format=None, sortable=True,
                 timezone=pytz.utc, *args, **kwargs):
        Column.__init__(self, label, sortable=sortable, *args, **kwargs)
        self.format = format
        self.timezone = timezone

    def render_data(self, obj):
        # If the datetime object is tz aware, conver it to local time
        datetime = getattr(obj, self.field_name)
        if settings.USE_TZ:
            datetime = pytz.utc.normalize(datetime).\
                astimezone(self.timezone)

        return date(datetime, self.format)


class DateTimeSinceColumn(Column):
    """
    A column that renders a date or time relative to now.
    """
    def __init__(self, label, sortable=True, timezone=pytz.utc,
                 *args, **kwargs):
        Column.__init__(self, label, sortable=sortable, *args, **kwargs)

    def render_data(self, obj):
        return _("%s ago") % timesince(getattr(obj, self.field_name))


class DataGrid(object):
    """
    A representation of a list of objects, sorted and organized by
    columns. The sort order and column lists can be customized. allowing
    users to view this data however they prefer.

    This is meant to be subclassed for specific uses. The subclasses are
    responsible for defining one or more column types. It can also set
    one or more of the following optional variables:

        * 'title':                  The title of the grid.
        * 'profile_sort_field':     The variable name in the user profile
                                    where the sort order can be loaded and
                                    saved.
        * 'profile_columns_field":  The variable name in the user profile
                                    where the columns list can be loaded and
                                    saved.
        * 'paginate_by':            The number of items to show on each page
                                    of the grid. The default is 50.
        * 'paginate_orphans':       If this number of objects or fewer are
                                    on the last page, it will be rolled into
                                    the previous page. The default is 3.
        * 'page':                   The page to display. If this is not
                                    specified, the 'page' variable passed
                                    in the URL will be used, or 1 if that is
                                    not specified.
        * 'listview_template':      The template used to render the list view.
                                    The default is 'datagrid/listview.html'
        * 'column_header_template': The template used to render each column
                                    header. The default is
                                    'datagrid/column_header.html'
        * 'cell_template':          The template used to render a cell of
                                    data. The default is 'datagrid/cell.html'
        * 'optimize_sorts':         Whether or not to optimize queries when
                                    using multiple sorts. This can offer a
                                    speed improvement, but may need to be
                                    turned off for more advanced querysets
                                    (such as when using extra()).
                                    The default is True.
    """
    def __init__(self, request, queryset=None, title="", extra_context={},
                 optimize_sorts=True):
        self.request = request
        self.queryset = queryset
        self.rows = []
        self.columns = []
        self.all_columns = []
        self.db_field_map = {}
        self.id_list = []
        self.paginator = None
        self.page = None
        self.sort_list = None
        self.state_loaded = False
        self.page_num = 0
        self.id = None
        self.extra_context = dict(extra_context)
        self.optimize_sorts = optimize_sorts
        self.cell_template_obj = None
        self.column_header_template_obj = None

        if not hasattr(request, "datagrid_count"):
            request.datagrid_count = 0

        self.id = "datagrid-%s" % request.datagrid_count
        request.datagrid_count += 1

        # Customizable variables
        self.title = title
        self.profile_sort_field = None
        self.profile_columns_field = None
        self.paginate_by = 50
        self.paginate_orphans = 3
        self.listview_template = 'datagrid/listview.html'
        self.column_header_template = 'datagrid/column_header.html'
        self.cell_template = 'datagrid/cell.html'

        for attr in dir(self):
            column = getattr(self, attr)
            if isinstance(column, Column):
                self.all_columns.append(column)
                column.datagrid = self
                column.id = attr

                # Reset the column.
                column.reset()

                if not column.field_name:
                    column.field_name = column.id

                if not column.db_field:
                    column.db_field = column.field_name

                self.db_field_map[column.id] = column.db_field

        self.all_columns.sort(key=lambda x: x.label)


    def load_state(self):
        """
        Loads the state of the datagrid.

        This will retrieve the user-specified or previously stored
        sorting order and columns list, as well as any state a subclass
        may need.
        """
        if self.state_loaded:
            return

        profile_sort_list = None
        profile_columns_list = None
        profile = None
        profile_dirty = False

        # Get the saved settings for this grid in the profile. These will
        # work as defaults and allow us to determine if we need to save
        # the profile.
        if self.request.user.is_authenticated():
            try:
                profile = self.request.user.get_profile()

                if self.profile_sort_field:
                    profile_sort_list = \
                        getattr(profile, self.profile_sort_field, None)

                if self.profile_columns_field:
                    profile_columns_list = \
                        getattr(profile, self.profile_columns_field, None)
            except SiteProfileNotAvailable:
                pass
            except ObjectDoesNotExist:
                pass


        # Figure out the columns we're going to display
        # We're also going to calculate the column widths based on the
        # shrink and expand values.
        colnames_str = self.request.GET.get('columns', profile_columns_list)

        if colnames_str:
            colnames = colnames_str.split(',')
        else:
            colnames = self.default_columns
            colnames_str = ",".join(colnames)

        expand_columns = []
        normal_columns = []

        for colname in colnames:
            try:
                column = getattr(self, colname)
            except AttributeError:
                # The user specified a column that doesn't exist. Skip it.
                continue

            self.columns.append(column)
            column.active = True

            if column.expand:
                # This column is requesting all remaining space. Save it for
                # later so we can tell how much to give it. Each expanded
                # column will count as two normal columns when calculating
                # the normal sized columns.
                expand_columns.append(column)
            elif column.shrink:
                # Make this as small as possible.
                column.width = 0
            else:
                # We'll divide the column widths equally after we've built
                # up the lists of expanded and normal sized columns.
                normal_columns.append(column)

        self.columns[-1].last = True

        # Try to figure out the column widths for each column.
        # We'll start with the normal sized columns.
        total_pct = 100

        # Each expanded column counts as two normal columns.
        normal_column_width = total_pct / (len(self.columns) +
                                           len(expand_columns))

        for column in normal_columns:
            column.width = normal_column_width
            total_pct -= normal_column_width

        if len(expand_columns) > 0:
            expanded_column_width = total_pct / len(expand_columns)
        else:
            expanded_column_width = 0

        for column in expand_columns:
            column.width = expanded_column_width


        # Now get the sorting order for the columns.
        sort_str = self.request.GET.get('sort', profile_sort_list)

        if sort_str:
            self.sort_list = sort_str.split(',')
        else:
            self.sort_list = self.default_sort
            sort_str = ",".join(self.sort_list)


        # A subclass might have some work to do for loading and saving
        # as well.
        if self.load_extra_state(profile):
            profile_dirty = True


        # Now that we have all that, figure out if we need to save new
        # settings back to the profile.
        if profile:
            if self.profile_columns_field and \
               colnames_str != profile_columns_list:
                setattr(profile, self.profile_columns_field, colnames_str)
                profile_dirty = True

            if self.profile_sort_field and sort_str != profile_sort_list:
                setattr(profile, self.profile_sort_field, sort_str)
                profile_dirty = True

            if profile_dirty:
                profile.save()

        self.state_loaded = True

        # Fetch the list of objects and have it ready.
        self.precompute_objects()


    def load_extra_state(self, profile):
        """
        Loads any extra state needed for this grid.

        This is used by subclasses that may have additional data to load
        and save. This should return True if any profile-stored state has
        changed, or False otherwise.
        """
        return False

    def precompute_objects(self):
        """
        Builds the queryset and stores the list of objects for use in
        rendering the datagrid.
        """
        query = self.queryset
        use_select_related = False

        # Generate the actual list of fields we'll be sorting by
        sort_list = []
        for sort_item in self.sort_list:
            if sort_item[0] == "-":
                base_sort_item = sort_item[1:]
                prefix = "-"
            else:
                base_sort_item = sort_item
                prefix = ""

            if sort_item and base_sort_item in self.db_field_map:
                db_field = self.db_field_map[base_sort_item]
                sort_list.append(prefix + db_field)

                # Lookups spanning tables require that we query from those
                # tables. In order to keep things simple, we'll just use
                # select_related so that we don't have to figure out the
                # table relationships. We only do this if we have a lookup
                # spanning tables.
                if '.' in db_field:
                    use_select_related = True

        if sort_list:
            query = query.order_by(*sort_list)

        self.paginator = QuerySetPaginator(query.distinct(), self.paginate_by,
                                           self.paginate_orphans)

        page_num = self.request.GET.get('page', 1)

        # Accept either "last" or a valid page number.
        if page_num == "last":
            page_num = self.paginator.num_pages

        try:
            self.page = self.paginator.page(page_num)
        except InvalidPage:
            raise Http404

        self.id_list = []

        if self.optimize_sorts and len(sort_list) > 0:
            # This can be slow when sorting by multiple columns. If we
            # have multiple items in the sort list, we'll request just the
            # IDs and then fetch the actual details from that.
            self.id_list = list(self.page.object_list.values_list(
                'pk', flat=True))

            # Make sure to unset the order. We can't meaningfully order these
            # results in the query, as what we really want is to keep it in
            # the order specified in id_list, and we certainly don't want
            # the database to do any special ordering (possibly slowing things
            # down). We'll set the order properly in a minute.
            self.page.object_list = self.post_process_queryset(
                self.queryset.model.objects.filter(
                    pk__in=self.id_list).order_by())

        if use_select_related:
            self.page.object_list = \
                self.page.object_list.select_related(depth=1)

        if self.id_list:
            # The database will give us the items in a more or less random
            # order, since it doesn't know to keep it in the order provided by
            # the ID list. This will place the results back in the order we
            # expect.
            index = dict([(id, pos) for (pos, id) in enumerate(self.id_list)])
            object_list = [None] * len(self.id_list)

            for obj in list(self.page.object_list):
                object_list[index[obj.pk]] = obj
        else:
            # Grab the whole list at once. We know it won't be too large,
            # and it will prevent one query per row.
            object_list = list(self.page.object_list)

        for column in self.columns:
            column.collect_objects(object_list)

        self.rows = [
            {
                'object': obj,
                'cells': [column.render_cell(obj) for column in self.columns]
            }
            for obj in object_list if obj is not None
        ]

    def post_process_queryset(self, queryset):
        """
        Processes a QuerySet after the initial query has been built and
        pagination applied. This is only used when optimizing a sort.

        By default, this just returns the existing queryset. Custom datagrid
        subclasses can override this to add additional queries (such as
        subqueries in an extra() call) for use in the cell renderers.

        When optimize_sorts is True, subqueries (using extra()) on the initial
        QuerySet passed to the datagrid will be stripped from the final
        result. This function can be used to re-add those subqueries.
        """
        for column in self.columns:
            queryset = column.augment_queryset(queryset)

        return queryset

    def render_listview(self):
        """
        Renders the standard list view of the grid.

        This can be called from templates.
        """
        self.load_state()

        context = {
            'datagrid': self,
            'is_paginated': self.page.has_other_pages(),
            'results_per_page': self.paginate_by,
            'has_next': self.page.has_next(),
            'has_previous': self.page.has_previous(),
            'page': self.page.number,
            'next': self.page.next_page_number(),
            'previous': self.page.previous_page_number(),
            'last_on_page': self.page.end_index(),
            'first_on_page': self.page.start_index(),
            'pages': self.paginator.num_pages,
            'hits': self.paginator.count,
            'page_range': self.paginator.page_range,
        }
        context.update(self.extra_context)

        return mark_safe(render_to_string(self.listview_template,
            RequestContext(self.request, context)))

    def render_listview_to_response(self, request=None):
        """
        Renders the listview to a response, preventing caching in the
        process.
        """
        response = HttpResponse(unicode(self.render_listview()))
        patch_cache_control(response, no_cache=True, no_store=True, max_age=0,
                            must_revalidate=True)
        return response

    def render_to_response(self, template_name, extra_context={}):
        """
        Renders a template containing this datagrid as a context variable.
        """
        self.load_state()

        # If the caller is requesting just this particular grid, return it.
        if self.request.GET.get('gridonly', False) and \
           self.request.GET.get('datagrid-id', None) == self.id:
            return self.render_listview_to_response()

        context = {
            'datagrid': self
        }
        context.update(extra_context)
        context.update(self.extra_context)

        return render_to_response(template_name, RequestContext(self.request,
                                                                context))

    @staticmethod
    def link_to_object(obj, value):
        return obj.get_absolute_url()

    @staticmethod
    def link_to_value(obj, value):
        return value.get_absolute_url()
