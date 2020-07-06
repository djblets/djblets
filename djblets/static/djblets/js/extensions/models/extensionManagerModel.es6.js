(function() {


/**
 * Represents an installed extension listed in the Manage Extensions list.
 *
 * This stores the various information about the extension that we'll display
 * to the user, and offers actions for enabling or disabling the extension.
 */
const InstalledExtension = Backbone.Model.extend({
    defaults: {
        author: null,
        authorURL: null,
        configURL: null,
        dbURL: null,
        enabled: false,
        loadable: true,
        loadError: null,
        name: null,
        summary: null,
        version: null,
    },

    /**
     * Return the URL to the API endpoint representing this extension.
     *
     * Returns:
     *     string:
     *     The URL to use for making changes to this extension.
     */
    url() {
        return Backbone.Model.prototype.url.call(this) + '/';
    },

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
    enable() {
        return new Promise((resolve, reject) => {
            this.save({
                enabled: true
            }, {
                wait: true,
                success: () => resolve(),
                error: (model, xhr) => {
                    this.set({
                        loadable: false,
                        loadError: xhr.errorRsp.load_error,
                        canEnable: !xhr.errorRsp.needs_reload,
                    });

                    reject(new Error(xhr.errorText));
                },
            });
        });
    },

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
    disable() {
        return new Promise((resolve, reject) => {
            this.save({
                enabled: false,
            }, {
                wait: true,
                success: () => resolve(),
                error: xhr => reject(new Error(xhr.errorText)),
            });
        });
    },

    /**
     * Return a JSON payload for requests sent to the server.
     *
     * Returns:
     *     object:
     *     A payload that will be serialized for making the API request.
     */
    toJSON() {
        return {
            enabled: this.get('enabled'),
        };
    },

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

        const configLink = rsp.links['admin-configure'];
        const dbLink = rsp.links['admin-database'];

        return {
            author: rsp.author,
            authorURL: rsp.author_url,
            canDisable: rsp.can_disable,
            canEnable: rsp.can_enable,
            configURL: configLink ? configLink.href : null,
            dbURL: dbLink ? dbLink.href : null,
            enabled: rsp.enabled,
            loadable: rsp.loadable,
            loadError: rsp.load_error,
            id: rsp.class_name,
            name: rsp.name,
            summary: rsp.summary,
            version: rsp.version,
        };
    },

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
    sync(method, model, options) {
        Backbone.sync.call(this, method, model, _.defaults({
            contentType: 'application/x-www-form-urlencoded',
            data: model.toJSON(options),
            processData: true,
            error: xhr => {
                let rsp;
                let text;

                try {
                    rsp = $.parseJSON(xhr.responseText);
                    text = rsp.err.msg;
                } catch (e) {
                    text = 'HTTP ' + xhr.status + ' ' + xhr.statusText;
                    rsp = {
                        loadError: text,
                        canEnable: false,
                    };
                }

                if (_.isFunction(options.error)) {
                    xhr.errorText = text;
                    xhr.errorRsp = rsp;
                    options.error(xhr, options);
                }
            },
        }, options));
    },
});


/**
 * A collection of installed extensions.
 *
 * This stores the list of installed extensions, and allows fetching from
 * the API.
 */
const InstalledExtensionCollection = Backbone.Collection.extend({
    model: InstalledExtension,

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
    },
});


/**
 * Manages installed extensions.
 *
 * This stores a collection of installed extensions, and provides
 * functionality for loading the current list from the server.
 *
 * Model Attributes:
 *     apiRoot (string):
 *         The root of the extensions API, used for all lookups.
 */
Djblets.ExtensionManager = Backbone.Model.extend({
    defaults: {
        apiRoot: null,
    },

    /**
     * Initialize the manager.
     */
    initialize() {
        this.installedExtensions = new InstalledExtensionCollection();
        this.installedExtensions.url = this.get('apiRoot');
    },

    /**
     * Load the extensions list.
     */
    load() {
        this.trigger('loading');

        this.installedExtensions.fetch({
            success: () => this.trigger('loaded'),
        });
    },
});


})();
