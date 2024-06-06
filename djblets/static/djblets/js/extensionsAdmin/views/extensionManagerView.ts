/**
 * Displays the interface showing all installed extensions.
 */

import {
    type EventsHash,
    BaseView,
    spina,
} from '@beanbag/spina';
import _ from 'underscore';

import {
    ConfigFormsList,
    ConfigFormsListItem,
    ConfigFormsListItems,
    ConfigFormsTableItemView,
    ConfigFormsTableView,
} from 'djblets/configForms';
import {
    type ListItemAttrs,
    type ListItemConstructorAttrs,
} from 'djblets/configForms/models/listItemModel';
import { type Extension } from 'djblets/extensions';

import { type ExtensionManager } from '../models/extensionManagerModel';


/**
 * Attributes for the ExtensionItem model.
 *
 * Version Added:
 *     5.0
 */
interface ExtensionItemAttrs extends ListItemAttrs {
    extension: Extension | null;
}


/**
 * An item in the list of registered extensions.
 *
 * This will contain information on the extension and actions for toggling
 * the enabled state, reloading the extension, or configuring the extension.
 */
@spina
class ExtensionItem extends ConfigFormsListItem<ExtensionItemAttrs> {
    static defaults: ExtensionItemAttrs = {
        extension: null,
    };

    /**
     * Initialize the item.
     *
     * This will set up the initial state and then listen for any changes
     * to the extension's state (caused by enabling/disabling/reloading the
     * extension).
     *
     * Args:
     *     attributes (ListItemConstructorAttrs, optional):
     *         Attributes for the model.
     */
    initialize(attributes: ListItemConstructorAttrs = {}) {
        super.initialize(attributes);

        this.#updateActions();
        this.#updateItemState();

        this.listenTo(
            this.get('extension'),
            'change:loadable change:loadError change:enabled',
            () => {
                this.#updateItemState();
                this.#updateActions();
            });
    }

    /**
     * Update the actions for the extension.
     *
     * If the extension is disabled, this will add an Enabled action.
     *
     * If it's enabled, but has a load error, it will add a Reload action.
     *
     * If it's enabled, it will provide actions for Configure and Database,
     * if enabled by the extension, along with a Disable action.
     */
    #updateActions() {
        const extension = this.get('extension');
        const actions = [];

        if (!extension.get('loadable')) {
            /* Add an action for reloading the extension. */
            actions.push({
                id: 'reload',
                label: _`Reload`,
            });
        } else if (extension.get('enabled')) {
            /*
             * Show all the actions for enabled extensions.
             *
             * Note that the order used is here to ensure visual alignment
             * for most-frequently-used options.
             */
            const configURL = extension.get('configURL');
            const dbURL = extension.get('dbURL');

            if (dbURL) {
                actions.push({
                    id: 'database',
                    label: _`Database`,
                    url: dbURL,
                });
            }

            if (configURL) {
                actions.push({
                    id: 'configure',
                    label: _`Configure`,
                    primary: true,
                    url: configURL,
                });
            }

            actions.push({
                danger: true,
                id: 'disable',
                label: _`Disable`,
            });
        } else {
            /* Add an action for enabling a disabled extension. */
            actions.push({
                id: 'enable',
                label: _`Enable`,
                primary: true,
            });
        }

        this.setActions(actions);
    }

    /**
     * Update the state of this item.
     *
     * This will set the "error", "enabled", or "disabled" state of the
     * item, depending on the corresponding state in the extension.
     */
    #updateItemState() {
        const extension = this.get('extension');
        let itemState: string;

        if (!extension.get('loadable')) {
            itemState = 'error';
        } else if (extension.get('enabled')) {
            itemState = 'enabled';
        } else {
            itemState = 'disabled';
        }

        this.set('itemState', itemState);
    }
}


/**
 * Displays an extension in the Manage Extensions list.
 *
 * This will show information about the extension, and provide links for
 * enabling/disabling the extension, and (depending on the extension's
 * capabilities) configuring it or viewing its database.
 */
@spina
class ExtensionItemView extends ConfigFormsTableItemView {
    static className =
        'djblets-c-extension-item djblets-c-config-forms-list__item';

