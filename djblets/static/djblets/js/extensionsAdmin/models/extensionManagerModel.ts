/**
 * Extension management support.
 */

import {
    type ModelAttributes,
    BaseCollection,
    BaseModel,
    spina,
} from '@beanbag/spina';
import * as Backbone from 'backbone';
import * as _ from 'underscore';


/**
 * Attributes for information on an installed extension.
 *
 * Version Added:
 *     4.0
 */
interface InstalledExtensionAttrs extends ModelAttributes {
    /**
     * The name of the author writing/maintaining the extension.
     */
    author: string;

    /**
     * The URL to the author's website.
     */
    authorURL: string;

    /**
     * The URL on Review Board for configuring the extension.
     */
    configURL: string;

    /**
     * The URL to the extension's database management page.
     */
    dbURL: string;

    /**
     * Whether the extension is currently enabled.
     */
    enabled: boolean;

    /**
     * An error message encountered when trying to load the extension.
     */
    loadError: string;

    /**
     * Whether the extension can be loaded.
     */
    loadable: boolean;

    /**
     * The display name of the extension.
     */
    name: string;

    /**
     * A short summary describing the extension.
     */
    summary: string;

    /**
     * The version of the extension.
     */
    version: string;
}


/**
 * Attributes for controlling the extension manager.
 *
 * Version Added:
 *     4.0
 */
interface ExtensionManagerAttrs extends ModelAttributes {
    /**
     * The root of the extension API.
     */
    apiRoot: string;
}


/**
 * Represents an installed extension listed in the Manage Extensions list.
 *
 * This stores the various information about the extension that we'll display
 * to the user, and offers actions for enabling or disabling the extension.
 */
@spina
class InstalledExtension extends BaseModel<InstalledExtensionAttrs> {
    static defaults: InstalledExtensionAttrs = {
        author: null,
        authorURL: null,
        configURL: null,
        dbURL: null,
        enabled: false,
        loadError: null,
        loadable: true,
        name: null,
        summary: null,
        version: null,
    };

    /**
     * Enable the extension.
     *
     * This will submit a request to the server to enable this extension.
     *
     * Returns:
     *     Promise:
     *     A promise that will be resolved when the request to enable the
     *     extension completes.
     */
    enable(): Promise<void> {
        return new Promise((resolve, reject) => {
            this.save({
                enabled: true,
            }, {
                wait: true,

                error: (model, xhr) => {
                    this.set({
                        canEnable: !xhr.errorRsp.needs_reload,
                        loadError: xhr.errorRsp.load_error,
                        loadable: false,
                    });

                    reject(new Error(xhr.errorText));
                },
                success: () => resolve(),
            });
        });
    }

    /**
     * Disable the extension.
     *
     * This will submit a request to the server to disable this extension.
     *
     * Returns:
     *     Promise:
     *     A promise that will be resolved when the request to enable the
     *     extension completes.
     */
    disable(): Promise<void> {
        return new Promise((resolve, reject) => {
            this.save({
                enabled: false,
            }, {
                wait: true,

                error: xhr => reject(new Error(xhr.errorText)),
                success: () => resolve(),
            });
        });
    }

    /**
     * Return a JSON payload for requests sent to the server.
     *
     * Returns:
     *     object:
     *     A payload that will be serialized for making the API request.
     */
    toJSON(): object {
        return {
            enabled: this.get('enabled'),
        };
    }

    /**
     * Parse a JSON payload from the server.
     *
     * Args:
     *     rsp (object):
     *         The payload from the server.
     *
     * Returns:
     *     object:
     *     The parsed response.
     */
    parse(rsp) {
        if (rsp.stat !== undefined) {
            rsp = rsp.extension;
        }

        const id = rsp.class_name;
        const configLink = rsp.links['admin-configure'];
        const dbLink = rsp.links['admin-database'];

        this.url = `${this.collection.url}${id}/`;

        return {
            author: rsp.author,
            authorURL: rsp.author_url,
            canDisable: rsp.can_disable,
            canEnable: rsp.can_enable,
            configURL: configLink ? configLink.href : null,
            dbURL: dbLink ? dbLink.href : null,
            enabled: rsp.enabled,
            id: id,
            loadError: rsp.load_error,
            loadable: rsp.loadable,
            name: rsp.name,
            summary: rsp.summary,
            version: rsp.version,
        };
    }

    /**
     * Perform AJAX requests against the server-side API.
     *
     * Args:
     *     method (string):
     *         The HTTP method to use.
     *
     *     model (InstalledExtension):
     *         The extension object being synced.
     *
     *     options (object):
     *         Options for the sync operation.
     */
    sync(
        method: string,
        model: InstalledExtension,
        options?: JQuery.AjaxSettings,
    ): JQueryXHR {
        return Backbone.sync.call(this, method, model, _.defaults({
            contentType: 'application/x-www-form-urlencoded',
            data: model.toJSON(),
            processData: true,

            error: (xhr, textStatus, errorThrown) => {
                let rsp;
                let text;

                try {
                    rsp = $.parseJSON(xhr.responseText);
                    text = rsp.err.msg;
                } catch (e) {
                    text = 'HTTP ' + xhr.status + ' ' + xhr.statusText;
                    rsp = {
                        canEnable: false,
                        loadError: text,
                    };
                }

                if (_.isFunction(options.error)) {
                    xhr.errorText = text;
                    xhr.errorRsp = rsp;
                    options.error(xhr, textStatus, errorThrown);
                }
            },
        }, options));
    }
}


/**
 * A collection of installed extensions.
 *
 * This stores the list of installed extensions, and allows fetching from
 * the API.
 */
@spina
class InstalledExtensionCollection extends BaseCollection {
    static model = InstalledExtension;

    /**
     * Parse the response from the server.
     *
     * Args:
     *     rsp (object):
     *         The response from the server.
     *
     * Returns:
     *     object:
     *     The parsed data from the response.
     */
    parse(rsp) {
        return rsp.extensions;
    }
}


/**
 * Manages installed extensions.
 *
 * This stores a collection of installed extensions, and provides
 * functionality for loading the current list from the server.
 */
@spina
export class ExtensionManager extends BaseModel<ExtensionManagerAttrs> {
    static defaults: ExtensionManagerAttrs = {
        apiRoot: null,
    };

    /**********************
     * Instance variables *
     **********************/

    /**
     * A collection of all installed extensions.
     */
    installedExtensions: InstalledExtensionCollection;

    /**
     * Initialize the manager.
     */
    initialize() {
        this.installedExtensions = new InstalledExtensionCollection();
        this.installedExtensions.url = this.get('apiRoot');
    }

    /**
     * Load the extensions list.
     */
    load() {
        this.trigger('loading');

        this.installedExtensions.fetch({
            success: () => this.trigger('loaded'),
        });
    }
}
