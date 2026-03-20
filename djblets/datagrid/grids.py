"""Components for creating customizable datagrids from database data.

Datagrids are used to display a table-based view of data from a database,
complete with pagination, batch selection, sorting, and flexible column
rendering.

Datagrids have one or more :py:class:`Column` subclasses associated, which will
render the data. The datagrid may display a subset of the rendered columns,
and users can choose which of those columns they want displayed, and in which
order.

There are two main types of datagrids:

* :py:class:`DataGrid` is the base class for a datagrid, and will display
  the data with standard numerical page-based pagination.

* :py:class:`AlphanumericDataGrid` is similar, but uses a more specific
  paginator that allows the user to paginate by the first letter/number/symbol
  of the data in a given field. This is useful for lists of users, for
  example.

All datagrids are meant to be subclassed.
"""

from __future__ import annotations

import logging
import re
import string
import traceback
from datetime import datetime
from typing import (Any, Callable, Dict, Iterable, List, Optional, Sequence,
                    Set, TYPE_CHECKING, Type, Union)
from urllib.parse import urlencode

import pytz
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import InvalidPage, Paginator
from django.db.models import QuerySet
from django.http import Http404, HttpResponse
from django.template.defaultfilters import date
from django.template.loader import get_template, render_to_string
from django.utils.cache import add_never_cache_headers
from django.utils.functional import cached_property
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe
from django.utils.timesince import timesince
from django.utils.translation import gettext_lazy as _
from housekeeping import deprecate_non_keyword_only_args
from typing_extensions import Final, TypeAlias, TypedDict
from typelets.symbols import UNSET

from djblets.deprecation import RemovedInDjblets70Warning
from djblets.template.context import get_default_template_context_processors
from djblets.util.http import get_url_params_except

if TYPE_CHECKING:
    from collections.abc import Mapping

    from django.core.paginator import Page
    from django.db.models import Model
    from django.http import HttpRequest
    from django.template.backends.base import _EngineTemplate
    from django.template.context import Context
    from django.utils.safestring import SafeString

    from typelets.django.json import SerializableDjangoJSONValue
    from typelets.django.strings import StrOrPromise
    from typelets.symbols import Unsettable

    _RenderContext: TypeAlias = Union[
        Context,
        Dict[str, Any],
    ]

    class _DataGridRow(TypedDict):
        cells: Sequence[SafeString]
        object: Any
        url: str | None


class DataGridColumnJSONData(TypedDict):
    """JSON-serializable data for a column definition in a datagrid.

    Version Added:
        5.3
    """

    #: Whether the column expands to take available space.
    expand: bool

    #: The ID of the column.
    id: str

    #: The displayed label of the column.
    label: str

    #: Whether the column shrinks to take minimal space.
    shrink: bool

    #: Whether the column is sortable.
    sortable: bool

    #: The calculated width of the column, as a percentage.
    width: float


class DataGridCellJSONData(TypedDict):
    """JSON-serializable data for a cell in a datagrid row.

    Version Added:
        5.3
    """

    #: The rendered HTML contents of the cell.
    #:
    #: This will be wrapped in a ``<td>``, and may contain CSS classes and
    #: column span information. Consumers may want to use that information
    #: and then normalize it for display, depending on their needs.
    html: SafeString

    #: A JSON value representing the contents of the cell.
    value: SerializableDjangoJSONValue


class DataGridRowJSONData(TypedDict):
    """JSON-serializable data for a row in a datagrid.

    Version Added:
        5.3
    """

    #: A mapping of column IDs to cell JSON data.
    cells: Mapping[str, DataGridCellJSONData]

    #: An optional URL represented by the row.
    url: str | None


class DataGridPaginationJSONData(TypedDict):
    """JSON-serializable data for a datagrid's pagination state.

    Version Added:
        5.3
    """

    #: The current 1-based page number of the results.
    current_page: int

    #: The 1-based index of the last row in the result.
    #:
    #: This index is within the total list of objects across all pages.
    end_index: int

    #: Whether there's a next page of results.
    has_next: bool

    #: Whether there's a previous page of results.
    has_previous: bool

    #: The number of rows to show per page.
    per_page: int

    #: The 1-based index of the first row in the result.
    #:
    #: This index is within the total list of objects across all pages.
    start_index: int

    #: The total number of rows across all pages.
    total_count: int

    #: The total number of pages.
    total_pages: int


class DataGridSortItemJSONData(TypedDict):
    """JSON-serializable data for a column sort item.

    Version Added:
        5.3
    """

    #: Whether the column is sorted in ascending order.
    ascending: bool

    #: The ID of the sorted column.
    column: str


class DataGridJSONData(TypedDict):
    """JSON-serializable data for a datagrid.

    This can be fed into
    :py:class:`~djblets.util.serializers.DjbletsJSONEncoder` to serialize to
    a JSON document.

    Version Added:
        5.3
    """

    #: JSON data on all active columns shown in the datagrid.
    columns: Sequence[DataGridColumnJSONData]

    #: JSON data on all inactive columns for the datagrid.
    available_columns: Sequence[DataGridColumnJSONData]

    #: JSON data on each row shown in the datagrid.
    rows: Sequence[DataGridRowJSONData]

    #: JSON data on the pagination state.
    pagination: DataGridPaginationJSONData

    #: JSON data on all the selected sort criteria.
    sort: Sequence[DataGridSortItemJSONData]


logger = logging.getLogger(__name__)


# Registration of all datagrid classes to columns.
_column_registry: Dict[Type[DataGrid], Dict[str, Column]] = {}


class DataGridPaginator(Paginator):
    """The default paginator used for datagrids.

    This is a specialized paginator that takes in a total count separately
    from the page data queryset. This allows the datagrid code to more
    efficiently calculate pagination data.

    Version Added:
        3.4
    """

    ######################
    # Instance variables #
    ######################

    #: The total number of items across all pages.
    #:
    #: Type:
    #:     int
    _total_count: int

    def __init__(
        self,
        *,
        total_count: int,
        **kwargs,
    ) -> None:
        """Initialize the paginator.

        Args:
            total_count (int):
                The total number of items across all pages.

            **kwargs (dict):
                Additional keyword argumens for the parent class.
        """
        super().__init__(**kwargs)

        self._total_count = total_count

    @cached_property
    def count(self) -> int:
        """The total number of items across all pages.

        Type:
            int
        """
        return self._total_count


