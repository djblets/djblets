/**
 * View for managing the integration configurations list.
 */

import {
    type EventsHash,
    type Result,
    BaseView,
    spina,
} from '@beanbag/spina';

import {
    ConfigFormsList,
    ConfigFormsListItem,
    ConfigFormsListItems,
    ConfigFormsTableItemView,
    ConfigFormsTableView,
} from 'djblets/configForms';
import {
    type ListItemAttrs,
} from 'djblets/configForms/models/listItemModel';
import {
    type IntegrationOptions,
    AddIntegrationPopupView,
} from './addIntegrationPopupView';


/**
 * Attributes for the IntegrationConfigItem model.
 *
 * Version Added:
 *     6.0
 */
interface IntegrationConfigItemAttrs extends ListItemAttrs {
    /** The ID of the integration. */
    integrationID: string;

    /** The name of the integration. */
    name: string;
}


/**
 * List item for a configuration.
 *
 * This stores basic display, actions, and API information for the
 * configuration.
 */
@spina
class IntegrationConfigItem extends ConfigFormsListItem<
    IntegrationConfigItemAttrs
> {
    static defaults: Result<Partial<IntegrationConfigItemAttrs>> = {
        removeLabel: _`Delete`,
        showRemove: true,
    };

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
    url(): string {
        return this.get('editURL');
    }

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
    parse(
        data: {
            editURL: string;
            enabled: boolean;
            id: string;
            integrationID: string;
            name: string;
        },
    ): IntegrationConfigItemAttrs {
        return {
            editURL: data.editURL,
            id: data.id,
            integrationID: data.integrationID,
            itemState: data.enabled ? 'enabled' : 'disabled',
            name: data.name,
        };
    }
}


/**
 * View for displaying information and actions for a configuration.
 *
 * This renders some basic information on the state of the configuration,
 * and provides actions for deleting configurations.
 */
@spina
class IntegrationConfigItemView extends ConfigFormsTableItemView {
    static className =
        'djblets-c-integration-config djblets-c-config-forms-list__item';

    static actionHandlers: EventsHash = {
        'delete': '_onDeleteClicked',
    };

    static template = _.template(dedent`
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
    `);

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
    }

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
                title: _`Are you sure you want to delete this integration?`,
            });
    }
}


/**
 * Options for the IntegrationConfigListView.
 *
 * Version Added:
 *     6.0
 */
export interface IntegrationConfigListViewOptions {
    /** The set of existing integration configurations. */
    configs: IntegrationConfigItemAttrs[];

    /** An array of integration IDs, in display order. */
    integrationIDs: string[];

    /** A mapping of integration ID to information. */
    integrationsMap: Record<string, IntegrationOptions>;
}


/**
 * Options for the integration config collection.
 *
 * Version Added:
 *     6.0
 */
interface IntegrationConfigListItemsOptions {
    /** The CSRF token to include with form submissions. */
    csrfToken: string;

    /** A mapping of integration ID to information. */
    integrationsMap: Record<string, IntegrationOptions>;
}


/**
 * View for managing the integration configurations list.
 *
 * This handles events for the Add Integration button and the resulting popup.
 */
@spina
export class IntegrationConfigListView extends BaseView<
    undefined,
    HTMLDivElement,
    IntegrationConfigListViewOptions
> {
    static events: EventsHash = {
        'click .djblets-c-integration-configs__add':
            '_onAddIntegrationClicked',
    };

    /**********************
     * Instance variables *
     **********************/

    /** The list of integrations. */
    list: ConfigFormsList;

    /** The view for the list. */
    listView: ConfigFormsTableView;

    /** The container element that the list is in. */
    _$listContainer: JQuery;

    /** An array of integration Ids, in display order. */
    _integrationIDs: string[];

    /** A mapping of integration ID to information. */
    _integrationsMap: Record<number, IntegrationOptions>;

    /** The popup view. */
    _popup: AddIntegrationPopupView;

    /**
     * Initialize the view.
     *
     * Args:
     *     options (IntegrationConfigListViewOptions):
     *         Options for the view.
     */
    initialize(options: IntegrationConfigListViewOptions) {
        this._integrationIDs = options.integrationIDs;
        this._integrationsMap = options.integrationsMap;

        this.list = new ConfigFormsList(
            {},
            {
                collection: new ConfigFormsListItems<
                    IntegrationConfigItem,
                    IntegrationConfigListItemsOptions
                >(
                    options.configs,
                    {
                        csrfToken: options.csrfToken,
                        integrationsMap: options.integrationsMap,
                        model: IntegrationConfigItem,
                        parse: true,
                    }
                ),
            });

        this._popup = null;
    }

    /**
     * Render the view.
     */
    protected onInitialRender() {
        this.listView = new ConfigFormsTableView({
            ItemView: IntegrationConfigItemView,
            el: this.$('.djblets-c-config-forms-list'),
            model: this.list,
        });
        this.listView.render().$el
            .removeAttr('aria-busy');

        this._$listContainer = this.listView.$el.parent();

        this.listenTo(this.list.collection, 'add remove',
                      this._showOrHideConfigsList);
        this._showOrHideConfigsList();
    }

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
    }

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
    _onAddIntegrationClicked(e: Event) {
        e.preventDefault();
        e.stopPropagation();

        if (!this._popup) {
            const integrationIDs = this._integrationIDs;
            const integrationsMap = this._integrationsMap;
            const integrations = [];

            for (let i = 0; i < integrationIDs.length; i++) {
                integrations.push(integrationsMap[integrationIDs[i]]);
            }

            this._popup = new AddIntegrationPopupView({
                integrations: integrations,
            });
            this._popup.render().$el.appendTo(this.$el);
        }

        this._popup.show($(e.target as HTMLElement));
    }
}
