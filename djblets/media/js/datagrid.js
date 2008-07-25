/* Create the DJBLETS namespace if it doesn't exist. */
if (!DJBLETS) {
    var DJBLETS = {};
}

try {
    if (Ext) {
        /*
         * We use getEl() from the old yui-ext. Make this wrap Ext.get if
         * using extjs.
         */
        getEl = Ext.get;
    }
} catch (e) {
}

DJBLETS.datagrids = {
    activeMenu: null,
    activeColumns: {},

    /*
     * Registers a datagrid. This will cause drag and drop and column
     * customization to be enabled.
     *
     * @param {HTMLElement} grid  The datagrid element.
     */
    registerDataGrid: function(grid) {
        this.activeColumns[grid] = [];

        var cols = grid.getElementsByTagName("col");
        for (var j = 0; j < cols.length; j++) {
            if (cols[j].className != "datagrid-customize") {
                this.activeColumns[grid].push(cols[j].className);
            }
        }

        var headers = grid.getElementsByTagName("th");

        for (var j = 0; j < headers.length; j++) {
            var header = getEl(headers[j]);
            header.unselectable();

            if (!header.hasClass("edit-columns")) {
                new DJBLETS.datagrids.DDColumn(header, grid);
            }
        }
    },

    /*
     * Unregisters a datagrid. This is used when we're getting ready to
     * reload a grid.
     *
     * @param {HTMLElement} grid  The datagrid.
     */
    unregisterDataGrid: function(grid) {
        this.activeColumns[grid] = [];
    },

    /*
     * Hides the currently open columns menu.
     */
    hideColumnsMenu: function() {
        if (this.activeMenu != null) {
            this.activeMenu.hide();
            this.activeMenu = null;
        }
    },

    /*
     * Toggles the visibility of the specified columns menu.
     *
     * @param {string}      menu_id  The ID of the menu.
     * @param {HTMLElement} elid     The element ID of the link that
     *                               called this function.
     * @param {event}       evt      The event that triggered this, if any.
     */
    toggleColumnsMenu: function(menu_id, elid, evt) {
        var el = getEl(elid);
        var menu = getEl(menu_id);

        if (menu.isVisible()) {
            this.hideColumnsMenu();
        } else {
            if (el.beginMeasure) {
                el.beginMeasure();
            }

            xy = el.getXY()

            if (el.endMeasure) {
                el.endMeasure();
            }

            menu.moveTo(xy[0] - menu.getWidth() + el.getWidth(),
                        xy[1] + el.getHeight());
            menu.show();
            this.activeMenu = menu;
        }

        if (evt) {
            YAHOO.util.Event.stopEvent(evt);
        }
    },

    /*
     * Callback handler for when the page finishes loading. Registers
     * the grids and enables drag and drop for the datagrids.
     */
    onPageLoad: function() {
        var grids = YAHOO.util.Dom.getElementsByClassName("datagrid-wrapper",
                                                          "div");
        for (var i = 0; i < grids.length; i++) {
            this.registerDataGrid(grids[i]);
        }
    },

    /*
     * Saves the new columns list on the server.
     *
     * @param {{string}}   gridId      The ID of the datagrid.
     * @param {{string}}   columnsStr  The columns to display.
     * @param {{function}} onSuccess   Optional callback on successful save.
     */
    saveColumns: function(gridId, columnsStr, onSuccess) {
        var url = window.location.pathname +
                  "?gridonly=1&datagrid-id=" + gridId +
                  "&columns=" + columnsStr;

        YAHOO.util.Connect.asyncRequest("GET", url, {
            success: onSuccess
        });
    },

    /*
     * Toggles the visibility of a column. This will build the resulting
     * columns string and request a save of the columns, followed by a
     * reload of the page.
     *
     * @param {{string}}  gridId    The ID of the datagrid.
     * @param {{string}}  columnId  The ID of the column to toggle.
     */
    toggleColumn: function(gridId, columnId) {
        var addingColumn = true;
        var grid = document.getElementById(gridId);
        var curColumns = this.activeColumns[grid];
        var newColumnsStr = "";

        for (var i = 0; i < curColumns.length; i++) {
            if (curColumns[i] == columnId) {
                /* We're removing this column. */
                addingColumn = false;
            } else {
                newColumnsStr += curColumns[i];

                if (i < curColumns.length - 1) {
                    newColumnsStr += ",";
                }
            }
        }

        if (addingColumn) {
            newColumnsStr += "," + columnId;
        }

        this.saveColumns(gridId, newColumnsStr, function(res) {
            this.hideColumnsMenu();
            this.unregisterDataGrid(gridId);

            /* The resulting text *should* be datagrid HTML. */
            var oldEl = getEl(gridId);
            oldEl.dom.id = "";

            var html = res.responseText;

            if (oldEl.dom.insertAdjacentHTML) {
                /* Supported by IE */
                oldEl.dom.insertAdjacentHTML("beforeBegin", html);
            } else {
                /* Everybody else. */
                var range = oldEl.dom.ownerDocument.createRange();
                range.setStartBefore(oldEl.dom);
                var newEl = range.createContextualFragment(html);
                oldEl.dom.parentNode.insertBefore(newEl, oldEl.dom);
            }
            oldEl.remove();

            this.registerDataGrid(document.getElementById(gridId));
        }.createDelegate(this));
    }
}