class Column:
    """A column in a datagrid.

    The column is the primary component of the datagrid. It is used to
    display not only the column header but the HTML for the cell as well.

    Columns can be tied to database fields and can be used for sorting.
    Not all columns have to allow for this, though.

    Columns can have an image, text, or both in the column header. The
    contents of the cells can be instructed to link to the object on the
    row or the data in the cell.

    If a Column defines an :py:attr:`image_class`, then it will be assumed that
    the class represents an icon, perhaps as part of a spritesheet, and will
    display it in a ``<div>``. An :py:attr:`image_url` cannot also be defined.

    Version Changed:
        5.3:
        Options for the column can now be set as class attributes when
        subclassing.
    """

    #: Descending sort order for columns.
    SORT_DESCENDING: Final[int] = 0

    #: Ascending sort order for columns.
    SORT_ASCENDING: Final[int] = 1

    ##########################################
    # Class customization/instance variables #
    ##########################################

    #: Unused option to indicate a cell is clickable.
    #:
    #: This has never been used and should not be used by any code.
    #:
    #: Deprecated:
    #:     5.3:
    #:     This will be removed in Djblets 7.
    cell_clickable: bool = False

    #: The path to a template for the cell.
    #:
    #: If provided, this will override the :py:attr:`DataGrid.cell_template`
    #: in the parent DataGrid.
    cell_template: (str | None) = None

    #: A function or string for CSS classes applied to the cell.
    css_class: (str | BuildCSSClassFunc) = ''

    #: The name of the database field containing the field used for sorting.
    #:
    #: Once columns are populated for a datagrid, this is guaranteed to be
    #: set.
    db_field: str = ''

    #: The default sorting direction when the user activates sorting.
    #:
    #: This must be either :py:attr:`SORT_ASCENDING` or
    #: :py:attr:`SORT_DESCENDING`.
    default_sort_dir: int = SORT_DESCENDING

    #: A detailed label to display in the Edit Columns menu.
    #:
    #: Defaults to :py:attr:`label`.
    detailed_label: (StrOrPromise | None) = None

    #: A detailed label in HTML form to display in the Edit Columns menu.
    #:
    #: This takes precedence over :py:attr:`detailed_label`.
    detailed_label_html: (StrOrPromise | SafeString | None) = None

    #: Whether the column will expand to the maximum size allowed.
    #:
    #: If there are other expanded columns, they'll share the available width
    #: equally.
    expand: bool = False

    #: The name of the field on the model containing the data to render.
    #:
    #: Once columns are populated for a datagrid, this is guaranteed to be
    #: set.
    field_name: str = ''

    #: The unique ID of the column on the datagrid.
    #:
    #: Once columns are populated for a datagrid, this is guaranteed to be
    #: set.
    id: str = ''

    #: The alt text for an image.
    image_alt: (StrOrPromise | None) = ''

    #: The CSS spritesheet icon class to use in the header/navigation menu.
    image_class: (str | None) = None

    #: The height of the image.
    image_height: (int | None) = None

    #: The URL to the image used in the header/navigation menu.
    image_url: (str | None) = None

    #: The width of the image.
    image_width: (int | None) = None

    #: The label to show in the column header.
    label: (StrOrPromise | None) = None

    #: Whether the contents of the cell will be linked to a URL.
    #:
    #: The URL used must be defined by either :py:attr:`link_func` or
    #: :py:meth:`DataGrid.link_to_object`.
    link: bool = False

    #: A function or string for CSS classes applied to a link.
    #:
    #: The CSS classes will be defined on the ``<a>`` for the cell's link
    #: wrapper. This is only used if :py:attr:`link` is ``True``.
    link_css_class: (str | LinkCSSClassFunc | None) = None

    #: A function used to return a URL for a given object.
    #:
    #: This is only used if :py:attr:`link` is ``True``.
    link_func: (LinkObjectFunc | None) = None

    #: Whether the column will shrink to the minimum size for the data.
    shrink: bool = False

    #: Whether the column can be sorted.
    sortable: bool = False

    @deprecate_non_keyword_only_args(RemovedInDjblets70Warning)
    def __init__(
        self,
        label: Unsettable[StrOrPromise | None] = UNSET,
        *,
        id: Unsettable[str] = UNSET,
        detailed_label: Unsettable[StrOrPromise | None] = UNSET,
        detailed_label_html: Unsettable[
            StrOrPromise | SafeString | None
        ] = UNSET,
        field_name: Unsettable[str] = UNSET,
        db_field: Unsettable[str] = UNSET,
        image_url: Unsettable[str | None] = UNSET,
        image_class: Unsettable[str | None] = UNSET,
        image_width: Unsettable[int | None] = UNSET,
        image_height: Unsettable[int | None] = UNSET,
        image_alt: Unsettable[StrOrPromise | None] = UNSET,
        shrink: Unsettable[bool] = UNSET,
        expand: Unsettable[bool] = UNSET,
        sortable: Unsettable[bool] = UNSET,
        default_sort_dir: Unsettable[int] = UNSET,
        link: Unsettable[bool] = UNSET,
        link_func: Unsettable[LinkObjectFunc | None] = UNSET,
        link_css_class: Unsettable[str | LinkCSSClassFunc | None] = UNSET,
        cell_clickable: Unsettable[bool] = UNSET,
        css_class: Unsettable[str | BuildCSSClassFunc] = UNSET,
    ) -> None:
        """Initialize the column.

        When initializing a column as part of a :py:class:`DataGrid` subclass,
        a number of options can be provided.

        Version Changed:
            5.3:
            * Any arguments not provided will now fall back to the
              corresponding attributes set on the class.

            * All arguments other than ``label`` are now keyword-only.
              This will be enforced in Djblets 7.

            * ``cell_clickable`` is deprecated and will be removed in
              Djblets 7. It's never been used.

        Args:
            id (str, optional):
                The unique ID of the column on the datagrid.

                if not provided, one will be calculated.

            label (str, optional):
                The label to show in the column header.

            detailed_label (str, optional):
                A detailed label to display in the column customization
                menu. Defaults to ``label``.

            detailed_label_html (str, optional):
                A detailed label in HTML form to display in the column
                customization menu. This takes precedence over
                ``detailed_label``.

            field_name (str, optional):
                The name of the field on the model containing the data to
                render.

            db_field (str, optional):
                The name of the database field containing the field used
                for sorting. Defaults to ``field_name``.

            image_url (str, optional):
                The URL to the image used in the header and navigation menu.
                This cannot be used with ``image_class``.

            image_class (str, optional):
                The CSS class of a spritesheet icon to use in the header
                and navigation menu. This cannot be used with ``image_url``.

            image_width (int, optional):
                The width of the image.

            image_height (int, optional):
                The height of the image.

            image_alt (str, optional):
                The alt text for the image.

            shrink (bool, optional):
                If ``True``, the column's width will be calculated to its
                minimum size.

            expand (bool, optional):
                If ``True``, the column's width will be calculated to its
                maximum size. If there are other expanded columns, they'll
                share the available width equally.

            sortable (bool, optional):
                If ``True``, the column can be sorted. This requires a
                ``db_field`` that allows for sorting.

            default_sort_dir (int, optional):
                The default sorting direction when the user activates sorting.
                Either :py:attr:`SORT_DESCENDING`
                or :py:attr:`SORT_ASCENDING`.

            link (bool, optional):
                If ``True``, the contents will be linked to the URL
                returned by ``link_func`` or
                :py:meth:`DataGrid.link_to_object`.

            link_func (callable, optional):
                Optional function that returns a URL for the link.

            link_css_class (str or callable, optional):
                The CSS class or classes to define on ``<a>`` for the link
                for the cell, if setting ``link=True``. This can be a
                function returning the classes.

            cell_clickable (bool, optional):
                Unused option to indicate a cell is clickable.

                Deprecated:
                    5.3:
                    This will be removed in Djblets 7.

            css_class (str or callable, optional):
                The CSS class or classes to define on the cell.

                This can be a function returning the classes.

        Raises:
            ValueError:
                An incorrect argument combination was provided.

                Details will be in the error message.
        """
        if cell_clickable is not UNSET:
            RemovedInDjblets70Warning.warn(
                'cell_clickable is deprecated and will be removed in '
                'Djblets 7.'
            )

        if id is not UNSET:
            self.id = id

        if field_name is not UNSET:
            self.field_name = field_name
        else:
            field_name = self.field_name

        if db_field is not UNSET:
            self.db_field = db_field
        elif not self.db_field and field_name:
            self.db_field = field_name

        if label is not UNSET:
            self.label = label
        else:
            label = self.label

        if detailed_label is not UNSET:
            self.detailed_label = detailed_label
        elif not self.detailed_label and label:
            self.detailed_label = label

        if detailed_label_html is not UNSET:
            self.detailed_label_html = detailed_label_html
        elif not self.detailed_label_html and self.detailed_label:
            self.detailed_label_html = escape(self.detailed_label)

        if image_url is not UNSET:
            self.image_url = image_url

        if image_class is not UNSET:
            self.image_class = image_class

        if self.image_class and self.image_url:
            raise ValueError(
                'image_class and image_url cannot both be set on this '
                'column.'
            )

        if image_width is not UNSET:
            self.image_width = image_width

        if image_height is not UNSET:
            self.image_height = image_height

        if image_alt is not UNSET:
            self.image_alt = image_alt

        if shrink is not UNSET:
            self.shrink = shrink

        if expand is not UNSET:
            self.expand = expand

        if sortable is not UNSET:
            self.sortable = sortable

        if default_sort_dir is not UNSET:
            self.default_sort_dir = default_sort_dir

        if link is not UNSET:
            self.link = link

        if link_func is not UNSET:
            self.link_func = link_func
        elif not self.link_func:
            self.link_func = (
                lambda state, x, y:
                state.datagrid.link_to_object(state, x, y)
            )

        if link_css_class is not UNSET:
            self.link_css_class = link_css_class

        if css_class is not UNSET:
            self.css_class = css_class

    @cached_property
    def cell_template_obj(self) -> Optional[_EngineTemplate]:
        """Return the cell template, if it exists.

        By default, this requires :py:attr:`cell_template` to be set.

        Returns:
            object:
            The template backend-specific template for the cell.
        """
        if self.cell_template:
            return get_template(self.cell_template)

        return None

    def setup_state(
        self,
        state: StatefulColumn,
    ) -> None:
        """Set up any state that may be needed for the column.

        This is called once per column per datagrid instance.

        By default, no additional state is set up. Subclasses can override
        this to set any variables they may need.

        Args:
            state (StatefulColumn):
                The state for the DataGrid instance.
        """
        pass

    def get_sort_field(
        self,
        state: StatefulColumn,
    ) -> Optional[str]:
        """Return the field used for sorting this column.

        By default, this returns :py:attr:`db_field`.

        Args:
            state (StatefulColumn):
                The state for the DataGrid instance.

        Returns:
            str:
            The field on the model used for sorting.
        """
        return self.db_field

    def get_toggle_url(
        self,
        state: StatefulColumn,
    ) -> str:
        """Return a URL to toggle this column's visibility.

        Args:
            state (StatefulColumn):
                The state for the DataGrid instance.

        Returns:
            str:
            The URL used to toggle column visibility.
        """
        datagrid = state.datagrid
        columns: List[str] = [
            column.id
            for column in datagrid.columns
        ]

        if state.active:
            try:
                columns.remove(self.id)
            except ValueError:
                pass
        else:
            columns.append(self.id)

        url_params = get_url_params_except(datagrid.request.GET,
                                           'columns')

        if url_params:
            url_params = f'{url_params}&'

        return '?%scolumns=%s' % (url_params, ','.join(columns))

    def get_header(
        self,
        state: StatefulColumn,
    ) -> str:
        """Render the header for the column.

        The column header will include the current sort indicator, if it
        belongs in the sort list. It will also be made clickable in order
        to modify the sort order appropriately, if sortable.

        Args:
            state (StatefulColumn):
                The state for the DataGrid instance.

        Returns:
            str:
            The HTML for the header.
        """
        datagrid = state.datagrid
        in_sort = False
        sort_direction = self.SORT_DESCENDING
        sort_primary = False
        sort_url = ''
        unsort_url = ''

        if self.sortable:
            sort_list = list(datagrid.sort_list or [])

            if sort_list:
                rev_column_id = f'-{self.id}'
                new_column_id = self.id
                cur_column_id = ''

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
            del sort_list[2:]

            query_args = datagrid.request.GET.copy()

            for key in ('datagrid-id', 'gridonly', 'columns'):
                query_args.pop(key, None)

            sort_query_args = query_args.copy()
            sort_query_args['sort'] = ','.join(sort_list)

            unsort_query_args = query_args.copy()
            unsort_query_args['sort'] = ','.join(sort_list[1:])

            sort_url = '?%s' % urlencode(sort_query_args)
            unsort_url = '?%s' % urlencode(unsort_query_args)

        return datagrid.column_header_template_obj.render(context={
            'column': self,
            'column_state': state,
            'in_sort': in_sort,
            'sort_ascending': sort_direction == self.SORT_ASCENDING,
            'sort_primary': sort_primary,
            'sort_url': sort_url,
            'unsort_url': unsort_url,
        })

    def collect_objects(
        self,
        state: StatefulColumn,
        object_list: Iterable[Any],
    ) -> None:
        """Iterate through the objects and builds a cache of data to display.

        This optimizes the fetching of data in the grid by grabbing all the
        IDs of related objects that will be queried for rendering, loading
        them all at once, and populating the cache.

        Args:
            state (StatefulColumn):
                The state for the DataGrid instance.

            object_list (list):
                The list of objects being rendered on the datagrid.
        """
        field_name = self.field_name
        id_field = f'{field_name}_id'
        ids: Set[Any] = set()
        model = None

        for obj in object_list:
            if not hasattr(obj, id_field):
                # This isn't the field type you're looking for.
                return

            id_value = getattr(obj, id_field)

            if id_value is None:
                continue

            ids.add(id_value)

            if not model:
                field = getattr(obj.__class__, field_name).field

                try:
                    model = field.rel.to
                except AttributeError:
                    # No idea what this is. Bail.
                    return

        if model and ids:
            for obj in model.objects.filter(pk__in=ids):
                state.data_cache[obj.pk] = obj

    def render_cell(
        self,
        state: StatefulColumn,
        obj: Any,
        render_context: _RenderContext,
    ) -> SafeString:
        """Render the table cell containing column data.

        Args:
            state (StatefulColumn):
                The state for the DataGrid instance.

            obj (object):
                The object being rendered for this row.

            render_context (dict or django.template.context.Context):
                The shared context used for cell renders.

        Returns:
            str:
            The rendered cell as HTML.
        """
        try:
            rendered_data = self.render_data(state, obj)
        except Exception as e:
            logger.exception('Error when calling render_data for DataGrid '
                             'Column %r: %s',
                             self, e)
            rendered_data = ''

        # We use empty strings instead of None just to keep cache keys small.
        url = ''
        css_class = ''
        link_css_class = ''

        if self.link:
            if self.link_func is not None:
                try:
                    url = self.link_func(state, obj, rendered_data)
                except AttributeError:
                    pass
            elif render_context:
                url = render_context.get('_datagrid_object_url')

        if self.css_class:
            if callable(self.css_class):
                css_class = self.css_class(obj)
            else:
                css_class = self.css_class

        if self.link_css_class:
            if callable(self.link_css_class):
                link_css_class = self.link_css_class(obj)
            else:
                link_css_class = self.link_css_class

        key = '%s:%s:%s:%s:%s' % (state.last, rendered_data, url, css_class,
                                  link_css_class)

        if key not in state.cell_render_cache:
            if url:
                css_class = '%s has-link' % css_class

            ctx: Dict[str, Any] = {}

            if render_context:
                ctx.update(render_context)

            ctx.update({
                'column': self,
                'column_state': state,
                'css_class': css_class.strip(),
                'link_css_class': link_css_class,
                'url': url,
                'data': mark_safe(rendered_data)
            })

            template = self.cell_template_obj

            if template is None:
                template = state.datagrid.cell_template_obj

            state.cell_render_cache[key] = template.render(ctx)

        return state.cell_render_cache[key]

    def render_data(
        self,
        state: StatefulColumn,
        obj: Any,
    ) -> str:
        """Render the column data within the cell.

        Args:
            state (StatefulColumn):
                The state for the DataGrid instance.

            obj (object):
                The object being rendered for this row.

        Returns:
            str:
            The rendered data as HTML.
        """
        field_name = self.field_name
        id_field = f'{field_name}_id'

        # Look for this directly so that we don't end up fetching the
        # data for the object.
        if id_field in obj.__dict__:
            pk = obj.__dict__[id_field]

            if pk in state.data_cache:
                return state.data_cache[pk]
            else:
                value = getattr(obj, field_name)
                state.data_cache[pk] = escape(value)
                return value
        else:
            return escape(self.get_raw_object_value(state, obj) or '')

    def to_json(
        self,
        state: StatefulColumn,
        obj: Any,
    ) -> SerializableDjangoJSONValue:
        """Return a JSON-serializable value for an object in a cell.

        Subclasses can override this to customize value extraction for JSON.

        Version Added:
            5.3

        Args:
            state (StatefulColumn):
                The state for the DataGrid instance.

            obj (object):
                The object being processed for this row.

        Returns:
            typelets.django.json.SerializableDjangoJSONValue:
            The raw value suitable for JSON serialization, or ``None`` if
            this column has no ``field_name``.
        """
        return self.get_raw_object_value(state, obj)

    def get_raw_object_value(
        self,
        state: StatefulColumn,
        obj: Any,
    ) -> Any:
        """Return the raw value for a given object in a cell.

        This is used to return a value that can be used by
        :py:meth:`render_data` and :py:meth:`to_json`.

        By default, this will use :py:attr:`field_name` as a ``.``-separated
        path of attributes. Any attributes mapping to a function will be
        called, returning the value for the next part in the path.

        Subclasses can override this to customize the logic for returning
        the object's value.

        Version Added:
            5.3

        Args:
            state (StatefulColumn):
                The state for the DataGrid instance.

            obj (object):
                The object being processed for this row.

        Returns:
            object:
            The resulting value, or ``None`` if the field was not found
            on the object.
        """
        field_name = self.field_name

        if not field_name:
            return None

        value = obj

        for field_name in field_name.split('.'):
            if field_name:
                value = getattr(value, field_name)

                if callable(value):
                    value = value()

        return value

    def augment_queryset_for_filter(
        self,
        state: StatefulColumn,
        queryset: QuerySet,
        *,
        request: HttpRequest,
        **kwargs,
    ) -> QuerySet:
        """Augment a queryset for filtering purposes.

        Subclasses can override this to add filters to the queryset to limit
        the results returned for display and for pagination.

        This must not be used to load additional data for display, or to
        pre-fetch/select-related any columns, unless required as part of the
        filter. Instead, override :py:meth:`augment_queryset_for_data`.

        Version Added:
            3.4

        Args:
            state (StatefulColumn):
                The state for the DataGrid instance.

            queryset (django.db.models.query.QuerySet):
                The queryset to augment.

            request (django.http.HttpRequest):
                The HTTP request from the client.

            **kwargs (dict):
                Additional keyword arguments for future expansion.

        Returns:
            django.db.models.query.QuerySet:
            The resulting augmented QuerySet.
        """
        return queryset

    def augment_queryset_for_data(
        self,
        state: StatefulColumn,
        queryset: QuerySet,
        *,
        request: HttpRequest,
        **kwargs,
    ) -> QuerySet:
        """Augment a queryset for data-rendering purposes.

        Subclasses can override this to query for additional data used for
        displaying this column.

        This must not be used to filter querysets. Instead, override
        :py:meth:`augment_queryset_for_filter`.

        Version Added:
            3.4

        Args:
            state (StatefulColumn):
                The state for the DataGrid instance.

            queryset (django.db.models.query.QuerySet):
                The queryset to augment.

            request (django.http.HttpRequest):
                The HTTP request from the client.

            **kwargs (dict):
                Additional keyword arguments for future expansion.

        Returns:
            django.db.models.query.QuerySet:
            The resulting augmented QuerySet.
        """
        return queryset

    def augment_queryset(
        self,
        state: StatefulColumn,
        queryset: QuerySet,
    ) -> QuerySet:
        """Augment a queryset with new queries.

        Subclasses can override this to extend the queryset to provide
        additional information, usually using queryset.extra(). This must
        return a queryset based on the original queryset.

        This should not restrict the query in any way, or the datagrid may
        not operate properly. It must only add additional data to the
        queryset.

        Args:
            state (StatefulColumn):
                The state for the DataGrid instance.

            queryset (django.db.models.QuerySet):
                The queryset to augment.

        Returns:
            django.db.models.QuerySet:
            The resulting QuerySet.
        """
        return queryset


