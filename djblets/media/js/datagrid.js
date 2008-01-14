/* Create the DJBLETS namespace if it doesn't exist. */
if (!DJBLETS) {
	var DJBLETS = {};
}

DJBLETS.datagrids = {
	activeMenu: null,
	registeredGrids: [],
	activeColumns: {},

	/*
	 * Registers a datagrid. This will cause drag and drop and column
	 * customization to be enabled.
	 *
	 * @param {string} datagrid_id    The ID of the datagrid.
	 * @param {array}  activeColumns  The list of active columns in order.
	 */
	registerDataGrid: function(datagrid_id, activeColumns) {
		this.registeredGrids.push(datagrid_id);
		this.activeColumns[datagrid_id] = activeColumns;
	},

	/*
	 * Hides the currently open columns menu.
	 */
	hideColumnsMenu: function() {
		this.activeMenu.hide();
		this.activeMenu = null;
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
			el.beginMeasure();
			xy = el.getXY()
			el.endMeasure();
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
	 * Callback handler for when the page finishes loading. Enables
	 * drag and drop for the datagrids.
	 */
	onPageLoad: function() {
		for (var i = 0; i < this.registeredGrids.length; i++) {
			var grid = getEl(this.registeredGrids[i]);
			var headers = grid.getChildrenByTagName("th");

			for (var j = 0; j < headers.length; j++) {
				headers[j].unselectable();

				if (!headers[j].hasClass("edit-columns")) {
					new DJBLETS.datagrids.DDColumn(headers[j], grid);
				}
			}
		}
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

YAHOO.extendX(DJBLETS.datagrids.DDColumn, YAHOO.util.DDProxy, {
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
		this.initConstraints();
	},

	/*
	 * Sets up the movement constraints for this column. This locks the
	 * column into the column header region. It has the effect of only
	 * allowing the column to slide left and right.
	 */
	initConstraints: function() {
		var thead = this.grid.getChildrenByTagName("thead")[0];
		var headerRegion = thead.getRegion();
		var colRegion = this.el.getRegion();

		this.setXConstraint(colRegion.left - headerRegion.left,
		                    headerRegion.right - colRegion.right);
		this.setYConstraint(colRegion.top - headerRegion.top,
		                    headerRegion.bottom - colRegion.bottom);

		YAHOO.util.Event.on(window, 'resize',
		                    this.initConstraints, this, true);
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
		dragEl.dom.style.border = null;
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

		this.saveColumns();
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
		var columns = this.grid.getChildrenByTagName("th");

		for (var i = 0; i < columns.length; i++) {
			if (!columns[i].hasClass("edit-columns")) {
				this.columnMidpoints.push(columns[i].getX() +
				                          columns[i].getWidth() / 2);

				if (columns[i] == this.el) {
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
		var colTags = this.grid.getChildrenByTagName("col");
		colTags[index].insertBefore(colTags[beforeIndex]);

		/* Swap the list of active columns */
		var tempName = DJBLETS.datagrids.activeColumns[this.grid.id][index];
		DJBLETS.datagrids.activeColumns[this.grid.id][index] =
			DJBLETS.datagrids.activeColumns[this.grid.id][beforeIndex];
		DJBLETS.datagrids.activeColumns[this.grid.id][beforeIndex] = tempName;

		/* Swap the cells. This will include the headers. */
		var table = this.grid.getChildrenByTagName("table")[0].dom;
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
	},

	/*
	 * Saves the new columns list on the server.
	 */
	saveColumns: function() {
		var columns = "";
		var grid_id = this.grid.id;
		var len = DJBLETS.datagrids.activeColumns[grid_id].length;

		for (var i = 0; i < len; i++) {
			columns += DJBLETS.datagrids.activeColumns[grid_id][i];

			if (i != len - 1) {
				columns += ",";
			}
		}

		var url = ".?gridonly=1&datagrid-id=" + grid_id +
		          "&columns=" + columns;

		YAHOO.util.Connect.asyncRequest("GET", url);
	}
});

YAHOO.util.Event.on(window, "load",
                    DJBLETS.datagrids.onPageLoad.createDelegate(DJBLETS.datagrids));
YAHOO.util.Event.on(document, "click", function(e) {
	if (DJBLETS.datagrids.activeMenu != null) {
		DJBLETS.datagrids.hideColumnsMenu();
	}
});
