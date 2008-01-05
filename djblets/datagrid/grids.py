from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import InvalidPage, ObjectPaginator
from django.http import Http404, HttpResponse
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.template.defaultfilters import date, timesince
from django.template.loader import render_to_string
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

        # State
        self.active = False
        self.last = False
        self.width = 0

    def get_toggle_url(self):
        """
        Returns the URL of the current page with this column's visibility
        toggled.
        """
        columns = [column.id for column in self.datagrid.columns]

        if self.active:
            columns.remove(self.id)
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
                                                                 "columns")
            unsort_url = url_prefix + ','.join(sort_list[1:])
            sort_url   = url_prefix + ','.join(sort_list)

        return mark_safe(render_to_string(self.datagrid.column_header_template,
            RequestContext(self.datagrid.request, {
                'column': self,
                'in_sort': in_sort,
                'sort_ascending': sort_direction == self.SORT_ASCENDING,
                'sort_primary': sort_primary,
                'sort_url': sort_url,
                'unsort_url': unsort_url,
            })))
    header = property(get_header)

    def get_url_params_except(self, *params):
        """
        Utility function to return a string containing URL parameters to
        this page with the specified parameter filtered out.
        """
        s = ""

        for key in self.datagrid.request.GET:
            if key not in params:
                s += "%s=%s&" % (key, self.datagrid.request.GET[key])

        return s

    def render_cell(self, obj):
        """
        Renders the table cell containing column data.
        """
        rendered_data = self.render_data(obj)
        css_class = ""
        url = ""

        if self.css_class:
            if callable(self.css_class):
                css_class = self.css_class(obj)
            else:
                css_class = self.css_class

        if self.link:
            try:
                url = self.link_func(obj, rendered_data)
            except AttributeError:
                pass

        return mark_safe(render_to_string(self.datagrid.cell_template,
            RequestContext(self.datagrid.request, {
                'column': self,
                'css_class': css_class,
                'url': url,
                'data': mark_safe(rendered_data)
            })))

    def render_data(self, obj):
        """
        Renders the column data to a string. This may contain HTML.
        """
        value = getattr(obj, self.field_name)

        if callable(value):
            return value()
        else:
            return value


class DateTimeColumn(Column):
    """
    A column that renders a date or time.
    """
    def __init__(self, label, format=None, sortable=True, *args, **kwargs):
        Column.__init__(self, label, sortable=sortable, *args, **kwargs)
        self.format = format

    def render_data(self, obj):
        return date(getattr(obj, self.field_name), self.format)


class DateTimeSinceColumn(Column):
    """
    A column that renders a date or time relative to now.
    """
    def __init__(self, label, sortable=True, *args, **kwargs):
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
    """
    def __init__(self, request, queryset=None, title=""):
        self.request = request
        self.queryset = queryset
        self.rows = []
        self.columns = []
        self.all_columns = []
        self.db_field_map = {}
        self.paginator = None
        self.sort_list = None
        self.state_loaded = False
        self.page_num = 0
        self.id = None

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
        self.page = None
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
                column.active = False
                column.last = False
                column.width = 0

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
        self.db_field_map = {}

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

        expanded_column_width = total_pct / len(expand_columns)

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
            if sort_item and sort_item in self.db_field_map:
                db_field = self.db_field_map[sort_item]
                sort_list.append(db_field)

                # Lookups spanning tables require that we query from those
                # tables. In order to keep things simple, we'll just use
                # select_related so that we don't have to figure out the
                # table relationships. We only do this if we have a lookup
                # spanning tables.
                if '.' in db_field:
                    use_select_related = True

        if sort_list:
            query = query.order_by(*sort_list)

        if use_select_related:
            query = query.select_related(depth=1)

        self.paginator = ObjectPaginator(query, self.paginate_by,
                                         self.paginate_orphans)

        if not self.page:
            page = self.request.GET.get('page', 1)

        # Accept either "last" or a valid page number.
        if page == "last":
            self.page_num = self.paginator.pages
        else:
            try:
                self.page_num = int(page)
            except ValueError:
                raise Http404

        try:
            object_list = self.paginator.get_page(self.page_num - 1)
        except InvalidPage:
            if self.page_num == 1:
                # Our queryset is empty.
                object_list = []
            else:
                raise Http404

        self.rows = []

        for obj in object_list:
            self.rows.append({
                'object': obj,
                'cells': [column.render_cell(obj) for column in self.columns]
            })

    def render_listview(self):
        """
        Renders the standard list view of the grid.

        This can be called from templates.
        """
        self.load_state()

        return mark_safe(render_to_string(self.listview_template,
            RequestContext(self.request, {
                'datagrid': self,
                'is_paginated': self.paginator.pages > 1,
                'results_per_page': self.paginate_by,
                'has_next': self.paginator.has_next_page(self.page_num - 1),
                'has_previous':
                    self.paginator.has_previous_page(self.page_num - 1),
                'page': self.page_num,
                'next': self.page_num + 1,
                'previous': self.page_num - 1,
                'last_on_page': self.paginator.last_on_page(self.page_num - 1),
                'first_on_page':
                    self.paginator.first_on_page(self.page_num - 1),
                'pages': self.paginator.pages,
                'hits': self.paginator.hits,
                'page_range': self.paginator.page_range,
            })))

    def render_to_response(self, template_name, extra_context={}):
        """
        Renders a template containing this datagrid as a context variable.
        """
        self.load_state()

        # If the caller is requesting just this particular grid, return it.
        if self.request.GET.get('gridonly', False) and \
           self.request.GET.get('datagrid-id', None) == self.id:
            return HttpResponse(unicode(self.render_listview()))

        context = {
            'datagrid': self
        }
        context.update(extra_context)

        return render_to_response(template_name, RequestContext(self.request,
                                                 context))

    @staticmethod
    def link_to_object(obj, value):
        return obj.get_absolute_url()

    @staticmethod
    def link_to_value(obj, value):
        return value.get_absolute_url()