class StatefulColumn:
    """A stateful wrapper for a Column instance.

    Columns must be stateless, as they are shared across all instances of
    a particular DataGrid. However, some state is needed for columns, such
    as their widths or active status.

    StatefulColumn wraps a :py:class:`Column` instance and provides state
    storage, and also provides a convenient way to call methods on a Column and
    pass the state.

    Attributes owned by the Column can be accessed directly through the
    StatefulColumn.

    Likewise, any functions owned by the Column can be accessed as well.
    The function will be invoked with this StatefulColumn as the first
    parameter passed.
    """

    ######################
    # Instance variables #
    ######################

    #: Whether this column is actively used in the datagrid.
    #:
    #: Type:
    #:     bool
    active: bool

    #: A cache of render keys to rendered HTML for the cell.
    #:
    #: Type:
    #:     dict
    cell_render_cache: Dict[str, SafeString]

    #: The column instance that this state is associated with.
    #:
    #: Type:
    #:     Column
    column: Column

    #: A cache of object IDs to objects for this column.
    #:
    #: Type:
    #:     dict
    data_cache: Dict[Any, Any]

    #: The datagrid that owns this column state.
    #:
    #: Type:
    #:     djblets.datagrid.grids.DataGrid
    datagrid: DataGrid

    #: Extra state data used by subclasses.
    #:
    #: Version Added:
    #:     5.3
    extra_data: dict[str, Any]

    #: Whether this is the last column in the datagrid.
    #:
    #: Type:
    #:     bool
    last: bool

    #: The computed reserved width of the column, as a percentage.
    #:
    #: Type:
    #:     float
    width: float

    def __init__(
        self,
        datagrid: DataGrid,
        column: Column,
    ) -> None:
        """Initialize the column state.

        Args:
            datagrid (DataGrid):
                The DataGrid instance owning this column state.

            column (Column):
                The column instance this state is associated with.
        """
        self.datagrid = datagrid
        self.column = column
        self.active = False
        self.last = False
        self.width = 0
        self.data_cache = {}
        self.cell_render_cache = {}
        self.extra_data = {}

        try:
            column.setup_state(self)
        except Exception as e:
            logger.exception('Error when calling setup_state for DataGrid '
                             'Column %r: %s',
                             self.column, e)

    @property
    def toggle_url(self) -> str:
        """The visibility toggle URL of the column.

        This is a convenience used by templates to call
        :py:meth:`Column.get_toggle_url` with the current state.

        Type:
            str
        """
        return self.column.get_toggle_url(self)

    @property
    def header(self) -> str:
        """The header of the column.

        This is a convenience used by templates to call
        :py:meth:`Column.get_header` with the current state.

        Type:
            str
        """
        return self.column.get_header(self)

    def __getattr__(
        self,
        name: str,
    ) -> Any:
        """Returns an attribute from the parent Column.

        This is called when accessing an attribute not found directly on
        StatefulColumn. The attribute will be fetched from the Column
        (if it exists there).

        In the case of accessing a function, a wrapper will be returned
        that will automatically pass this StatefulColumn instance as the
        first parameter.

        Args:
            name (str):
                The attribute to fetch from the column.

        Returns:
            object:
            The attribute value from the column.
        """
        result = getattr(self.column, name)

        if callable(result):
            return lambda *args, **kwargs: result(self, *args, **kwargs)

        return result


