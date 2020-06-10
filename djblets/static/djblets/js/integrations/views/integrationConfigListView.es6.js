(function() {


/**
 * List item for a configuration.
 *
 * This stores basic display, actions, and API information for the
 * configuration.
 */
const IntegrationConfigItem = Djblets.Config.ListItem.extend({
    defaults: _.defaults({
        removeLabel: _`Delete`,
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

    /**
     * Return the attributes for this item from a provided payload.
     *
     * Args:
     *     data (object):
     *         The data for this item provided when constructing the
     *         integrations page.
     *
     * Returns:
     *     object:
     *     The new attribute data from the item.
     */
    parse(data) {
        return {
            editURL: data.editURL,
            id: data.id,
            integrationID: data.integrationID,
            itemState: data.enabled ? 'enabled' : 'disabled',
            name: data.name,
        };
    },
});


/**
 * View for displaying information and actions for a configuration.
 *
 * This renders some basic information on the state of the configuration,
 * and provides actions for deleting configurations.
 */
const IntegrationConfigItemView = Djblets.Config.TableItemView.extend({
    className:
        'djblets-c-integration-config djblets-c-config-forms-list__item',

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
        <td class="djblets-c-config-forms-list__item-state"></td>
        <td></td>
    `),

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
            .text(_`
                This integration will be permanently removed. This cannot
                be undone.
            `)
            .modalBox({
                title: _`Are you sure you want to delete this integration?`,
                buttons: [
                    $('<button>')
                        .text(_`Cancel`),
                    $('<button class="danger">')
                        .text(_`Delete Integration`)
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

    addIntegrationPopupViewType: Djblets.AddIntegrationPopupView,
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
                        parse: true,
                    }
                ),
            });

        this._popup = null;
    },

    /**
     * Render the view.
     *
     * Returns:
     *     Djblets.IntegrationConfigListView:
     *     This view, for chaining.
     */
    render() {
        this.listView = new this.listViewType({
            el: this.$('.djblets-c-config-forms-list'),
            model: this.list,
            ItemView: this.listItemViewType,
        });
        this.listView.render().$el
            .removeAttr('aria-busy');

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

        if (!this._popup) {
            const integrationIDs = this._integrationIDs;
            const integrationsMap = this._integrationsMap;
            const integrations = [];

            for (let i = 0; i < integrationIDs.length; i++) {
                integrations.push(integrationsMap[integrationIDs[i]]);
            }

            this._popup = new this.addIntegrationPopupViewType({
                integrations: integrations,
            });
            this._popup.render().$el.appendTo(this.$el);
        }

        this._popup.show($(e.target));
    },
});


})();