    static actionHandlers: EventsHash = {
        'disable': '_onDisableClicked',
        'enable': '_onEnableClicked',
        'reload': '_onReloadClicked',
    };

    static template = _.template(dedent`
        <td class="djblets-c-config-forms-list__item-main">
         <div class="djblets-c-extension-item__header">
          <h3 class="djblets-c-extension-item__name"><%- name %></h3>
          <span class="djblets-c-extension-item__version"><%- version %></span>
          <div class="djblets-c-extension-item__author">
           <% if (authorURL) { %>
            <a href="<%- authorURL %>"><%- author %></a>
           <% } else { %>
            <%- author %>
           <% } %>
          </div>
         </div>
         <p class="djblets-c-extension-item__description">
          <%- summary %>
         </p>
         <% if (!loadable) { %>
          <pre class="djblets-c-extension-item__load-error"><%-
            loadError %></pre>
         <% } %>
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
        return this.model.get('extension').attributes;
    }

    /**
     * Handle a click on the Disable action.
     *
     * This will make an asynchronous request to disable the extension.
     *
     * Returns:
     *     Promise:
     *     A promise for the disable request. This will resolve once the
     *     API has handled the request.
     */
    _onDisableClicked() {
        return this.model.get('extension').disable()
            .catch(error => {
                alert(_`Failed to disable the extension: ${error.message}.`);
            });
    }

    /**
     * Handle a click on the Enable action.
     *
     * This will make an asynchronous request to enable the extension.
     *
     * Returns:
     *     Promise:
     *     A promise for the enable request. This will resolve once the
     *     API has handled the request.
     */
    _onEnableClicked() {
        return this.model.get('extension').enable()
            .catch(error => {
                alert(_`Failed to enable the extension: ${error.message}.`);
            });
    }

    /**
     * Handle a click on the Reload action.
     *
     * This will trigger an event on the item that tells the extension
     * manager to perform a full reload of all extensions, this one included.
     *
     * Returns:
     *     Promise:
     *     A promise for the enable request. This will never resolve, in
     *     practice, but is returned to enable the action's spinner until
     *     the page reloads.
     */
    _onReloadClicked() {
        return new Promise(() => this.model.trigger('needsReload'));
    }
}


/**
 * Displays the interface showing all installed extensions.
 *
 * This loads the list of installed extensions and displays each in a list.
 */
@spina
export class ExtensionManagerView extends BaseView<
    ExtensionManager,
    HTMLFormElement
> {
    static events: EventsHash = {
        'click .djblets-c-extensions__reload': '_reloadFull',
    };

    /**********************
     * Instance variables *
     **********************/

    /** The extension list model. */
    list: ConfigFormsList;

    /** The extension list view. */
    listView: ConfigFormsTableView;

    /**
     * Initialize the view.
     */
    initialize() {
        this.list = new ConfigFormsList(
            {},
            {
                collection: new ConfigFormsListItems(
                    [],
                    {
                        model: ExtensionItem,
                    }),
            });
    }

    /**
     * Render the view.
     */
    protected onInitialRender() {
        const model = this.model;
        const list = this.list;

        this.listView = new ConfigFormsTableView({
            ItemView: ExtensionItemView,
            el: this.$('.djblets-c-config-forms-list'),
            model: list,
        });
        this.listView.render().$el
            .removeAttr('aria-busy')
            .addClass('-all-items-are-multiline');

        this.listenTo(model, 'loading', () => list.collection.reset());
        this.listenTo(model, 'loaded', this._onLoaded);
        model.load();
    }

    /**
     * Handler for when the list of extensions is loaded.
     *
     * Renders each extension in the list. If the list is empty, this will
     * display that there are no extensions installed.
     */
    _onLoaded() {
        const items = this.list.collection;

        this.model.installedExtensions.each(extension => {
            const item = items.add({
                extension: extension,
            });

            this.listenTo(item, 'needsReload', this._reloadFull);
        });
    }

    /**
     * Perform a full reload of the list of extensions on the server.
     *
     * This submits our form, which is set in the template to tell the
     * ExtensionManager to do a full reload.
     */
    _reloadFull() {
        this.el.submit();
    }
}