class CheckboxColumn(Column):
    """A column that renders a checkbox.

    The :py:meth:`is_selectable` and :py:meth:`is_selected` functions can be
    overridden to control whether a checkbox is displayed in a row and whether
    that checkbox is initially checked.

    The checkboxes have a ``data-object-id`` attribute that contains the ID of
    the object that row represents. This allows the JavaScript code to
    determine which rows have been checked, and operate on that
    accordingly.

    The checkboxes also have a ``data-checkbox-name`` attribute that
    contains the value passed in to the ``checkbox_name`` parameter of its
    constructor.

    Version Changed:
        5.3:
        Options for the column can now be set as class attributes when
        subclassing.
    """

    # Overrides for the parent class.
    cell_template: (str | None) = 'datagrid/cell_no_link.html'
    detailed_label: (StrOrPromise | None) = _('Select Rows')
    shrink = True

    ##########################################
    # Class customization/instance variables #
    ##########################################

    #: The name to set for the checkbox in the HTML.
    #:
    #: This is set in ``data-checkbox-name``.
    checkbox_name: str = 'select'

    #: Whether a checkbox will be used for the column header.
    show_checkbox_header: bool = True

    # TODO: Remove shrink and detailed_label from the args list in Djblets 7.
    @deprecate_non_keyword_only_args(RemovedInDjblets70Warning)
    def __init__(
        self,
        label: Unsettable[StrOrPromise | None] = UNSET,
        *args,
        checkbox_name: Unsettable[str] = UNSET,
        shrink: Unsettable[bool] = UNSET,
        show_checkbox_header: Unsettable[bool] = UNSET,
        detailed_label: Unsettable[StrOrPromise | None] = UNSET,
        **kwargs,
    ) -> None:
        """Initialize the column.

        Version Changed:
            5.3:
            * Any arguments not provided will now fall back to the
              corresponding attributes set on the class.

            * All arguments other than ``label`` are now keyword-only.
              This will be enforced in Djblets 7.

        Args:
            label (str, optional):
                The label to show in the column header.

            *args (tuple):
                Additional positional arguments for the column.

            checkbox_name (str, optional):
                The name set in ``data-checkbox-name``.

            shrink (bool, optional):
                If ``True``, the column's width will be calculated to its
                minimum size.

            show_checkbox_header (bool, optional):
                If ``True``, a checkbox will be used for the column header.

            detailed_label (str, optional):
                The detailed label to show for the column.

            **kwargs (dict):
                Additional keyword arguments for the column.
        """
        if show_checkbox_header is not UNSET:
            self.show_checkbox_header = show_checkbox_header

        if checkbox_name is not UNSET:
            self.checkbox_name = checkbox_name

        if label is UNSET and not self.label:
            self.label = format_html(
                '<input class="datagrid-header-checkbox"'
                ' type="checkbox" data-checkbox-name="{}">',
                self.checkbox_name,
            )

        if not self.detailed_label_html:
            if detailed_label is UNSET:
                detailed_label = self.detailed_label

            self.detailed_label_html = format_html(
                '<input type="checkbox"> {}',
                detailed_label,
            )

        super().__init__(
            label,
            *args,
            shrink=shrink,
            detailed_label=detailed_label,
            **kwargs,
        )

    def render_data(
        self,
        state: StatefulColumn,
        obj: Any,
    ) -> str:
        """Render the column data within the cell.

        Args:
            state (StatefulColumn):
                The state for the DataGrid instance.

            obj (object):
                The object being rendered for this row.

        Returns:
            str:
            The rendered data as HTML.
        """
        if self.is_selectable(state, obj):
            checked = ''

            if self.is_selected(state, obj):
                checked = mark_safe('checked="true"')

            return format_html('<input type="checkbox" data-object-id="{0}" '
                               'data-checkbox-name="{1}" {2} />',
                               getattr(obj, 'pk', None),
                               self.checkbox_name,
                               checked)
        else:
            return ''

    def is_selectable(
        self,
        state: StatefulColumn,
        obj: Any,
    ) -> bool:
        """Return whether an object can be selected.

        By default, this always returns ``True``. Subclasses can override this
        to disable rendering a checkbox for a given object.

        Args:
            state (StatefulColumn):
                The state for the DataGrid instance.

            obj (object):
                The object being rendered for this row.

        Returns:
            bool:
            ``True`` if a checkbox will be rendered and can be selected.
            ``False`` if no checkbox will be rendered.
        """
        return True

    def is_selected(
        self,
        state: StatefulColumn,
        obj: Any,
    ) -> bool:
        """Return whether an object is selected by default.

        By default, this returns ``False``. Subclasses can override this to
        enable a checkbox by default for a given object.

        Args:
            state (StatefulColumn):
                The state for the DataGrid instance.

            obj (object):
                The object being rendered for this row.

        Returns:
            bool:
            ``True`` if the checkbox will be selected by default.
            ``False`` if it will not.
        """
        return False

    def to_json(
        self,
        state: StatefulColumn,
        obj: Any,
    ) -> SerializableDjangoJSONValue:
        """Return a JSON-serializable value for an object in a cell.

        Version Added:
            5.3

        Args:
            state (StatefulColumn):
                The state for the DataGrid instance.

            obj (object):
                The object being processed for this row.

        Returns:
            typelets.django.json.SerializableDjangoJSONValue:
            ``True`` if the checkbox is selected, ``False`` if not
            selectable or not selected.
        """
        return (self.is_selectable(state, obj) and
                self.is_selected(state, obj))


class DateTimeColumn(Column):
    """A column that renders a date or time.

    Version Changed:
        5.3:
        Options for the column can now be set as class attributes when
        subclassing.
    """

    sortable: bool = True

    ##########################################
    # Class customization/instance variables #
    ##########################################

    #: The format used to show the date/time.
    #:
    #: This must be a valid :py:func:`~datetime.date.strftime`
    #: format string. If not provided, Django's default will be used.
    format: (str | None) = None

    #: The timezone used to normalize the date/time to.
    timezone: Any = pytz.utc

    # TODO: Remove label and sortable from the args list in Djblets 7.
    @deprecate_non_keyword_only_args(RemovedInDjblets70Warning)
    def __init__(
        self,
        label: Unsettable[StrOrPromise | None] = UNSET,
        *args,
        format: Unsettable[str | None] = UNSET,
        sortable: Unsettable[bool] = UNSET,
        timezone: Unsettable[Any] = UNSET,
        **kwargs,
    ) -> None:
        """Initialize the column.

        Version Changed:
            5.3:
            * Any arguments not provided will now fall back to the
              corresponding attributes set on the class.

            * All arguments other than ``label`` are now keyword-only.
              This will be enforced in Djblets 7.

        Args:
            label (str, optional):
                The label to show in the column header.

            format (str, optional):
                The format used to show the date/time.

                This must be a valid :py:func:`~datetime.date.strftime`
                format string. If not provided, Django's default will be used.

            sortable (bool, optional):
                Whether the field should be sortable.

                This is enabled by default.

            timezone (object, optional):
                The timezone used to normalize the date/time to.

            *args (tuple):
                Additional positional arguments for the column.

            **kwargs (dict):
                Additional keyword arguments for the column.
        """
        super().__init__(
            label,
            sortable=sortable,
            *args, **kwargs,
        )

        if format is not UNSET:
            self.format = format

        if timezone is not UNSET:
            self.timezone = timezone

    def render_data(
        self,
        state: StatefulColumn,
        obj: Any,
    ) -> str:
        """Render the column data within the cell.

        Args:
            state (StatefulColumn):
                The state for the DataGrid instance.

            obj (object):
                The object being rendered for this row.

        Returns:
            str:
            The rendered data as HTML.
        """
        return date(self.get_raw_object_value(state, obj), self.format)

    def to_json(
        self,
        state: StatefulColumn,
        obj: Any,
    ) -> SerializableDjangoJSONValue:
        """Return a JSON-serializable value for an object in a cell.

        Version Added:
            5.3

        Args:
            state (StatefulColumn):
                The state for the DataGrid instance.

            obj (object):
                The object being processed for this row.

        Returns:
            typelets.django.json.SerializableDjangoJSONValue:
            The datetime value as an ISO-formatted string, or ``None`` if
            not present.
        """
        timestamp = self.get_raw_object_value(state, obj)

        if timestamp is None:
            return None

        return timestamp.isoformat()

    def get_raw_object_value(
        self,
        state: StatefulColumn,
        obj: Any,
    ) -> datetime | None:
        """Return the raw value for a given object in a cell.

        This will return a normalized :py:class:`datetime.datetime` for the
        object in the cell.

        Version Added:
            5.3

        Args:
            state (StatefulColumn):
                The state for the DataGrid instance.

            obj (object):
                The object being processed for this row.

        Returns:
            datetime.datetime:
            The resulting value.
        """
        result = getattr(obj, self.field_name, None)

        if result is None:
            return None

        # If the datetime object is tz aware, convert it to local time.
        if settings.USE_TZ:
            result = (
                pytz.utc.normalize(result)
                .astimezone(self.timezone)
            )

        return result


class DateTimeSinceColumn(Column):
    """A column that renders a date or time relative to now.

    Version Changed:
        5.3:
        Options for the column can now be set as class attributes when
        subclassing.
    """

    sortable: bool = True

    # TODO: Remove this function in Djblets 7.
    @deprecate_non_keyword_only_args(RemovedInDjblets70Warning)
    def __init__(
        self,
        label: Unsettable[StrOrPromise | None] = UNSET,
        *args,
        sortable: Unsettable[bool] = UNSET,
        **kwargs,
    ) -> None:
        """Initialize the column.

        Version Changed:
            5.3:
            * Any arguments not provided will now fall back to the
              corresponding attributes set on the class.

            * All arguments other than ``label`` are now keyword-only.
              This will be enforced in Djblets 7.

        Args:
            label (str, optional):
                The label to show in the column header.

            *args (tuple):
                Additional positional arguments for the column.

            sortable (bool, optional):
                Whether the field should be sortable.

                This is enabled by default.

            **kwargs (dict):
                Additional keyword arguments for the column.
        """
        super().__init__(label,
                         *args,
                         sortable=sortable,
                         **kwargs)

    def render_data(
        self,
        state: StatefulColumn,
        obj: Any,
    ) -> str:
        """Render the column data within the cell.

        Args:
            state (StatefulColumn):
                The state for the DataGrid instance.

            obj (object):
                The object being rendered for this row.

        Returns:
            str:
            The rendered data as HTML.
        """
        return _('%s ago') % timesince(self.get_raw_object_value(state, obj))

    def to_json(
        self,
        state: StatefulColumn,
        obj: Any,
    ) -> SerializableDjangoJSONValue:
        """Return a JSON-serializable value for an object in a cell.

        Unlike :py:meth:`render_data`, which returns a human-readable
        "X ago" string, this returns the actual datetime value as an
        ISO-formatted string suitable for JSON serialization.

        Version Added:
            5.3

        Args:
            state (StatefulColumn):
                The state for the DataGrid instance.

            obj (object):
                The object being processed for this row.

        Returns:
            typelets.django.json.SerializableDjangoJSONValue:
            The datetime value as an ISO-formatted string, or ``None`` if
            not present.
        """
        timestamp = self.get_raw_object_value(state, obj)

        if timestamp is None:
            return None

        return timestamp.isoformat()


