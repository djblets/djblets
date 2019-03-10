(function() {


/**
 * List item for a configuration.
 *
 * This stores basic display, actions, and API information for the
 * configuration.
 */
const IntegrationConfigItem = Djblets.Config.ListItem.extend({
    defaults: _.defaults({
        disabledText: gettext('Disabled'),
        enabledText: gettext('Enabled'),
        integrationID: null,
        enabled: false,
        name: null,
        removeLabel: gettext('Delete'),
        showRemove: true,
    }, Djblets.Config.ListItem.prototype.defaults),

    /**
     * Return the API URL for the item.
     *
     * This is the same as the ``editURL`` attribute, and is used to
     * perform HTTP DELETE requests.
     *
     * Returns:
     *     string:
     *     The URL to perform API operations on.
     */
    url() {
        return this.get('editURL');
    },
});


/**
 * View for displaying information and actions for a configuration.
 *
 * This renders some basic information on the state of the configuration,
 * and provides actions for deleting configurations.
 */
const IntegrationConfigItemView = Djblets.Config.TableItemView.extend({
    actionHandlers: {
        'delete': '_onDeleteClicked',
    },

    template: _.template(dedent`
        <td class="djblets-c-integration-config__name">
         <img src="<%- iconSrc %>"
              srcset="<%- iconSrcSet %>"
              width="32" height="32" alt="">
         <a href="<%- editURL %>"><%- name %></a>
        </td>
        <td class="djblets-c-integration-config__integration-name">
         <%- integrationName %>
        </td>
        <td class="djblets-c-integration-config__status">
         <% if (enabled) { %>
          <span class="fa fa-check"></span> <%- enabledText %>
         <% } else { %>
          <span class="fa fa-close"></span> <%- disabledText %>
         <% } %>
        </td>
        <td></td>
    `),

    _baseClassName:
        'djblets-c-integration-config djblets-c-config-forms-list__item ',

    /**
     * Return the CSS class name of the item.
     *
     * Returns:
     *     string:
     *     The CSS class name.
     */
    className() {
        return this._baseClassName +
               (this.model.get('enabled') ? '-is-enabled' : '-is-disabled');
    },

    /**
     * Return context data for rendering the item's template.
     *
     * Returns:
     *     object:
     *     Context data for the render.
     */
    getRenderContext() {
        const integrationID = this.model.get('integrationID');
        const integration =
            this.model.collection.options.integrationsMap[integrationID];

        return {
            iconSrc: integration.iconSrc,
            iconSrcSet: integration.iconSrcSet,
            integrationName: integration.name,
        };
    },

    /**
     * Handle the Delete action on the item.
     *
     * This will display a confirmation dialog, and then send an HTTP DELETE
     * to remove the configuration.
     */
    _onDeleteClicked() {
        $('<p>')
            .html(gettext('This integration will be permanently removed. This cannot be undone.'))
            .modalBox({
                title: gettext('Are you sure you want to delete this integration?'),
                buttons: [
                    $('<input type="button">')
                        .val(gettext('Cancel')),
                    $('<input type="button" class="danger">')
                        .val(gettext('Delete Integration'))
                        .click(() => this.model.destroy({
                            beforeSend: xhr => {
                                xhr.setRequestHeader(
                                    'X-CSRFToken',
                                    this.model.collection.options.csrfToken);
                            },
                        })),
                ],
            });
    },
});


/**
 * View for managing the integration configurations list.
 *
 * This handles events for the Add Integration button and the resulting popup.
 */
Djblets.IntegrationConfigListView = Backbone.View.extend({
    events: {
        'click .djblets-c-integration-configs__add': '_onAddIntegrationClicked',
    },

    listItemsCollectionType: Djblets.Config.ListItems,
    listItemType: IntegrationConfigItem,
    listViewType: Djblets.Config.TableView,
    listItemViewType: IntegrationConfigItemView,

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         Options for the view.
     *
     * Option Args:
     *     configs (Array):
     *         An array of data on the configurations, in display order.
     *
     *     integrationIDs (Array):
     *         An array of integration IDs, in display order.
     *
     *     integrationsMap (object):
     *         A mapping of integration ID to information.
     */
    initialize(options) {
        this._integrationIDs = options.integrationIDs;
        this._integrationsMap = options.integrationsMap;

        this.list = new Djblets.Config.List(
            {},
            {
                collection: new this.listItemsCollectionType(
                    options.configs,
                    {
                        csrfToken: options.csrfToken,
                        integrationsMap: options.integrationsMap,
                        model: this.listItemType,
                    }
                ),
            });
    },

    /**
     * Render the view.
     *
     * Returns:
     *     Djblets.IntegrationConfigListView:
     *     This view, for chaining.
     */
    render() {
        this._$popup = this.$('.djblets-c-integrations-popup');

        this.listView = new this.listViewType({
            el: this.$('.djblets-c-config-forms-list'),
            model: this.list,
            ItemView: this.listItemViewType,
        });
        this.listView.render();

        this._$listContainer = this.listView.$el.parent();

        this.listenTo(this.list.collection, 'add remove',
                      this._showOrHideConfigsList);
        this._showOrHideConfigsList();

        return this;
    },

    /**
     * Show or hide the list of configurations.
     *
     * This will show the list's container if there's at least one item to
     * show, or hide it if the list is empty.
     */
    _showOrHideConfigsList() {
        if (this.list.collection.length > 0) {
            this._$listContainer.show();
        } else {
            this._$listContainer.hide();
        }
    },

    /**
     * Hide the integrations list popup.
     *
     * This will hide the popup from the screen and disconnect all related
     * events.
     */
    _hidePopup() {
        this._$popup.hide();

        $(document).off('click.djblets-integrations-popup');
        $(window).off('resize.djblets-integrations-popup');
    },

    /**
     * Handler for the Add Integration button.
     *
     * This will show the integrations list popup, allowing the user to choose
     * an integration to add.
     *
     * The logic for showing the popup will align the popup with the left-hand
     * side of the Add Integration button, and set the width to the maximum
     * amount that will cleanly fit a row of tiles without obscuring any part
     * of a tile or leaving extra space after a tile.
     *
     * Args:
     *     e (jQuery.Event):
     *         The click event.
     */
    _onAddIntegrationClicked(e) {
        e.preventDefault();
        e.stopPropagation();

        const $window = $(window);
        const $popup = this._$popup;
        const popupEl = $popup[0];
        const $button = $(e.target);
        const buttonPos = $button.position();

        /*
         * First, position the popup and set it to a small size to trigger
         * scrolling behavior, so we can perform calculations. It does need
         * to be big enough to fit the scrollbar, though, hence the width.
         */
        $popup
            .move(buttonPos.left,
                  buttonPos.top + $button.outerHeight(),
                  'absolute')
            .width(100)
            .height(1)
            .show();

        const popupBorderWidths = $popup.getExtents('b', 'lr');
        const scrollbarWidth = popupEl.offsetWidth - popupEl.clientWidth -
                               popupBorderWidths;

        const popupOffset = $popup.offset();
        const popupHeight = Math.floor(
            $window.height() - popupOffset.top -
            $popup.getExtents('bm', 'tb'));

        /*
         * Set the new width and height.
         *
         * We're resetting the height back to "auto" so it's not forced to be
         * too big, but cap around the screen boundary so it can't grow too
         * large.
         */
        $popup.css({
            'height': 'auto',
            'max-height': popupHeight,
        });

        if ($popup.hasClass('-is-empty')) {
            $popup.css('width', 'auto');
        } else {
            /*
             * Get the width of one of the integration tiles in the popup, so
             * we can start to figure out how many we can fit on screen.
             */
            const tileWidth = $popup
                .find('.djblets-c-integration')
                .filter(':first')
                .outerWidth(true);
            const winWidth = $window.width();
            const availWidth = winWidth - popupOffset.left - scrollbarWidth -
                               $popup.getExtents('m', 'r');

            let popupWidth = Math.max(Math.floor(availWidth / tileWidth), 1) *
                             tileWidth + scrollbarWidth + popupBorderWidths;

            $popup.outerWidth(popupWidth);

            /*
             * Now that we have a width and height set, we might not actually
             * be showing a scrollbar anymore. Find out how much extra space we
             * now have here, and if it's not what we had before for the scroll
             * bar, we can strip that out.
             */
            const newScrollbarWidth = popupEl.offsetWidth -
                                      popupEl.clientWidth -
                                      popupBorderWidths;

            if (newScrollbarWidth === 0) {
                popupWidth -= scrollbarWidth;
                $popup.outerWidth(popupWidth);
            }

            /*
             * If the menu is off-screen (which might be due to a very small
             * screen width), we'll need to shift the popup over a bit.
             */
            if (popupOffset.left + popupWidth > winWidth) {
                $popup.css('left', winWidth - popupWidth);
            }
        }

        /*
         * Wire up events to hide the popup when the document is clicked or
         * the window resized.
         */
        $(document).one('click.djblets-integrations-popup',
                        () => this._hidePopup());
        $(window).one('resize.djblets-integrations-popup',
                      () => this._hidePopup());
    },
});


})();
