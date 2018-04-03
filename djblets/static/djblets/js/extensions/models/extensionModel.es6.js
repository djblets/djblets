/**
 * Base class for an extension.
 *
 * Extensions that deal with JavaScript should subclass this to provide any
 * initialization code it needs, such as the initialization of hooks.
 *
 * Extension instances will have read access to the server-stored settings
 * for the extension.
 */
Djblets.Extension = Backbone.Model.extend({
    defaults: {
        id: null,
        name: null,
        settings: {},
    },

    /**
     * Initialize the extension.
     *
     * Subclasses that override this are expected to call this method.
     */
    initialize() {
        this.hooks = [];
    },
});