class DataGrid:
    """A paginated table of data based on queries from a database.

    A datagriad represents a list of objects, sorted and organized by
    columns. The sort order and column lists can be customized. allowing
    users to view this data however they prefer.

    This is meant to be subclassed for specific uses. The subclasses are
    responsible for defining one or more column types. It can also set
    one or more of the following optional variables:
    """

    _columns = None

    #: Whether to allow search indexing on the page.
    #:
    #: Version Added:
    #:     5.3
    allow_search_indexing: bool = True

    #: The list of default columns for this datagrid.
    #:
    #: Type:
    #:     list of str
    default_columns: List[str] = []

    #: The default sort list for columns.
    #:
    #: Type:
    #:     list of str
    default_sort: List[str] = []

    ######################
    # Instance variables #
    ######################

    #: The template used to render a cell of data.
    #:
    #: The default is :file:`datagrid/cell.html`.
    #:
    #: Type:
    #:     str
    cell_template: str

    #: A mapping of columns to stateful columns.
    #:
    #: Type:
    #:     dict
    column_map: Dict[Column, StatefulColumn]

    #: A list of all stateful columns on this datagrid.
    #:
    #: Type:
    #:     list of StatefulColumn
    columns: List[StatefulColumn]

    #: The template used to render each column header.
    #:
    #: The default is :file:`datagrid/column_header.html`.
    #:
    #: Type:
    #:     str
    custom_header_template: str

    #: Extra context to render in each template.
    #:
    #: Type:
    #:     dict
    extra_context: _RenderContext

    #: The ID of this datagrid.
    #:
    #: Type:
    #:     str
    id: str

    #: A list of IDs for objects on the current page of results.
    #:
    #: Type:
    #:     list of object
    id_list: List[Any]

    #: The template used to render the list view.
    #:
    #: The default is :file:`datagrid/listview.html`.
    #:
    #: Type:
    #:     str
    listview_template: str

    #: Whether or not to optimize queries when using multiple sorts.
    #:
    #: This can offer a speed improvement, but may need to be turned off for
    #: more advanced querysets (such as when using :py:meth:`QuerySet.extra()
    #: <django.db.models.query.QuerySet.extra>`).
    #:
    #: The default is ``True``.
    #:
    #: Type:
    #:     bool
    optimize_sorts: bool

    #: The current page of results.
    #:
    #: Type:
    #:     django.core.paginator.Page
    page: Optional[Page]

    #: The 1-based page number to display.
    #:
    #: If this is not explicitly set, the ``?page=`` query argument will be
    #: used. Otherwise, this defaults to 1.
    #:
    #: Type:
    #:     int
    page_num: int

    #: The paginator managing pages of results.
    #:
    #: Type:
    #:     DataGridPaginator
    paginator: Optional[DataGridPaginator]

    #: The template used for the paginator.
    #:
    #: This defaults to :file:`datagrid/paginator.html`.
    #:
    #: Type:
    #:     str
    paginator_template: str

    #: The number of items to show on each page of the grid.
    #:
    #: This defaults to 50.
    #:
    #: Type:
    #:     int
    paginate_by: int

    #: The number of orphan items to collect on the last page of results.
    #:
    #: If the last page contains this number of objects or fewer, it will be
    #: rolled up into the previous page.
    #:
    #: Type:
    #:     int
    paginate_orphans: int

    #: The profile field storing the column list for the datagrid.
    #:
    #: Type:
    #:     str
    profile_columns_field: Optional[str]

    #: The profile field storing the sort order for the datagrid.
    #:
    #: Type:
    #:     str
    profile_sort_field: Optional[str]

    #: A copy of all the row data.
    #:
    #: Type:
    #:     list of _DataGridRow
    rows: List[_DataGridRow]

    #: The sort priority list for the results.
    #:
    #: Type:
    #:     list of str
    sort_list: Optional[List[str]]

    #: Query arguments to include when fetching datagrid contents.
    #:
    #: Type:
    #:     List[str]
    special_query_args: List[str]

    #: Whether state has been loaded for the datagrid.
    #:
    #: Type:
    #:     bool
    state_loaded: bool

    #: The title of the grid.
    #:
    #: Type:
    #:     str
    title: StrOrPromise

    #: Whether to use distinct querysets.
    #:
    #: This is currently enabled by default. This default may be changed in
    #: a future release. Callers should explicitly set this to the value
    #: they want to use.
    #:
    #: Version Added:
    #:     3.4
    #:
    #: Type:
    #:     bool
    use_distinct: bool

    #: Any explicit column names provided during initialization.
    #:
    #: Version Added:
    #:     5.3
    _column_names: Unsettable[Sequence[str] | None]

    #: The model for the objects in the datagrid.
    #:
    #: Type:
    #:     type
    _model: Optional[Type[Model]]

    #: Any explicit column sort order provided during initialization.
    #:
    #: Version Added:
    #:     5.3
    _sort_column_names: Unsettable[Sequence[str] | None]

    @classmethod
    def add_column(
        cls,
        column: Column,
    ) -> None:
        """Add a new column for this datagrid.

        This can be used to add columns to a DataGrid subclass after
        the subclass has already been defined.

        The column added must have a unique ID already set.

        Args:
            column (Column):
                The column to add.

        Raises:
            KeyError:
                The column is missing an ID.
        """
        cls._populate_columns()

        if not column.id:
            raise KeyError(
                'Custom datagrid columns must have a unique id attribute.')

        if column.id in _column_registry[cls]:
            raise KeyError('"%s" is already a registered column for %s'
                           % (column.id, cls.__name__))

        _column_registry[cls][column.id] = column

    @classmethod
    def remove_column(
        cls,
        column: Column,
    ) -> None:
        """Remove a column from this datagrid.

        This can be used to remove columns previously added through
        :py:meth:`add_column`.

        Args:
            column (Column):
                The column to remove.

        Raises:
            KeyError:
                The column could not be found.
        """
        cls._populate_columns()

        try:
            del _column_registry[cls][column.id]
        except KeyError:
            raise KeyError('"%s" is not a registered column for %s'
                           % (column.id, cls.__name__))

    @classmethod
    def get_column(
        cls,
        column_id: str,
    ) -> Optional[Column]:
        """Return the column with the given ID.

        If not found, this will return None.

        Args:
            column_id (str):
                The ID of the column to return.

        Returns:
            Column:
            The resulting column at the given index.
        """
        cls._populate_columns()

        return _column_registry[cls].get(column_id)

    @classmethod
    def get_columns(cls) -> Sequence[Column]:
        """Return the list of registered columns for this datagrid.

        Returns:
            list of Column:
            The list of columns registered on this datagrid.
        """
        cls._populate_columns()

        return list(_column_registry[cls].values())

    @classmethod
    def _populate_columns(cls) -> None:
        """Populate the default list of columns for the datagrid.

        The default list contains all columns added in the class definition.
        """
        if cls not in _column_registry:
            _column_registry[cls] = {}

            for key in dir(cls):
                column = getattr(cls, key)

                if isinstance(column, Column):
                    column.id = key

                    if not column.field_name:
                        column.field_name = column.id

                    if not column.db_field:
                        column.db_field = column.field_name

                    cls.add_column(column)

    @deprecate_non_keyword_only_args(RemovedInDjblets70Warning)
    def __init__(
        self,
        *,
        request: HttpRequest,
        queryset: (QuerySet | None) = None,
        title: str = '',
        extra_context: (_RenderContext | None) = None,
        optimize_sorts: bool = True,
        model: (type[Model] | None) = None,
        use_distinct: bool = True,
        columns: Unsettable[Sequence[str] | None] = UNSET,
        sort: Unsettable[Sequence[str] | None] = UNSET,
    ) -> None:
        """Initialize the datagrid.

        Version Changed:
            5.3:
            * Added ``columns`` and ``sort`` arguments.
            * All arguments are now keyword-only. Positional arguments are
              deprecated and will no longer be supported in Djblets 7.

        Version Changed:
            3.4:
            Added the ``use_distinct`` argument.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            queryset (django.db.models.QuerySet, optional):
                A QuerySet returning the objects to render in the grid.

            title (str, optional):
                The displayed title of the datagrid.

            extra_context (dict or django.template.Context, optional):
                Extra context variables to render on the datagrid template.

            optimize_sorts (bool, optional):
                If ``True``, sorting will be optimized, reducing the
                complexity of the queries. This is the default.

            model (type, optional):
                The model for the objects in the datagrid. Defaults to the
                model associated with ``queryset``.

            use_distinct (bool, optional):
                Whether to use distinct querysets.

                This is currently enabled by default. This default may be
                changed in a future release. Callers should explicitly
                set this to the value they want to use.

                Version Added:
                    3.4

            columns (list of str, optional):
                An explicit list of column names to show for the datagrid.

                If specified, this will take precedence over any provided
                in an HTTP request or from a user profile, and will not be
                saved in the profile.

                Version Added:
                    5.3

            sort (list of str, optional):
                An explicit column sort order to use for the datagrid.

                If specified, this will take precedence over any provided
                in an HTTP request or from a user profile, and will not be
                saved in the profile.

                Version Added:
                    5.3
        """
        self.request = request
        self.queryset = queryset
        self.rows = []
        self.columns = []
        self.column_map = {}
        self.id_list = []
        self.paginator = None
        self.page = None
        self.sort_list = None
        self.state_loaded = False
        self.page_num = 0
        self.extra_context = dict(extra_context or {})
        self.optimize_sorts = optimize_sorts
        self.use_distinct = use_distinct
        self.special_query_args = []
        self._model = model
        self._column_names = columns
        self._sort_column_names = sort
        self.default_sort = []

        datagrid_count = getattr(request, 'datagrid_count', 0)
        self.id = f'datagrid-{datagrid_count}'
        setattr(request, 'datagrid_count', datagrid_count + 1)

        # Customizable variables
        self.title = title
        self.profile_sort_field = None
        self.profile_columns_field = None
        self.paginate_by = 50
        self.paginate_orphans = 3
        self.listview_template = 'datagrid/listview.html'
        self.column_header_template = 'datagrid/column_header.html'
        self.cell_template = 'datagrid/cell.html'
        self.paginator_template = 'datagrid/paginator.html'

    @cached_property
    def cell_template_obj(self) -> _EngineTemplate:
        """The rendered template used for cells on this datagrid.

        This will only be generated once, and reused for all cells.

        Type:
            object
        """
        obj = get_template(self.cell_template)

        if not obj:
            logger.error('Unable to load template "%s" for datagrid '
                         'cell. This may be an installation issue.',
                         self.cell_template,
                         extra={'request': self.request})

        return obj

    @cached_property
    def column_header_template_obj(self) -> _EngineTemplate:
        """The rendered template used for column headers on this datagrid.

        This will only be generated once, and reused for all headers.

        Type:
            object
        """
        obj = get_template(self.column_header_template)

        if not obj:
            logger.error('Unable to load template "%s" for datagrid '
                         'column headers. This may be an installation '
                         'issue.',
                         self.column_header_template,
                         extra={'request': self.request})

        return obj

    @property
    def all_columns(self) -> Sequence[StatefulColumn]:
        """All columns in the datagrid, sorted by label.

        Type:
            list of StatefulColumn
        """
        return [
            self.get_stateful_column(column)
            for column in sorted(self.get_columns(),
                                 key=lambda x: str(x.detailed_label))
        ]

    @property
    def model(self) -> Optional[Type[Model]]:
        """The model representing the objects shown in the grid.

        Type:
            django.db.models.Model
        """
        if self._model is None and self.queryset is not None:
            return self.queryset.model

        return self._model

    @cached_property
    def meta_tags_html(self) -> SafeString:
        """The meta tags to include on the datagrid page.

        This will set the canonical URL for the page (which will exclude
        view customization options like ``columns`` and ``sort``), and
        disable search indexing if :py:attr:`allow_search_indexing` is
        ``False``.

        Version Added:
            5.3

        Type:
            django.utils.safestring.SafeString
        """
        tags: list[SafeString] = [
            format_html('<link rel="canonical" href="{}">',
                        self.get_canonical_url()),
        ]

        if not self.allow_search_indexing:
            tags.append(mark_safe(
                '<meta name="robots" content="nofollow,noindex">'
            ))

        return mark_safe('\n'.join(tags))

    def get_canonical_url(self) -> str:
        """Return the canonical URL for the current datagrid page.

        By default, the canonical URL excludes the following:

        * Default view customization query string options (``columns``,
          ``datagrid-id``, ``gridonly``, ``sort``).

        * ``page``, if the page number is 1.

        The result must always be an absolute URL.

        Version Added:
            5.3

        Returns:
            str:
            The canonical URL for the current datagrid page.
        """
        request = self.request
        url = request.path
        exclude = ['columns', 'datagrid-id', 'gridonly', 'sort']

        if request.GET.get('page') == '1':
            exclude.append('page')

        url_params = get_url_params_except(request.GET, *exclude)

        if url_params:
            url += f'?{url_params}'

        return request.build_absolute_uri(url)

    def get_stateful_column(
        self,
        column: Column,
    ) -> StatefulColumn:
        """Return a StatefulColumn for the given Column instance.

        If one has already been created, it will be returned.

        Args:
            column (Column):
                The column associated with the stateful column.

        Returns:
            StatefulColumn:
            The column state associated with the column.
        """
        if column not in self.column_map:
            self.column_map[column] = StatefulColumn(self, column)

        return self.column_map[column]

    def load_state(
        self,
        render_context: (_RenderContext | None) = None,
    ) -> None:
        """Load the state of the datagrid.

        This will retrieve the user-specified or previously stored
        sorting order and columns list, as well as any state a subclass
        may need.

        Args:
            render_context (dict or django.template.Context, optional):
                Common template variable context to render on the datagrid.
        """
        if self.state_loaded:
            return

        request = self.request

        profile_sort_list: (str | None) = None
        profile_columns_list: (str | None) = None
        profile: (Model | None) = None
        profile_dirty_fields: list[str] = []
        profile_columns_field: (str | None) = None
        profile_sort_field: (str | None) = None

        # Get the saved settings for this grid in the profile. These will
        # work as defaults and allow us to determine if we need to save
        # the profile.
        if (request.user.is_authenticated and
            (profile := self.get_user_profile())):
            # We have a profile we can load defaults from, if needed.
            profile_sort_field = self.profile_sort_field
            profile_columns_field = self.profile_columns_field

            if profile_sort_field:
                profile_sort_list = getattr(profile, profile_sort_field, None)

            if profile_columns_field:
                profile_columns_list = getattr(profile, profile_columns_field,
                                               None)

        profile_can_save_columns: bool = profile_columns_field is not None
        profile_can_save_sort: bool = profile_sort_field is not None

        # Figure out the columns we're going to display.
        column_names = self._column_names

        if column_names is UNSET:
            temp_column_names = (
                request.GET.get('columns', profile_columns_list) or
                ''
            )

            if isinstance(temp_column_names, str):
                column_names = temp_column_names.split(',')
            elif isinstance(temp_column_names, list):
                column_names = temp_column_names
            else:
                column_names = []
        else:
            # The caller provided a custom columns list for this instance,
            # so don't save it back to the profile.
            profile_can_save_columns = False

            if column_names is None:
                column_names = []

        # Try to load the columns. If the resulting list is empty (due to
        # an empty list of column names, or missing columns), we'll load
        # from defaults.
        columns: list[Column | None] = list(filter(None, [
            self.get_column(column_name)
            for column_name in column_names
        ]))

        if not columns:
            # No columns could be loaded. Fall back on defaults.
            column_names = self.default_columns
            columns = [
                self.get_column(column_name)
                for column_name in column_names
            ]

        # Create the stateful columns and begin separating into expanded
        # and normal columns.
        #
        # We're also going to calculate the column widths based on the
        # shrink and expand values.
        stateful_columns = self.columns
        expand_columns: list[StatefulColumn] = []
        normal_columns: list[StatefulColumn] = []

        for column_def in columns:
            if column_def is None:
                continue

            stateful_column = self.get_stateful_column(column_def)
            stateful_columns.append(stateful_column)
            stateful_column.active = True

            if stateful_column.expand:
                # This column is requesting all remaining space. Save it for
                # later so we can tell how much to give it. Each expanded
                # column will count as two normal columns when calculating
                # the normal sized columns.
                expand_columns.append(stateful_column)
            elif stateful_column.shrink:
                # Make this as small as possible.
                stateful_column.width = 0
            else:
                # We'll divide the column widths equally after we've built
                # up the lists of expanded and normal sized columns.
                normal_columns.append(stateful_column)

        stateful_columns[-1].last = True

        # Try to figure out the column widths for each column.
        # We'll start with the normal sized columns.
        total_pct = 100.0

        # Each expanded column counts as two normal columns.
        normal_column_width = total_pct / (len(stateful_columns) +
                                           len(expand_columns))

        for stateful_column in normal_columns:
            stateful_column.width = normal_column_width
            total_pct -= normal_column_width

        if len(expand_columns) > 0:
            expanded_column_width = total_pct / len(expand_columns)
        else:
            expanded_column_width = 0

        for stateful_column in expand_columns:
            stateful_column.width = expanded_column_width

        # Now get the sorting order for the columns.
        sort_column_names = self._sort_column_names

        if sort_column_names is UNSET:
            temp_sort_column_names = request.GET.get('sort', profile_sort_list)

            if isinstance(temp_sort_column_names, str):
                sort_column_names = temp_sort_column_names.split(',')
            elif isinstance(temp_sort_column_names, list):
                sort_column_names = temp_sort_column_names
            else:
                sort_column_names = []
        else:
            # The caller provided a custom sort list for this instance,
            # so don't save it back to the profile.
            profile_can_save_sort = False

            if sort_column_names is None:
                sort_column_names = []

        sort_list: list[str] = []

        # If there are columns names to sort, filter out any that aren't
        # sortable or can't be found.
        for sort_item in sort_column_names:
            if not sort_item:
                continue

            if sort_item[0] == '-':
                base_sort_item = sort_item[1:]
            else:
                base_sort_item = sort_item

            column = self.get_column(base_sort_item)

            if column and column.sortable:
                sort_list.append(sort_item)

        if not sort_list:
            # No sorted columns were found. Fall back on defaults.
            sort_list = self.default_sort

        self.sort_list = sort_list

        # A subclass might have some work to do for loading and saving
        # as well.
        load_state_result = self.load_extra_state(profile)

        assert isinstance(load_state_result, list)
        profile_dirty_fields += load_state_result

        # Now that we have all that, figure out if we need to save new
        # settings back to the profile.
        #
        # We'll only save if the caller didn't pass in custom columns or
        # sort to the constructor.
        if profile:
            if profile_can_save_columns:
                stored_column_names = ','.join(column_names)

                if stored_column_names != profile_columns_list:
                    assert profile_columns_field is not None

                    setattr(profile, profile_columns_field,
                            stored_column_names)
                    profile_dirty_fields.append(profile_columns_field)

            if profile_can_save_sort:
                stored_sort = ','.join(sort_list)

                if stored_sort != profile_sort_list:
                    assert profile_sort_field is not None

                    setattr(profile, profile_sort_field, stored_sort)
                    profile_dirty_fields.append(profile_sort_field)

            if profile_dirty_fields:
                profile.save(update_fields=profile_dirty_fields)

        self.state_loaded = True

        # Fetch the list of objects and have it ready.
        self.precompute_objects(render_context)

    def get_user_profile(self) -> Optional[Model]:
        """Return the object, if any, to use for the user profile state.

        Returns:
            django.db.models.Model:
            The object, if any, used to store and retrieve persistent
            profile state for the datagrid.
        """
        if hasattr(self.request.user, 'get_profile'):
            try:
                return self.request.user.get_profile()  # type: ignore
            except ObjectDoesNotExist:
                pass

        return None

    def load_extra_state(
        self,
        profile: Optional[Model],
    ) -> list[str]:
        """Load any extra state needed for this grid.

        This is used by subclasses that may have additional data to load
        and save.

        Version Changed:
            5.3:
            This must now return a list of strings, not a bool.

        Version Changed:
            3.0:
            This should now return a list of field names to save in
            ``profile``. Any other result is deprecated and will no longer be
            supported in Djblets 4.0.

        Args:
            profile (django.db.models.Model):
                The profile model instance to load from, if any.

        Returns:
            list of str:
            A list of field names on ``profile`` that have been modified and
            should be saved.
        """
        return []

    def precompute_objects(
        self,
        render_context: Optional[_RenderContext] = None,
    ) -> None:
        """Pre-compute all objects used to render the datagrid.

        This builds the queryset and stores the list of objects for use in
        rendering the datagrid. It takes into consideration sorting,
        the current page, and augmented queries from columns.

        Args:
            render_context (dict or django.template.Context):
                The common template variable context to render on the datagrid,
                provided in the constructor.
        """
        assert self.sort_list is not None

        request = self.request

        filter_queryset = self.queryset
        assert filter_queryset is not None

        # Apply filters to the filter queryset.
        filter_queryset = self.post_process_queryset_for_filter(
            filter_queryset.all(),
            request=request)

        # We can now base the data queryset off of this.
        data_queryset = filter_queryset.all()

        use_select_related: bool = False

        # Generate the actual list of fields we'll be sorting by
        sort_list: List[str] = []

        for sort_item in self.sort_list:
            if sort_item[0] == '-':
                base_sort_item = sort_item[1:]
                prefix = '-'
            else:
                base_sort_item = sort_item
                prefix = ''

            if sort_item:
                column = self.get_column(base_sort_item)

                if not column:
                    logger.warning('Skipping non-existing sort column "%s"',
                                   base_sort_item,
                                   extra={'request': request})
                    continue

                elif not column.sortable:
                    logger.warning('Skipping column "%s" which is not '
                                   'sortable',
                                   base_sort_item,
                                   extra={'request': request})
                    continue

                stateful_column = self.get_stateful_column(column)

                if stateful_column:
                    try:
                        sort_field = stateful_column.get_sort_field()
                    except Exception as e:
                        logger.exception('Error when calling get_sort_field '
                                         'for DataGrid Column %r: %s',
                                         column, e,
                                         extra={'request': request})
                        continue

                    if sort_field:
                        sort_list.append(prefix + sort_field)

                    # Lookups spanning tables require that we query from those
                    # tables. In order to keep things simple, we'll just use
                    # select_related so that we don't have to figure out the
                    # table relationships. We only do this if we have a lookup
                    # spanning tables.
                    if '.' in sort_field:
                        use_select_related = True

        # If we're sorting, apply the sort list to the data queryset only.
        if sort_list:
            data_queryset = data_queryset.order_by(*sort_list)

        # This is a legacy approach to post-processing querysets. We'll only
        # use it for the data queryset, since filtering was never officially
        # supported prior to Djblets 3.4/4.1.
        #
        # Note that we'll end up calling this again when filtering by IDs.
        data_queryset = self.post_process_queryset(data_queryset)

        # Filter out duplicates in the data queryset. We won't bother with
        # the counts queryset. That's purely informational, so if it's off by
        # a bit, it's not a major problem.
        if self.use_distinct and hasattr(data_queryset, 'distinct'):
            data_queryset = data_queryset.distinct()

        paginator = self.build_paginator(
            queryset=data_queryset,
            total_count=filter_queryset.order_by().count())

        self.paginator = paginator

        # Figure out what page we're starting on.
        page_num = request.GET.get('page', 1)

        # Accept either "last" or a valid page number.
        if page_num == 'last':
            page_num = paginator.num_pages

        try:
            page = paginator.page(page_num)
        except InvalidPage:
            raise Http404

        self.page = page

        id_list: List[Any] = []

        if self.optimize_sorts and len(sort_list) > 0:
            # This can be slow when sorting by multiple columns. If we
            # have multiple items in the sort list, we'll request just the
            # IDs and then fetch the actual details from that.
            if hasattr(page.object_list, 'values_list'):
                # This is a standard QuerySet.
                id_list = list(
                    page.object_list
                    .values_list('pk', flat=True)  # type: ignore
                )
            else:
                # This is something more custom. Perhaps a Haystack
                # SearchQuerySet. It must have a 'pk' or it won't work.
                id_list = [
                    int(obj.pk)
                    for obj in page.object_list
                ]

            self.id_list = id_list

            # Make sure to unset the order. We can't meaningfully order these
            # results in the query, as what we really want is to keep it in
            # the order specified in id_list, and we certainly don't want
            # the database to do any special ordering (possibly slowing things
            # down). We'll set the order properly in a minute.
            assert self.model is not None
            page_queryset = self.post_process_queryset(
                self.model.objects.filter(pk__in=id_list).order_by())
        else:
            self.id_list = id_list
            page_queryset = page.object_list  # type: ignore

        page_queryset = self.post_process_queryset_for_data(
            page_queryset,  # type: ignore
            request=request)

        if use_select_related and hasattr(page.object_list, 'select_related'):
            page_queryset = (
                page_queryset
                .select_related(depth=1)  # type: ignore
            )

        page.object_list = page_queryset

        object_list: List[Optional[Model]]

        if id_list:
            # The database will give us the items in a more or less random
            # order, since it doesn't know to keep it in the order provided by
            # the ID list. This will place the results back in the order we
            # expect.
            index = {
                obj_id: pos
                for pos, obj_id in enumerate(id_list)
            }
            object_list = [None] * len(id_list)

            for obj in list(page.object_list):
                object_list[index[obj.pk]] = obj
        else:
            # Grab the whole list at once. We know it won't be too large,
            # and it will prevent one query per row.
            object_list = list(page.object_list)

        stateful_columns = self.columns

        for stateful_column in stateful_columns:
            stateful_column.collect_objects(object_list)

        if render_context is None:
            render_context = self._build_render_context()

        rows: List[_DataGridRow] = []

        for obj in object_list:
            if obj is None:
                continue

            if hasattr(obj, 'get_absolute_url'):
                obj_url = obj.get_absolute_url()  # type: ignore
            else:
                obj_url = None

            render_context['_datagrid_object_url'] = obj_url

            cells: list[SafeString] = []

            for stateful_column in stateful_columns:
                try:
                    rendered_cell = stateful_column.render_cell(
                        obj, render_context)
                except Exception as e:
                    logger.exception(
                        'Error when calling render_cell for DataGrid '
                        'Column %r: %s',
                        stateful_column, e,
                        extra={'request': request})
                    rendered_cell = mark_safe('')

                cells.append(rendered_cell)

            rows.append({
                'object': obj,
                'cells': cells,
                'url': obj_url,
            })

        self.rows = rows

    def post_process_queryset_for_filter(
        self,
        queryset: QuerySet,
        **kwargs,
    ) -> QuerySet:
        """Add column-specific filters to the queryset.

        Subclasses can override this to add filters to the queryset to limit
        the results returned for display and for pagination.

        This must not be used to load additional data for display, or to
        pre-fetch/select-related any columns, unless required as part of the
        filter. Instead, override :py:meth:`post_process_queryset_for_data`.

        Version Added:
            3.4

        Args:
            queryset (django.db.models.query.QuerySet):
                The queryset to augment.

            **kwargs (dict):
                Additional keyword arguments for future expansion.

        Returns:
            django.db.models.query.QuerySet:
            The resulting augmented QuerySet.
        """
        request = self.request

        for column in self.columns:
            try:
                queryset = column.augment_queryset_for_filter(
                    queryset=queryset,
                    request=request)
            except Exception as e:
                logger.exception(
                    'Error when calling augment_queryset_for_filter() for '
                    'DataGrid Column %r: %s',
                    column, e,
                    extra={'request': request})

        return queryset

    def post_process_queryset_for_data(
        self,
        queryset: QuerySet,
        **kwargs,
    ) -> QuerySet:
        """Add column-specific data lookups to the queryset.

        Subclasses can override this to query for additional data used for
        displaying this column.

        This must not be used to filter querysets. Instead, override
        :py:meth:`post_process_queryset_for_filter`.

        Version Added:
            3.4

        Args:
            queryset (django.db.models.query.QuerySet):
                The queryset to augment.

            **kwargs (dict):
                Additional keyword arguments for future expansion.

        Returns:
            django.db.models.query.QuerySet:
            The resulting augmented QuerySet.
        """
        request = self.request

        for column in self.columns:
            try:
                queryset = column.augment_queryset_for_data(
                    queryset=queryset,
                    request=request)
            except Exception as e:
                logger.exception(
                    'Error when calling augment_queryset_for_data() for '
                    'DataGrid Column %r: %s',
                    column, e,
                    extra={'request': request})

        return queryset

    def post_process_queryset(
        self,
        queryset: QuerySet,
    ) -> QuerySet:
        """Add column-specific data to the queryset.

        Individual columns can define additional joins and extra info to add on
        to the queryset. This handles adding all of those.

        Args:
            queryset (django.db.models.query.QuerySet):
                The queryset to augment.

        Returns:
            django.db.models.query.QuerySet:
            The resulting augmented QuerySet.
        """
        for column in self.columns:
            try:
                queryset = column.augment_queryset(queryset)
            except Exception as e:
                logger.exception('Error when calling augment_queryset for '
                                 'DataGrid Column %r: %s',
                                 column, e,
                                 extra={'request': self.request})

        return queryset

    def render_listview(
        self,
        render_context: Optional[_RenderContext] = None,
    ) -> SafeString:
        """Render the standard list view of the grid.

        This can be called from templates.

        Args:
            render_context (dict or django.template.Context, optional):
                The common template variable context to render on the datagrid,
                provided in the constructor.

        Returns:
            django.utils.safestring.SafeString:
            The rendered HTML for the datagrid page.
        """
        try:
            if render_context is None:
                render_context = self._build_render_context()

            self.load_state(render_context)

            context: Dict[str, Any] = {
                'datagrid': self,
            }

            context.update(self.extra_context)
            context.update(render_context)

            return render_to_string(self.listview_template, context)
        except Exception:
            trace = traceback.format_exc()
            logger.exception('Failed to render datagrid:\n%s',
                             trace,
                             extra={'request': self.request})
            return format_html('<pre>{0}</pre>', trace)

    def render_listview_to_response(
        self,
        request: Optional[HttpRequest] = None,
        render_context: Optional[_RenderContext] = None,
    ) -> HttpResponse:
        """Render the listview to a response.

        The rendered result will not be cached by the browser.

        Args:
            request (django.http.HttpRequest, optional):
                The HTTP request from the client.

            render_context (dict or django.template.Context, optional):
                The common template variable context to render on the datagrid,
                provided in the constructor.

        Returns:
            django.http.HttpResponse:
            The HTTP response to send to the client.
        """
        response = HttpResponse(str(self.render_listview(render_context)))
        add_never_cache_headers(response)
        return response

    def render_to_response(
        self,
        template_name: str,
        extra_context: _RenderContext = {},
    ) -> HttpResponse:
        """Render the entire datagrid page to a response.

        This will render the entire page, given the specified template, with
        the datagrid as a part of it. This is the primary function a view
        will be using to render the page.

        Args:
            template_name (str):
                The template for the page.

            extra_context (dict or django.template.Context):
                Extra context variables to use in the template.

        Returns:
            django.http.HttpResponse:
            The HTTP response to send to the client.
        """
        render_context = self._build_render_context()
        self.load_state(render_context)

        request = self.request

        # If the caller is requesting just this particular grid, return it.
        if (request.GET.get('gridonly', False) and
            request.GET.get('datagrid-id', None) == self.id):
            return self.render_listview_to_response(
                render_context=render_context)

        context: Dict[str, Any] = {
            'datagrid': self,
        }
        context.update(extra_context)
        context.update(render_context)

        response = HttpResponse(
            render_to_string(template_name=template_name, context=context))
        add_never_cache_headers(response)
        return response

    def render_paginator(
        self,
        adjacent_pages: int = 3,
    ) -> SafeString:
        """Render the paginator for the datagrid.

        This can be called from templates.

        Args:
            adjacent_pages (int):
                The number of adjacent page numbers to show in the
                paginator.

        Returns:
            django.utils.safestring.SafeString:
            The paginator as HTML.
        """
        request = self.request
        extra_query = get_url_params_except(request.GET,
                                            'page', 'gridonly',
                                            *self.special_query_args)

        paginator = self.paginator
        page = self.page

        assert paginator is not None
        assert page is not None

        page_nums = range(max(1, page.number - adjacent_pages),
                          min(paginator.num_pages,
                              page.number + adjacent_pages) + 1)

        if page_nums:
            show_first = (page_nums[0] != 1)
            show_last = (page_nums[-1] != paginator.num_pages)
        else:
            show_first = False
            show_last = False

        if extra_query:
            extra_query += '&'

        # Generate rel tags for the HTML.
        rel_common: str = ''
        nofollow: str = ''

        if (not self.allow_search_indexing or
            'sort' in request.GET or
            'columns' in request.GET or
            'gridonly' in request.GET):
            # When there are view options or internal flags, we want to
            # avoid following or indexing any pagination links.
            rel_common = ' nofollow noindex'
        else:
            nofollow = ' nofollow'

        context = {
            'extra_query': extra_query,
            'has_next': page.has_next(),
            'has_previous': page.has_previous(),
            'hits': paginator.count,
            'is_paginated': page.has_other_pages(),
            'page': page.number,
            'page_numbers': page_nums,
            'pages': paginator.num_pages,
            'rel_first_page': f'first{rel_common}',
            'rel_last_page': f'last{nofollow}{rel_common}',
            'rel_next_page': f'next{rel_common}',
            'rel_page': rel_common.strip(),
            'rel_prev_page': f'prev{rel_common}',
            'results_per_page': self.paginate_by,
            'show_first': show_first,
            'show_last': show_last,
        }

        if page.has_next():
            context['next'] = page.next_page_number()
        else:
            context['next'] = None

        if page.has_previous():
            context['previous'] = page.previous_page_number()
        else:
            context['previous'] = None

        context.update(self.extra_context)

        return render_to_string(self.paginator_template, context)

    def build_paginator(
        self,
        queryset: QuerySet,
        *,
        total_count: int,
        **kwargs,
    ) -> DataGridPaginator:
        """Build the paginator for the datagrid.

        This can be overridden to use a special paginator or to perform
        any kind of processing before passing on the query.

        Args:
            queryset (django.db.models.QuerySet):
                A queryset-compatible object for fetching column data.

            total_count (int):
                The total number of items across all pages.

            **kwargs (dict):
                Additional keyword arguments, for future expansion.

        Returns:
            DataGridPaginator
            A populated paginator object.
        """
        return DataGridPaginator(
            object_list=queryset,
            total_count=total_count,
            per_page=self.paginate_by,
            orphans=self.paginate_orphans)

    def to_json(self) -> DataGridJSONData:
        """Serialize the datagrid to a JSON-compatible dictionary.

        This method produces a complete representation of the datagrid's
        current state, including column metadata, row data, pagination
        information, and sort state. The result is suitable for use with
        :py:class:`~django.http.JsonResponse` or an API response.

        Version Added:
            5.3

        Returns:
            DataGridJSONData:
            A dictionary containing a JSON-serializable representation of
            the datagrid.
        """
        self.load_state()

        stateful_columns = self.columns

        # Serialize the information for each column.
        active_columns_data: list[DataGridColumnJSONData] = []
        inactive_columns_data: list[DataGridColumnJSONData] = []
        active_columns: set[str] = set()

        for stateful_column in stateful_columns:
            column = stateful_column.column
            active_columns.add(column.id)

            active_columns_data.append({
                'expand': column.expand,
                'id': column.id,
                'label': str(column.label),
                'shrink': column.shrink,
                'sortable': column.sortable,
                'width': stateful_column.width,
            })

        for stateful_column in self.all_columns:
            column = stateful_column.column

            if column.id not in active_columns:
                inactive_columns_data.append({
                    'expand': column.expand,
                    'id': column.id,
                    'label': str(column.label),
                    'shrink': column.shrink,
                    'sortable': column.sortable,
                    'width': stateful_column.width,
                })

        # Begin serializing each row in the datagrid.
        rows_data: list[DataGridRowJSONData] = []
        page = self.page

        assert page is not None

        for row in self.rows:
            # Serialize each cell in the row.
            cells_data: dict[str, DataGridCellJSONData] = {}
            obj = row['object']

            for stateful_column, html in zip(stateful_columns, row['cells']):
                column = stateful_column.column

                cells_data[column.id] = {
                    'html': html,
                    'value': column.to_json(stateful_column, obj),
                }

            rows_data.append({
                'cells': cells_data,
                'url': row['url'],
            })

        # Serialize the pagination data.
        paginator = self.paginator
        assert paginator is not None

        pagination_data: DataGridPaginationJSONData = {
            'current_page': page.number,
            'end_index': page.end_index(),
            'has_next': page.has_next(),
            'has_previous': page.has_previous(),
            'per_page': self.paginate_by,
            'start_index': page.start_index(),
            'total_count': paginator.count,
            'total_pages': paginator.num_pages,
        }

        # Serialize the sort state.
        sort_data: list[DataGridSortItemJSONData] = []

        if sort_list := self.sort_list:
            for sort_item in sort_list:
                if sort_item.startswith('-'):
                    column_id = sort_item[1:]
                    ascending = False
                else:
                    column_id = sort_item
                    ascending = True

                sort_data.append({
                    'ascending': ascending,
                    'column': column_id,
                })

        return {
            'available_columns': inactive_columns_data,
            'columns': active_columns_data,
            'pagination': pagination_data,
            'rows': rows_data,
            'sort': sort_data,
        }

    def _build_render_context(self) -> _RenderContext:
        """Build a dictionary containing RequestContext contents.

        A RequestContext can be expensive, so it's best to reuse the
        contents of one when possible. This is not easy with a standard
        RequestContext, but it's possible to build one and then pull out
        the contents into a dictionary.
        """
        request = self.request
        render_context: _RenderContext = {}

        for context_processor in get_default_template_context_processors():
            render_context.update(context_processor(request))

        return render_context

    @staticmethod
    def link_to_object(
        state: StatefulColumn,
        obj: Any,
        value: Any,
    ) -> str:
        """Return a URL for the given object.

        This defaults to calling ``obj.get_absolute_url``.

        Returns:
            str:
            The URL for the object.
        """
        return obj.get_absolute_url()

    @staticmethod
    def link_to_value(
        state: StatefulColumn,
        obj: Any,
        value: Any,
    ) -> str:
        """Return a URL for the given value.

        This defaults to calling ``value.get_absolute_url``.

        Returns:
            str:
            The URL for the value.
        """
        return value.get_absolute_url()


