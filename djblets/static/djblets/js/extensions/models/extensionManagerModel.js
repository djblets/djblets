var InstalledExtension;


/*
 * Represents an installed extension listed in the Manage Extensions list.
 *
 * This stores the various information about the extension that we'll display
 * to the user, and offers actions for enabling or disabling the extension.
 */
InstalledExtension = Backbone.Model.extend({
    defaults: {
        author: null,
        authorURL: null,
        configURL: null,
        dbURL: null,
        enabled: false,
        name: null,
        summary: null,
        version: null
    },

    url: function() {
        return SITE_ROOT + 'api/extensions/' + this.id + '/';
    },

    /*
     * Enables the extension.
     */
    enable: function() {
        this.save({
            enabled: true
        }, {
            wait: true,
            error: function(model, xhr) {
                alert(gettext('Failed to enable extension. ') +
                      xhr.errorText + '.');
            }
        });
    },

    /*
     * Disables the extension.
     */
    disable: function() {
        this.save({
            enabled: false
        }, {
            wait: true,
            error: function(model, xhr) {
                alert(gettext('Failed to disable extension. ') +
                      xhr.errorText + '.');
            }
        });
    },

    /*
     * Returns a JSON payload for requests sent to the server.
     */
    toJSON: function() {
        return {
            enabled: this.get('enabled')
        };
    },

    /*
     * Parses a JSON payload from the server.
     */
    parse: function(rsp) {
        var configLink,
            dbLink;

        if (rsp.stat !== undefined) {
            rsp = rsp.extension;
        }

        configLink = rsp.links['admin-configure'];
        dbLink = rsp.links['admin-database'];

        return {
            author: rsp.author,
            authorURL: rsp.author_url,
            configURL: configLink ? configLink.href : null,
            dbURL: dbLink ? dbLink.href : null,
            enabled: rsp.enabled,
            id: rsp.class_name,
            name: rsp.name,
            summary: rsp.summary,
            version: rsp.version
        };
    },

    /*
     * Performs AJAX requests against the server-side API.
     */
    sync: function(method, model, options) {
        Backbone.sync.call(this, method, model, _.defaults({
            contentType: 'application/x-www-form-urlencoded',
            data: model.toJSON(options),
            processData: true,
            error: _.bind(function(xhr) {
                var rsp = null,
                    text;

                try {
                    rsp = $.parseJSON(xhr.responseText);
                    text = rsp.err.msg;
                } catch (e) {
                    text = 'HTTP ' + xhr.status + ' ' + xhr.statusText;
                }

                console.log(xhr.responseText);
                if (_.isFunction(options.error)) {
                    xhr.errorText = text;
                    options.error(xhr, options);
                }
            }, this)
        }, options));
    }
});


/*
 * Manages installed extensions.
 *
 * This stores a collection of installed extensions, and provides
 * functionality for loading the current list from the server.
 */
Djblets.ExtensionManager = Backbone.Model.extend({
    initialize: function(attrs, options) {
        this.installedExtensions = new InstalledExtensionCollection();
    },

    load: function() {
        this.installedExtensions.fetch({
            success: _.bind(function() {
                this.trigger('loaded');
            }, this)
        });
    }
});
