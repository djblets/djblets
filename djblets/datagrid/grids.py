from django.core.exceptions import ObjectDoesNotExist
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

    def __init__(self, label=None, field_name=None,
                 image_url=None, image_width=None, image_height=None,
                 image_alt="", shrink=False, expand=False, sortable=False,
                 default_sort_dir=SORT_DESCENDING, link=False,
                 link_func=None, cell_clickable=False, css_class=""):
        self.datagrid = None
        self.field_name = field_name
        self.label = label
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
        self.width = 0

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
                rev_field_name = "-%s" % self.field_name
                new_field_name = self.field_name
                cur_field_name = ""

                if self.field_name in sort_list:
                    # This column is currently being sorted in
                    # ascending order.
                    sort_direction = self.SORT_ASCENDING
                    cur_field_name = self.field_name
                    new_field_name = rev_field_name
                elif rev_field_name in sort_list:
                    # This column is currently being sorted in
                    # descending order.
                    sort_direction = self.SORT_DESCENDING
                    cur_field_name = rev_field_name
                    new_field_name = self.field_name

                if cur_field_name:
                    in_sort = True
                    sort_primary = (sort_list[0] == cur_field_name)

                    if not sort_primary:
                        # If this is not the primary column, we want to keep
                        # the sort order intact.
                        new_field_name = cur_field_name

                    # Remove this column from the current location in the list
                    # so we can move it to the front of the list.
                    sort_list.remove(cur_field_name)

                # Insert the column name into the beginning of the sort list.
                sort_list.insert(0, new_field_name)
            else:
                # There's no sort list to begin with. Make this column
                # the only entry.
                sort_list = [self.field_name]

            # We can only support two entries in the sort list, so truncate
            # this.
            del(sort_list[2:])

            url_prefix = "?"

            for key in self.datagrid.request.GET:
                if key != "sort":
                    url_prefix += "%s=%s&" % \
                        (key, self.datagrid.request.GET[key])

            url_prefix += "sort="

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

    def render_cell(self, obj):
        """
        Renders the table cell containing column data.
        """
        rendered_data = self.render_data(obj)
        s = "<td"

        if self.css_class:
            if callable(self.css_class):
                s += ' class="%s"' % self.css_class(obj)
            else:
                s += ' class="%s"' % self.css_class

        url = ""
        if self.link:
            try:
                url = self.link_func(obj, rendered_data)
            except AttributeError:
                pass

        if url:
            if self.cell_clickable:
                s += ' onclick="javascript:window.location=\'%s\'; ' \
                     'return false;"' % url

            s += '><a href="%s">%s</a></td>' % (url, rendered_data)
        else:
            s += '>%s</td>' % rendered_data

        return mark_safe(s)

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

        * 'profile_sort_field':     The variable name in the user profile
                                    where the sort order can be loaded and
                                    saved.
        * 'profile_columns_field":  The variable name in the user profile
                                    where the columns list can be loaded and
                                    saved.
        * 'paginate_by':            The default number of items to show on
                                    each page of the grid.
        * 'listview_template':      The template used to render the list view.
                                    The default is 'datagrid/listview.html'
        * 'column_header_template': The template used to render each column
                                    header. The default is
                                    'datagrid/column_header.html'
    """
    def __init__(self, request, queryset=None, title=""):
        self.request = request
        self.queryset = queryset
        self.columns = []
        self.sort_list = None
        self.state_loaded = False

        # Customizable variables
        self.title = title
        self.profile_sort_field = None
        self.profile_columns_field = None
        self.paginate_by = 50
        self.listview_template = 'datagrid/listview.html'
        self.column_header_template = 'datagrid/column_header.html'

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

        for colname in colnames:
            try:
                column = getattr(self, colname)
            except AttributeError:
                # The user specified a column that doesn't exist. Skip it.
                continue

            column.datagrid = self
            self.columns.append(column)

            if not column.field_name:
                column.field_name = colname

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

    def load_extra_state(self, profile):
        """
        Loads any extra state needed for this grid.

        This is used by subclasses that may have additional data to load
        and save. This should return True if any profile-stored state has
        changed, or False otherwise.
        """
        return False

    def rows(self):
        """
        Retrieves the rows of the grid, sorted by the current sort order.

        The resulting data is a dictionary with the following keys:

            * 'object': The object represented in the row.
            * 'cells':  The cells in the row.
        """
        query = self.queryset

        # See if we have any valid entries in sort_list. If so, apply them.
        for sort_item in self.sort_list:
            if sort_item:
                query = query.order_by(*self.sort_list)
                break

        for obj in query:
            yield {
                'object': obj,
                'cells': [column.render_cell(obj) for column in self.columns]
            }

    def render_listview(self):
        """
        Renders the standard list view of the grid.

        This can be called from templates.
        """
        self.load_state()

        return mark_safe(render_to_string(self.listview_template,
            RequestContext(self.request, {
                'datagrid': self,
            })))

    def render_to_response(self, template_name, extra_context={}):
        """
        Renders a template containing this datagrid as a context variable.
        """
        self.load_state()

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