class AlphanumericDataGrid(DataGrid):
    """A DataGrid subclass for an alphanumerically-paginated datagrid.

    This is useful for datasets that need to be queried alphanumerically,
    according to the starting character of their ``sortable`` column.
    """

    ######################
    # Instance variables #
    ######################

    #: The current letter being displayed on the datagrid.
    #:
    #: Type:
    #:     str
    current_letter: str

    # TODO: After Djblets 7, convert this to keyword-only with deprecation.
    #       We want to wait until after DataGrid is moved over, so we don't
    #       break *args.
    def __init__(
        self,
        request: HttpRequest,
        queryset: QuerySet,
        sortable_column: str,
        extra_regex: str = '^[0-9].*',
        *args,
        **kwargs,
    ) -> None:
        """Initialize the datagrid.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            queryset (django.db.models.QuerySet):
                A QuerySet returning the objects to render in the grid.

            sortable_column (str):
                The model field used for the alphanumeric prefixes.

            extra_regex (str, optional):
                A regex used for matching the beginning of entries in
                ``sortable_column``.

            *args (tuple):
                Positional arguments to pass to the parent constructor.

            **kwargs (dict):
                Keyword arguments to pass to the parent constructor.
        """
        current_letter = request.GET.get('letter', 'all')
        self.current_letter = current_letter

        regex_match = re.compile(extra_regex)

        if current_letter == 'all':
            pass  # No filtering
        elif current_letter.isalpha():
            queryset = queryset.filter(**{
                sortable_column + '__istartswith': current_letter
            })
        elif regex_match.match(current_letter):
            queryset = queryset.filter(**{
                sortable_column + '__regex': extra_regex
            })
        else:
            raise Http404

        super().__init__(request, queryset, *args, **kwargs)

        self.extra_context['current_letter'] = current_letter
        self.extra_context['letters'] = (['all', '0'] +
                                         list(string.ascii_uppercase))

        self.special_query_args.append('letter')
        self.paginator_template = 'datagrid/alphanumeric_paginator.html'


#: A type alias for a function that returns a URL for an object.
#:
#: Version Added:
#:     3.4
LinkObjectFunc: TypeAlias = Callable[[StatefulColumn, Any, str], str]


#: A type alias for a function that returns a CSS class name for a link.
#:
#: Version Added:
#:     3.4
LinkCSSClassFunc: TypeAlias = Callable[[Any], str]


#: A type alias for a function that returns a CSS class name for an object.
#:
#: Version Added:
#:     3.4
BuildCSSClassFunc: TypeAlias = Callable[[Any], str]