/*
 * Special drag-and-drop object for draggable columns.
 *
 * This handles the work of representing the dragged column, placing it in
 * a new spot, rearranging all the cells for the new arrangement, and saving
 * the setting.
 *
 * @param {Element} el    The column header Element.
 * @param {Element} grid  The datagrid element.
 */
DJBLETS.datagrids.DDColumn = function(el, grid) {
    this.grid = grid;
    this.el = el;
    DJBLETS.datagrids.DDColumn.superclass.constructor.apply(this, [
        YAHOO.util.Dom.generateId(el.dom), "datagrid-columns", {
            resizeFrame: false
        }
    ]);
}

YAHOO.extend(DJBLETS.datagrids.DDColumn, YAHOO.util.DDProxy, {
    grid: null,
    el: null,
    lastX: 0,
    columnMidpoints: [],
    columns: [],
    dragIndex: 0,

    /*
     * Initializes the object. This just wraps DDProxy.init and calls
     * initConstraints().
     */
    init: function() {
        DJBLETS.datagrids.DDColumn.superclass.init.apply(this, arguments);

        /*
         * YAHOO.ext.EventManager has a nice buffered onWindowResize
         * function that gives us buffered resizes. It depends on some
         * additional YAHOO.ext code, which is why we don't (yet) re-implement
         * it. However, we may wish to do so in the future to remove the
         * deprecated yui-ext support from this file.
         */
        if (YAHOO.ext) {
            YAHOO.ext.EventManager.onWindowResize(this.initConstraints,
                                                  this, true);
        } else {
            YAHOO.util.Event.on(window, "resize",
                                this.initConstraints.createDelegate(this));
        }

        this.initConstraints();
    },

    /*
     * Sets up the movement constraints for this column. This locks the
     * column into the column header region. It has the effect of only
     * allowing the column to slide left and right.
     */
    initConstraints: function() {
        var thead = getEl(this.grid.getElementsByTagName("thead")[0]);
        var headerRegion = thead.getRegion();
        var colRegion = this.el.getRegion();

        this.setXConstraint(colRegion.left - headerRegion.left,
                            headerRegion.right - colRegion.right);
        this.setYConstraint(colRegion.top - headerRegion.top,
                            headerRegion.bottom - colRegion.bottom);
    },

    /*
     * Handles the beginning of the drag.
     *
     * Creates the proxy element and builds the column information needed
     * for determining when we should switch columns.
     *
     * @param {int} x  The X position of the mousedown.
     * @param {int} y  The Y position of the mousedown.
     */
    startDrag: function(x, y) {
        var dragEl = getEl(this.getDragEl());
        this.el.hide();

        dragEl.setStyle("border", "");
        dragEl.dom.innerHTML = this.el.dom.innerHTML;
        dragEl.addClass(this.el.dom.className);
        dragEl.addClass("datagrid-header-drag");

        /* Account for the padding of the contents in the width and height. */
        dragEl.setWidth(this.el.getWidth());
        dragEl.setHeight(this.el.getHeight());

        this.buildColumnInfo();
    },

    /*
     * Handles the end of a drag.
     *
     * This removes the proxy element, shows the original header (now in its
     * new place) and saves the new arrangement.
     *
     * @param {event} e  The event.
     */
    endDrag: function(e) {
        var dragEl = getEl(this.getDragEl());
        dragEl.hide();
        this.el.show();

        this.columnMidpoints = [];

        /* Build the new columns list. */
        var columns = DJBLETS.datagrids.activeColumns[this.grid];
        var columnsStr = "";

        for (var i = 0; i < columns.length; i++) {
            columnsStr += columns[i];

            if (i != columns.length - 1) {
                columnsStr += ",";
            }
        }

        DJBLETS.datagrids.saveColumns(this.grid.id, columnsStr);
    },

    /*
     * Handles movement while in drag mode.
     *
     * This will check if we've crossed the midpoint of a column. If so, we
     * switch the columns.
     *
     * @param {event} e  The event.
     */
    onDrag: function(e) {
        /*
         * Check the direction we're moving and see if we're ready to switch
         * with another column.
         */
        var x = YAHOO.util.Event.getPageX(e);

        if (x == this.lastX) {
            /* No change that we care about. Bail out. */
            return;
        }

        var dragEl = getEl(this.getDragEl());
        var hitX = -1;
        var index = -1;

        if (x < this.lastX) {
            index = this.dragIndex - 1;
            hitX = dragEl.getX();
        } else {
            index = this.dragIndex + 1;
            hitX = dragEl.getRight();
        }

        if (index >= 0 && index < this.columnMidpoints.length) {
            /* Check that we're dragging past the midpoint. If so, swap. */
            if (x < this.lastX && hitX <= this.columnMidpoints[index]) {
                this.swapColumnBefore(this.dragIndex, index);
            } else if (x > this.lastX && hitX >= this.columnMidpoints[index]) {
                this.swapColumnBefore(index, this.dragIndex);
            }
        }

        this.lastX = x;
    },

    /*
     * Builds the necessary information on the columns.
     *
     * This will construct an array of midpoints that are used to determine
     * when we should swap columns during a drag. It also sets the index
     * of the currently dragged column.
     */
    buildColumnInfo: function() {
        /* Grab the list of midpoints for each column. */
        this.columnMidpoints = [];

        var columns = this.grid.getElementsByTagName("th");

        for (var i = 0; i < columns.length; i++) {
            var column = getEl(columns[i]);

            if (!column.hasClass("edit-columns")) {
                this.columnMidpoints.push(column.getX() +
                                          column.getWidth() / 2);

                if (column == this.el) {
                    this.dragIndex = i;
                }
            }
        }
    },

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
    swapColumnBefore: function(index, beforeIndex) {
        /* Swap the column info. */
        var colTags = this.grid.getElementsByTagName("col");
        getEl(colTags[index]).insertBefore(getEl(colTags[beforeIndex]));

        /* Swap the list of active columns */
        var tempName = DJBLETS.datagrids.activeColumns[this.grid][index];
        DJBLETS.datagrids.activeColumns[this.grid][index] =
            DJBLETS.datagrids.activeColumns[this.grid][beforeIndex];
        DJBLETS.datagrids.activeColumns[this.grid][beforeIndex] = tempName;

        /* Swap the cells. This will include the headers. */
        var table = this.grid.getElementsByTagName("table")[0];
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

        /* Everything has changed, so rebuild our view of things. */
        this.buildColumnInfo();
    }
});

YAHOO.util.Event.on(window, "load", function() {
    DJBLETS.datagrids.onPageLoad();
});

YAHOO.util.Event.on(document, "click", function(e) {
    if (DJBLETS.datagrids.activeMenu != null) {
        DJBLETS.datagrids.hideColumnsMenu();
    }
});
