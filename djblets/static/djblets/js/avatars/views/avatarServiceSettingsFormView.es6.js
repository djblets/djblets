/**
 * A base class for avatar service settings forms.
 *
 * Subclasses should override this to provide additional behaviour for
 * previews, etc.
 */
Djblets.Avatars.ServiceSettingsFormView = Backbone.View.extend({
    /**
     * Validate the form.
     *
     * Returns:
     *     boolean:
     *     Whether or not the form is valid.
     */
    validate() {
        return true;
    }
});
