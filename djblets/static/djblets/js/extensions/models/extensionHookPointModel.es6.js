/**
 * Defines a point where extension hooks can plug into.
 *
 * This is meant to be instantiated and provided as a 'hookPoint' field on
 * an ExtensionHook subclass, in order to provide a place to hook into.
 */
Djblets.ExtensionHookPoint = Backbone.Model.extend({
    /**
     * Initialize the hook point.
     */
    initialize() {
        this.hooks = [];
    },

    /**
     * Add a hook instance to the list of known hooks.
     *
     * Args:
     *     hook (Djblets.ExtensionHook):
     *         The hook instance.
     */
    addHook(hook) {
        this.hooks.push(hook);
    },
});
