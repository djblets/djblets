/**
 * Display a list item for a config page.
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
    className: 'djblets-c-config-forms-list__item',
    iconBaseClassName: 'djblets-icon',

    /**
     * A mapping of item states to CSS classes.
     *
     * Subclasses can extend this to provide custom CSS classes, or support
     * custom item states.
     */
    itemStateClasses: {
        disabled: '-is-disabled',
        enabled: '-is-enabled',
        error: '-has-error',
    },

    actionHandlers: {},

    template: _.template(dedent`
        <% if (editURL) { %>
        <a href="<%- editURL %>"><%- text %></a>
        <% } else { %>
        <%- text %>
        <% } %>
    `),

    /**
     * Initialize the view.
     */
    initialize() {
        this.listenTo(this.model, 'actionsChanged', this.render);
        this.listenTo(this.model, 'request', this.showSpinner);
        this.listenTo(this.model, 'sync', this.hideSpinner);
        this.listenTo(this.model, 'destroy', this.remove);

        this.$spinnerParent = null;
        this.$spinner = null;
    },

    /**
     * Render the view.
     *
     * This will be called every time the list of actions change for
     * the item.
     *
     * Returns:
     *     Djblets.Config.ListItemView:
     *     This view.
     */
    render() {
        const model = this.model;

        this.$el
            .empty()
            .append(this.template(_.defaults(
                model.attributes,
                this.getRenderContext()
            )));

        this._$itemState =
            this.$('.djblets-c-config-forms-list__item-state');

        this.listenTo(model, 'change:itemState', this._onItemStateChanged);
        this._onItemStateChanged();

        this.addActions(this.getActionsParent());

        return this;
    },

    /**
     * Return additional render context.
     *
     * By default this returns an empty object. Subclasses can use this to
     * provide additional values to :js:attr:`template` when it is rendered.
     *
     * Returns:
     *     object:
     *     Additional rendering context for the template.
     */
    getRenderContext() {
        return {};
    },

    /**
     * Remove the item.
     *
     * This will fade out the item, and then remove it from view.
     */
    remove() {
        this.$el.fadeOut('normal',
                         () => Backbone.View.prototype.remove.call(this));
    },

    /**
     * Return the container for the actions.
     *
     * This defaults to being this element, but it can be overridden to
     * return a more specific element.
     *
     * Returns:
     *     jQuery:
     *     The container for the actions.
     */
    getActionsParent() {
        return this.$el;
    },

    /**
     * Display a spinner on the item.
     *
     * This can be used to show that the item is being loaded from the
     * server.
     */
    showSpinner() {
        if (this.$spinner) {
            return;
        }

        this.$el.attr('aria-busy', 'true');
        this.$spinner = $('<span>')
            .addClass('djblets-o-spinner')
            .attr('aria-hidden', 'true')
            .prependTo(this.$spinnerParent)
            .hide()
            .css('visibility', 'visible')
            .fadeIn();
    },

    /**
     * Hide the currently visible spinner.
     */
    hideSpinner() {
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
        this.$spinner.fadeOut('slow', () => {
            this.$spinner.remove();
            this.$spinner = null;
        });

        this.$el.removeAttr('aria-busy');
    },

    /**
     * Add all registered actions to the view.
     *
     * Args:
     *     $parentEl (jQuery):
     *         The parent element to add the actions to.
     */
    addActions($parentEl) {
        const $actions = $('<span>')
            .addClass('djblets-c-config-forms-list__item-actions');

        this.model.actions.forEach(action => {
            const $action = this._buildActionEl(action)
                .appendTo($actions);

            if (action.children) {
                if (action.label) {
                    $action.append(' &#9662;');
                }

                /*
                 * Show the dropdown after we let this event propagate.
                 */
                $action.click(() => _.defer(
                    () => this._showActionDropdown(action, $action)
                ));
            }
        });

        this.$spinnerParent = $actions;

        $actions.prependTo($parentEl);
    },

    /**
     * Show a dropdown for a menu action.
     *
     * Args:
     *     action (object):
     *         The action to show the dropdown for. See
     *         :js:class:`Djblets.Config.ListItem`. for a list of attributes.
     *
     *     $action (jQuery):
     *         The element that represents the action.
     */
    _showActionDropdown(action, $action) {
        const actionPos = $action.position();
        const $menu = $('<div/>')
            .css({
                minWidth: $action.outerWidth(),
                position: 'absolute',
            })
            .addClass('djblets-c-config-forms-popup-menu')
            .click(e => e.stopPropagation());
        const $items = $('<ul/>')
            .addClass('djblets-c-config-forms-popup-menu__items')
            .appendTo($menu);
        const actionLeft = actionPos.left + $action.getExtents('m', 'l');

        action.children.forEach(
            childAction => $('<li/>')
                .addClass('djblets-c-config-forms-popup-menu__item ' +
                          `config-forms-list-action-row-${childAction.id}`)
                .append(this._buildActionEl(childAction))
                .appendTo($items)
        );

        this.trigger('actionMenuPopUp', {
            action: action,
            $action: $action,
            $menu: $menu,
        });

        $menu.appendTo($action.parent());

        const winWidth = $(window).width();
        const paneWidth = $menu.width();

        $menu.move(($action.offset().left + paneWidth > winWidth
                    ? actionLeft + $action.innerWidth() - paneWidth
                    : actionLeft),
                   actionPos.top + $action.outerHeight(),
                   'absolute');

        /* Any click outside this dropdown should close it. */
        $(document).one('click', () => {
            this.trigger('actionMenuPopDown', {
                action: action,
                $action: $action,
                $menu: $menu,
            });

            $menu.remove();
        });
    },

    /**
     * Build the element for an action.
     *
     * If the action's type is ``'checkbox'``, a checkbox will be shown.
     * Otherwise, the action will be shown as a button.
     *
     * Args:
     *     action (object):
     *         The action to show the dropdown for. See
     *         :js:class:`Djblets.Config.ListItem` for a list of attributes.
     */
    _buildActionEl(action) {
        const enabled = (action.enabled !== false);
        const actionHandlerName = (enabled
                                   ? this.actionHandlers[action.id]
                                   : null);
        const isCheckbox = (action.type === 'checkbox');
        const isRadio = (action.type === 'radio');

        let $action;
        let $result;

        if (isCheckbox || isRadio) {
            const inputID = _.uniqueId('action_' + action.type);
            $action = $('<input/>')
                .attr({
                    name: action.name,
                    type: action.type,
                    id: inputID
                });
            const $label = $('<label>')
                .attr('for', inputID)
                .text(action.label);

            if (action.id) {
                $label.addClass(`config-forms-list-action-label-${action.id}`);
            }

            $result = $('<span/>')
                .append($action)
                .append($label);

            if (action.propName) {
                if (isCheckbox) {
                    $action.bindProperty('checked', this.model,
                                         action.propName);
                } else if (isRadio) {
                    $action.bindProperty(
                        'checked', this.model, action.propName, {
                            radioValue: action.radioValue
                        }
                    );
                }
            }

            if (action.enabledPropName) {
                $action.bindProperty(
                    'disabled', this.model, action.enabledPropName,
                    {
                        inverse: (action.enabledPropInverse !== true)
                    });
            }

            if (actionHandlerName) {
                const actionHandler = _.debounce(
                    _.bind(this[actionHandlerName], this),
                    50,
                    true
                );

                $action.change(actionHandler);

                if (isRadio && action.dispatchOnClick) {
                    $action.click(actionHandler);
                }
            }
        } else {
            if (action.url) {
                $action = $('<a class="btn" role="button">')
                    .attr('href', action.url);
            } else {
                $action = $('<button type="button">');
            }

            $result = $action;

            if (action.label) {
                $action.text(action.label);
            }

            if (action.ariaLabel) {
                $action.attr('aria-label', action.ariaLabel);
            }

            if (action.iconName) {
                $action.prepend($('<span>')
                    .addClass(this.iconBaseClassName)
                    .addClass(`${this.iconBaseClassName}-${action.iconName}`));
            }

            if (actionHandlerName) {
                $action.click(evt => {
                    evt.preventDefault();
                    evt.stopPropagation();

                    this._onActionButtonClicked(evt, actionHandlerName,
                                                $action);
                });
            }
        }

        $action.addClass('djblets-c-config-forms-list__item-action');

        if (action.id) {
            $action.addClass(`config-forms-list-action-${action.id}`);
        }

        if (action.danger) {
            $action.addClass('-is-danger');
        }

        if (action.primary) {
            $action.addClass('-is-primary');
        }

        if (!enabled) {
            $action.prop('disabled', true);
        }

        return $result;
    },

    /**
     * Handle changes to the item state.
     *
     * This will update the CSS class used on the item and any relevant text
     * contained within the item to reflect the current state.
     */
    _onItemStateChanged() {
        const model = this.model;
        const oldItemState = model.previous('itemState');
        const itemState = model.get('itemState');

        if (oldItemState) {
            this.$el.removeClass(this.itemStateClasses[oldItemState]);
        }

        if (itemState) {
            this.$el.addClass(this.itemStateClasses[itemState]);

            /*
             * Note that if we didn't find an element in the template for
             * this before, this is basically a no-op.
             */
            this._$itemState.text(model.itemStateTexts[itemState]);
        }
    },

    /**
     * Handle clicks on a list item action button.
     *
     * This will invoke the click handler on the view. If that handler
     * returns a Promise, this will disable the button, replace its contents
     * with a spinner, and then wait for the promise to resolve before
     * setting the button's contents and enabled states back to normal.
     *
     * Args:
     *     evt (jQuery.Event):
     *         The click event on the button.
     *
     *     actionHandlerName (string):
     *         The name of the action handler function to call.
     *
     *     $action (jQuery):
     *         The action button that was clicked.
     */
    _onActionButtonClicked(evt, actionHandlerName, $action) {
        const promise = this[actionHandlerName].call(this, evt);

        if (promise && typeof promise.then === 'function') {
            $action.prop('disabled', true);

            const childrenHTML = $action.html();
            $action.empty();

            const $spinner = $('<span class="djblets-o-spinner">')
                .appendTo($action);

            /*
             * This is a promise, so there's an async operation
             * going on. Set up the spinner.
             */
            promise.finally(() => {
                $spinner.remove();
                $action.html(childrenHTML);
                $action.prop('disabled', false);
            });
        }
    },
});
