(function($) {


/*
 * Creates a datagrid. This will cause drag and drop and column
 * customization to be enabled.
 */
jQuery.fn.datagrid = function() {
    /* References */
    var that = this;
    var gridId = this.attr("id");
    var editButton = $("#" + gridId + "-edit");
    var menu = $("#" + gridId + "-menu");
    var editColumns = $("th.edit-columns", this);

    /* State */
    var activeColumns = [];
    var activeMenu = null;
    var columnMidpoints = [];
    var dragColumn = null;
    var dragColumnsChanged = false;
    var dragColumnWidth = 0;
    var dragIndex = 0;
    var dragLastX = 0;

    /* Add all the non-special columns to the list. */
    $("col", this).not(".datagrid-customize").each(function(i) {
        activeColumns.push(this.className);
    });

    /* Make the columns unselectable. */
    $.ui.disableSelection($("th", this));

    /* Make the columns draggable. */
    $("th", this).not(".edit-columns").draggable({
        appendTo: "body",
        axis: "x",
        containment: $("thead:first", this),
        cursor: "move",
        helper: function() {
            return $("<div></div>")
                .addClass("datagrid-header-drag datagrid-header")
                .width($(this).width())
                .height($(this).height())
                .css("top", $(this).offset().top)
                .html($(this).html());
        },
        start: startColumnDrag,
        stop: endColumnDrag,
        drag: onColumnDrag
    });

    /* Register callbacks for the columns. */
    $("tr", menu).each(function(i) {
        var className = this.className;

        $(".datagrid-menu-checkbox, .datagrid-menu-label a", this).click(
            function() {
                toggleColumn(className);
            }
        );
    });

    editButton.click(function(evt) {
        evt.stopPropagation();
        toggleColumnsMenu();
    });

    $(document.body).click(hideColumnsMenu);


    /********************************************************************
     * Column customization
     ********************************************************************/

    /*
     * Hides the currently open columns menu.
     */
    function hideColumnsMenu() {
        if (activeMenu != null) {
            activeMenu.hide();
            activeMenu = null;
        }
    }

    /*
     * Toggles the visibility of the specified columns menu.
     */
    function toggleColumnsMenu() {
        if (menu.is(":visible")) {
            hideColumnsMenu();
        } else {
            var offset = editButton.offset()

            menu.css({
                left: offset.left - menu.outerWidth() + editButton.outerWidth(),
                top:  offset.top + editButton.outerHeight()
            });
            menu.show();

            activeMenu = menu;
        }
    }

    /*
     * Saves the new columns list on the server.
     *
     * @param {string}   columnsStr  The columns to display.
     * @param {function} onSuccess   Optional callback on successful save.
     */
    function saveColumns(columnsStr, onSuccess) {
        var url = window.location.pathname +
                  "?gridonly=1&datagrid-id=" + gridId +
                  "&columns=" + columnsStr;

        jQuery.get(url, onSuccess);
    }

    /*
     * Toggles the visibility of a column. This will build the resulting
     * columns string and request a save of the columns, followed by a
     * reload of the page.
     *
     * @param {string}  columnId  The ID of the column to toggle.
     */
    function toggleColumn(columnId) {
        saveColumns(serializeColumns(columnId), function(html) {
            that.replaceWith(html);
            $("#" + gridId).datagrid();
        });
    }

    /*
     * Serializes the active column list, optionally adding one new entry
     * to the end of the list.
     *
     * @return The serialized column list.
     */
    function serializeColumns(addedColumn) {
        var columnsStr = "";

        $(activeColumns).each(function(i) {
            var curColumn = activeColumns[i];

            if (curColumn == addedColumn) {
                /* We're removing this column. */
                addedColumn = null;
            } else {
                columnsStr += curColumn;

                if (i < activeColumns.length - 1) {
                    columnsStr += ",";
                }
            }
        });

        if (addedColumn) {
            columnsStr += "," + addedColumn;
        }

        return columnsStr;
    }


    /********************************************************************
     * Column reordering support
     ********************************************************************/

    /*
     * Handles the beginning of the drag.
     *
     * Builds the column information needed for determining when we should
     * switch columns.
     *
     * @param {event}  evt The event.
     * @param {object} ui  The jQuery drag and drop information.
     */
    function startColumnDrag(evt, ui) {
        dragColumn = this;
        dragColumnsChanged = false;
        dragColumnWidth = ui.helper.width();
        dragIndex = 0;
        dragLastX = 0;
        buildColumnInfo();

        /* Hide the column but keep its area reserved. */
        $(this).css("visibility", "hidden");
    }

    /*
     * Handles the end of a drag.
     *
     * This shows the original header (now in its new place) and saves
     * the new columns configuration.
     */
    function endColumnDrag() {
        /* Re-show the column header. */
        $(this).css("visibility", "visible");

        columnMidpoints = [];

        if (dragColumnsChanged) {
            /* Build the new columns list */
            saveColumns(serializeColumns());
        }
    }

    /*
     * Handles movement while in drag mode.
     *
     * This will check if we've crossed the midpoint of a column. If so, we
     * switch the columns.
     *
     * @param {event}  e  The event.
     * @param {object} ui The jQuery drag and drop information.
     */
    function onColumnDrag(e, ui) {
        /*
         * Check the direction we're moving and see if we're ready to switch
         * with another column.
         */
        var x = e.pageX;

        if (x == dragLastX) {
            /* No change that we care about. Bail out. */
            return;
        }

        var hitX = -1;
        var index = -1;

        if (x < dragLastX) {
            index = dragIndex - 1;
            hitX = ui.absolutePosition.left;
        } else {
            index = dragIndex + 1;
            hitX = ui.absolutePosition.left + ui.helper.width();
        }

        if (index >= 0 && index < columnMidpoints.length) {
            /* Check that we're dragging past the midpoint. If so, swap. */
            if (x < dragLastX && hitX <= columnMidpoints[index]) {
                swapColumnBefore(dragIndex, index);
            } else if (x > dragLastX && hitX >= columnMidpoints[index]) {
                swapColumnBefore(index, dragIndex);
            }
        }

        dragLastX = x;
    }

    /*
     * Builds the necessary information on the columns.
     *
     * This will construct an array of midpoints that are used to determine
     * when we should swap columns during a drag. It also sets the index
     * of the currently dragged column.
     */
    function buildColumnInfo() {
        /* Clear and rebuild the list of mid points. */
        columnMidpoints = [];

        $("th", that).not(".edit-columns").each(function(i) {
            var column = $(this);
            var offset = column.offset();

            if (this == dragColumn) {
                dragIndex = i;

                /*
                 * Getting the width of an invisible element is very bad
                 * when the element is a <th>. Use our pre-calculated width.
                 */
                width = dragColumnWidth;
            } else {
                width = column.width();
            }

            columnMidpoints.push(Math.round(offset.left + width / 2));
        });
    }

    /*
     * Swaps two columns, placing the first before the second.
     *
     * It is assumed that the two columns are siblings. Horrible disfiguring
     * things might happen if this isn't the case, or it might not. Who
     * can tell. Our code behaves, though.
     *
     * @param {int} index       The index of the column to move.
     * @param {int} beforeIndex The index of the column to place the first
     *                          before.
     */
    function swapColumnBefore(index, beforeIndex) {
        /* Swap the column info. */
        var colTags = $("col", that);
        $(colTags[index]).insertBefore($(colTags[beforeIndex]));

        /* Swap the list of active columns */
        var tempName = activeColumns[index];
        activeColumns[index] = activeColumns[beforeIndex];
        activeColumns[beforeIndex] = tempName;

        /* Swap the cells. This will include the headers. */
        var table = $("table:first", that)[0];
        for (var i = 0; i < table.rows.length; i++) {
            var row = table.rows[i];
            var cell = row.cells[index];
            var beforeCell = row.cells[beforeIndex];

            row.insertBefore(cell, beforeCell);

            /* Switch the colspans. */
            var tempColSpan = cell.colSpan;
            cell.colSpan = beforeCell.colSpan;
            beforeCell.colSpan = tempColSpan;
        }

        dragColumnsChanged = true;

        /* Everything has changed, so rebuild our view of things. */
        buildColumnInfo();
    }

    return this;
};

$(document).ready(function() {
    $("div.datagrid-wrapper").datagrid();
});

})(jQuery);
