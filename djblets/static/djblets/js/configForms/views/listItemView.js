/*
 * Displays a list item for a config page.
 *
 * The list item will show information on the item and any actions that can
 * be invoked.
 *
 * By default, this will show the text from the ListItem model, linking it
 * if the model has an editURL attribute. This can be customized by subclasses
 * by overriding `template`.
 */
Djblets.Config.ListItemView = Backbone.View.extend({
    tagName: 'li',
    className: 'config-forms-list-item',
    iconBaseClassName: 'djblets-icon',

    actionHandlers: {},

    template: _.template([
        '<% if (editURL) { %>',
        '<a href="<%- editURL %>"><%- text %></a>',
        '<% } else { %>',
        '<%- text %>',
        '<% } %>'
    ].join('')),

    /*
     * Initializes the view.
     */
    initialize: function() {
        this.listenTo(this.model, 'actionsChanged', this.render);
        this.listenTo(this.model, 'request', this.showSpinner);
        this.listenTo(this.model, 'sync', this.hideSpinner);
        this.listenTo(this.model, 'destroy', this.remove);

        this.$spinnerParent = null;
        this.$spinner = null;
    },

    /* Renders the view.
     *
     * This will be called every time the list of actions change for
     * the item.
     */
    render: function() {
        this.$el
            .empty()
            .append(this.template(this.model.attributes));
        this.addActions(this.$el);

        return this;
    },

    /*
     * Removes the item.
     *
     * This will fade out the item, and then remove it from view.
     */
    remove: function() {
        this.$el.fadeOut('normal',
                         _.bind(Backbone.View.prototype.remove, this));
    },

    /*
     * Displays a spinner on the item.
     *
     * This can be used to show that the item is being loaded from the
     * server.
     */
    showSpinner: function() {
        if (this.$spinner) {
            return;
        }

        this.$spinner = $('<span/>')
            .addClass('config-forms-list-item-spinner')
            .appendTo(this.$spinnerParent)
            .hide()
            .css('visibility', 'visible')
            .fadeIn();
    },

    /*
     * Hides the currently visible spinner.
     */
    hideSpinner: function() {
        if (!this.$spinner) {
            return;
        }

        /*
         * The slow fadeout does two things:
         *
         * 1) It prevents the spinner from disappearing too quickly
         *    (in combination with the fadeIn above), in case the operation
         *    is really fast, giving some feedback that something actually
         *    happened.
         *
         * 2) By fading out, it doesn't look like it just simply stops.
         *    Helps provide a sense of completion.
         */
        this.$spinner.fadeOut('slow', _.bind(function() {
            this.$spinner.remove();
            this.$spinner = null;
        }, this));
    },

    /*
     * Adds all registered actions to the view.
     */
    addActions: function($parentEl) {
        _.each(this.model.actions, function(action) {
            var $action = this._buildActionEl(action)
                    .appendTo($parentEl);

            if (action.children) {
                if (action.label) {
                    $action.append(' &#9662;');
                }

                $action.click(_.bind(function() {
                    /*
                     * Show the dropdown after we let this event propagate.
                     */
                    _.defer(_.bind(this._showActionDropdown, this,
                                   action, $action));
                }, this));
            }
        }, this);

        this.$spinnerParent = $parentEl;
    },

    /*
     * Shows a dropdown for a menu action.
     */
    _showActionDropdown: function(action, $action) {
        var actionPos = $action.position(),
            $pane = $('<ul/>')
                .addClass('action-menu')
                .move(actionPos.left + $action.getExtents('m', 'l'),
                      actionPos.top + $action.outerHeight(),
                      'absolute')
                .click(function(e) {
                    /* Don't let a click on the dropdown close it. */
                    e.stopPropagation();
                });

        _.each(action.children, function(childAction) {
            $('<li/>')
                .append(this._buildActionEl(childAction))
                .appendTo($pane);
        }, this);

        $pane.appendTo($action.parent());

        /* Any click outside this dropdown should close it. */
        $(document).one('click', function() {
            $pane.remove();
        });
    },

    /*
     * Builds the element for an action.
     *
     * If the action's type is "checkbox", a checkbox will be shown. Otherwise,
     * the action will be shown as a button.
     */
    _buildActionEl: function(action) {
        var actionHandlerName = (action.enabled !== false
                                 ? this.actionHandlers[action.id]
                                 : null),
            checkboxID,
            $action,
            $result;

        if (action.type === 'checkbox') {
            checkboxID = _.uniqueId('action_check');
            $action = $('<input/>')
                .attr({
                    type: "checkbox",
                    id: checkboxID
                });

            $result = $('<span/>')
                .append($action)
                .append($('<label/>')
                    .attr('for', checkboxID)
                    .text(action.label));

            if (action.propName) {
                $action.bindProperty('checked', this.model, action.propName);
            }

            if (actionHandlerName) {
                $action.change(_.bind(this[actionHandlerName], this));
            }
        } else {
            $action = $result = $('<a class="btn"/>')
                .text(action.label || '');

            if (action.iconName) {
                $action.append($('<span/>')
                    .addClass(this.iconBaseClassName)
                    .addClass(this.iconBaseClassName + '-' + action.iconName));
            }

            if (actionHandlerName) {
                $action.click(_.bind(this[actionHandlerName], this));
            }
        }

        if (action.id) {
            $action.addClass('config-forms-list-action-' + action.id);
        }

        if (action.danger) {
            $action.addClass('danger');
        }

        if (action.enabled === false) {
            $action.attr('disabled', 'disabled');
            $result.addClass('disabled');
        }

        return $result;
    }
});
